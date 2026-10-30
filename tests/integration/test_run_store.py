"""Integration tests for filesystem run and artifact storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from harnessbench.domain.run import ConditionManifest, Run, RunStatus
from harnessbench.storage.store import RunStore, StorageError

ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA_PATH = ROOT / "schemas" / "run.schema.json"


def manifest() -> ConditionManifest:
    return ConditionManifest(
        model={"provider": "example", "name": "baseline", "revision": "0.1.0"},
        harness={"name": "direct", "version": "0.1.0"},
        runtime={"name": "local", "version": "0.1.0"},
        environment={"profile": "E0"},
        network={"profile": "N0"},
        budgets={"wall_seconds": 30},
        verifier_version="0.1.0",
    )


def run(run_id: str = "run-0001", status: RunStatus = RunStatus.PLANNED) -> Run:
    return Run(
        schema_version="0.1.0",
        run_id=run_id,
        experiment_id="experiment-0001",
        task_id="example.echo.v1",
        status=status,
        condition_manifest=manifest(),
        timestamps={"created_at": "2026-10-30T00:00:00Z"},
    )


def load_run_schema() -> dict[str, Any]:
    with RUN_SCHEMA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_run_round_trips_through_store(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    original = run()

    path = store.save_run(original)

    assert path == tmp_path / "run-0001" / "run.json"
    assert store.load_run("run-0001") == original


def test_saved_manifest_passes_run_schema(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    path = store.save_run(run())

    payload = json.loads(path.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(load_run_schema()).iter_errors(payload))

    assert errors == []


def test_artifacts_round_trip_and_are_listed(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.save_run(run())

    store.save_artifact("run-0001", "greeting.txt", b"hello harnessbench\n")
    store.save_artifact("run-0001", "nested/log.txt", b"log\n")

    assert store.read_artifact("run-0001", "greeting.txt") == b"hello harnessbench\n"
    assert store.list_artifacts("run-0001") == ("greeting.txt", "nested/log.txt")


def test_artifact_requires_saved_run(tmp_path: Path) -> None:
    store = RunStore(tmp_path)

    with pytest.raises(StorageError, match="no saved manifest"):
        store.save_artifact("run-0001", "greeting.txt", b"data")


def test_store_rejects_unsafe_run_ids(tmp_path: Path) -> None:
    store = RunStore(tmp_path)

    with pytest.raises(StorageError, match="invalid run id"):
        store.save_run(run(run_id="../escape"))


def test_store_rejects_unsafe_artifact_paths(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.save_run(run())

    with pytest.raises(StorageError, match="path must stay"):
        store.save_artifact("run-0001", "../escape.txt", b"data")


def test_missing_run_is_reported(tmp_path: Path) -> None:
    store = RunStore(tmp_path)

    with pytest.raises(StorageError, match="cannot read run"):
        store.load_run("run-0001")
