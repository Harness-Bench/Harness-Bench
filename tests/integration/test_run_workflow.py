"""Integration tests for the end-to-end baseline run workflow."""

from __future__ import annotations

import json
from pathlib import Path

from harnessbench.cli.workflows import load_run_report, run_task
from harnessbench.domain.run import RunStatus
from harnessbench.storage.store import RunStore
from harnessbench.verification.verifier import VerificationStatus

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_TASK_PATH = ROOT / "benchmarks" / "examples" / "echo" / "task.json"
EXAMPLE_RESPONSE_PATH = ROOT / "benchmarks" / "examples" / "echo" / "model_response.json"
NESTED_TASK_PATH = ROOT / "benchmarks" / "examples" / "nested-write" / "task.json"
NESTED_RESPONSE_PATH = ROOT / "benchmarks" / "examples" / "nested-write" / "model_response.json"


def write_response(path: Path, actions: object) -> Path:
    path.write_text(json.dumps({"actions": actions}), encoding="utf-8")
    return path


def test_successful_run_persists_verified_record(tmp_path: Path) -> None:
    outcome = run_task(
        EXAMPLE_TASK_PATH,
        EXAMPLE_RESPONSE_PATH,
        runs_root=tmp_path,
        run_id="run-0001",
    )

    assert outcome.run.status is RunStatus.SUCCESS
    assert outcome.verification is not None
    assert outcome.verification.status is VerificationStatus.PASSED
    assert "greeting.txt" in outcome.run.artifact_refs
    assert "verification.json" in outcome.run.artifact_refs
    assert outcome.run.verification_ref == "verification.json"
    assert outcome.run.evidence_refs == ("greeting.txt",)
    assert outcome.run.condition_manifest.verifier_version == "0.1.0"
    assert outcome.run.condition_manifest.runtime["isolation"] == "none"
    assert outcome.run.condition_manifest.runtime["limits"] == "not_enforced"
    assert "created_at" in outcome.run.timestamps
    assert "finished_at" in outcome.run.timestamps

    store = RunStore(tmp_path)
    loaded = store.load_run("run-0001")
    assert loaded == outcome.run

    verification = json.loads(store.read_artifact("run-0001", "verification.json"))
    assert verification["status"] == "passed"
    assert store.read_artifact("run-0001", "greeting.txt") == b"hello harnessbench\n"


def test_failed_verification_becomes_task_failure(tmp_path: Path) -> None:
    response = write_response(
        tmp_path / "response.json",
        [{"type": "write_file", "path": "greeting.txt", "content": "wrong\n"}],
    )

    outcome = run_task(
        EXAMPLE_TASK_PATH,
        response,
        runs_root=tmp_path / "runs",
        run_id="run-failed",
    )

    assert outcome.run.status is RunStatus.TASK_FAILED
    assert outcome.verification is not None
    assert outcome.verification.status is VerificationStatus.FAILED
    assert outcome.run.failure_detail is not None
    assert outcome.run.failure_detail["verifier_status"] == "failed"


def test_adapter_failure_is_not_a_task_failure(tmp_path: Path) -> None:
    response = tmp_path / "response.json"
    response.write_text("not json", encoding="utf-8")

    outcome = run_task(
        EXAMPLE_TASK_PATH,
        response,
        runs_root=tmp_path / "runs",
        run_id="run-adapter-failure",
    )

    assert outcome.run.status is RunStatus.ADAPTER_FAILED
    assert outcome.verification is None
    assert outcome.run.failure_detail is not None
    assert outcome.run.failure_detail["stage"] == "harness_adapter"


def test_missing_model_response_is_an_adapter_failure(tmp_path: Path) -> None:
    outcome = run_task(
        EXAMPLE_TASK_PATH,
        tmp_path / "missing.json",
        runs_root=tmp_path / "runs",
        run_id="run-missing-response",
    )

    assert outcome.run.status is RunStatus.ADAPTER_FAILED
    assert outcome.run.failure_detail is not None
    assert outcome.run.failure_detail["stage"] == "model_adapter"


def test_file_action_cannot_escape_workspace(tmp_path: Path) -> None:
    response = write_response(
        tmp_path / "response.json",
        [{"type": "write_file", "path": "../escape.txt", "content": "escape\n"}],
    )

    outcome = run_task(
        EXAMPLE_TASK_PATH,
        response,
        runs_root=tmp_path / "runs",
        run_id="run-escape",
    )

    assert outcome.run.status is RunStatus.ADAPTER_FAILED
    assert outcome.run.failure_detail is not None
    assert "escapes the workspace" in outcome.run.failure_detail["message"]


def test_report_can_be_reloaded_from_storage(tmp_path: Path) -> None:
    outcome = run_task(
        EXAMPLE_TASK_PATH,
        EXAMPLE_RESPONSE_PATH,
        runs_root=tmp_path,
        run_id="run-report",
    )

    run, verification = load_run_report("run-report", runs_root=tmp_path)

    assert run == outcome.run
    assert verification is not None
    assert verification["status"] == "passed"


def test_nested_example_task_runs_and_verifies(tmp_path: Path) -> None:
    outcome = run_task(
        NESTED_TASK_PATH,
        NESTED_RESPONSE_PATH,
        runs_root=tmp_path,
        run_id="run-nested",
    )

    assert outcome.run.status is RunStatus.SUCCESS
    assert outcome.verification is not None
    assert outcome.verification.status is VerificationStatus.PASSED
    assert "out/result.txt" in outcome.run.artifact_refs
