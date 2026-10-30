"""Unit tests for the file verifier."""

from __future__ import annotations

from pathlib import Path

from harnessbench.domain.task import Task
from harnessbench.verification.verifier import (
    CheckStatus,
    FileVerifier,
    VerificationStatus,
)


def task(criteria: tuple[dict[str, object], ...]) -> Task:
    return Task(
        schema_version="0.1.0",
        task_id="example.echo.v1",
        title="Write a greeting file",
        task_level="B0",
        environment_level="E0",
        instructions="Create greeting.txt.",
        success_criteria=criteria,
        domains=("D1",),
        language_profile={"natural_languages": ["en"]},
        provenance={"source": "test", "split": "public_dev"},
    )


def test_passes_when_all_criteria_pass(tmp_path: Path) -> None:
    (tmp_path / "greeting.txt").write_text("hello harnessbench\n", encoding="utf-8")
    criteria = (
        {"criterion_id": "exists", "kind": "file_exists", "path": "greeting.txt"},
        {
            "criterion_id": "content",
            "kind": "content_equals",
            "path": "greeting.txt",
            "expected": "hello harnessbench\n",
        },
    )

    result = FileVerifier().verify(task(criteria), tmp_path)

    assert result.status is VerificationStatus.PASSED
    assert all(check.status is CheckStatus.PASSED for check in result.checks)
    assert result.evidence_refs == ("greeting.txt",)


def test_fails_when_file_is_missing(tmp_path: Path) -> None:
    criteria = ({"criterion_id": "exists", "kind": "file_exists", "path": "missing.txt"},)

    result = FileVerifier().verify(task(criteria), tmp_path)

    assert result.status is VerificationStatus.FAILED
    assert result.checks[0].status is CheckStatus.FAILED


def test_fails_when_content_differs(tmp_path: Path) -> None:
    (tmp_path / "greeting.txt").write_text("wrong\n", encoding="utf-8")
    criteria = (
        {
            "criterion_id": "content",
            "kind": "content_equals",
            "path": "greeting.txt",
            "expected": "hello harnessbench\n",
        },
    )

    result = FileVerifier().verify(task(criteria), tmp_path)

    assert result.status is VerificationStatus.FAILED


def test_invalid_when_kind_is_unsupported(tmp_path: Path) -> None:
    criteria = ({"criterion_id": "unknown", "kind": "command", "path": "greeting.txt"},)

    result = FileVerifier().verify(task(criteria), tmp_path)

    assert result.status is VerificationStatus.INVALID
    assert result.checks[0].status is CheckStatus.INVALID


def test_invalid_when_path_escapes_workspace(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("data\n", encoding="utf-8")
    criteria = ({"criterion_id": "escape", "kind": "file_exists", "path": "../outside.txt"},)

    result = FileVerifier().verify(task(criteria), tmp_path)

    assert result.status is VerificationStatus.INVALID
    assert "escapes the workspace" in result.checks[0].detail


def test_invalid_when_expected_content_is_missing(tmp_path: Path) -> None:
    criteria = ({"criterion_id": "content", "kind": "content_equals", "path": "greeting.txt"},)

    result = FileVerifier().verify(task(criteria), tmp_path)

    assert result.status is VerificationStatus.INVALID
    assert result.checks[0].status is CheckStatus.INVALID


def test_invalid_when_workspace_is_missing(tmp_path: Path) -> None:
    criteria = ({"criterion_id": "exists", "kind": "file_exists", "path": "greeting.txt"},)

    result = FileVerifier().verify(task(criteria), tmp_path / "missing")

    assert result.status is VerificationStatus.INVALID
    assert result.checks == ()
    assert "workspace does not exist" in (result.detail or "")


def test_invalid_when_task_has_no_criteria(tmp_path: Path) -> None:
    result = FileVerifier().verify(task(()), tmp_path)

    assert result.status is VerificationStatus.INVALID
    assert result.detail == "task has no success criteria"


def test_result_maps_to_distinct_run_statuses(tmp_path: Path) -> None:
    verifier = FileVerifier()
    passed = verifier.verify(
        task(({"criterion_id": "exists", "kind": "file_exists", "path": "missing.txt"},)),
        tmp_path,
    )
    (tmp_path / "missing.txt").write_text("data\n", encoding="utf-8")
    success = verifier.verify(
        task(({"criterion_id": "exists", "kind": "file_exists", "path": "missing.txt"},)),
        tmp_path,
    )

    assert passed.to_run_status().value == "task_failed"
    assert success.to_run_status().value == "success"
