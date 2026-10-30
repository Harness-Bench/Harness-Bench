"""Integration tests for filesystem run and artifact storage."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from harnessbench.domain.run import ConditionManifest, Run, RunStatus
from harnessbench.storage.run_schema import RunSchemaError, validate_run_payload
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


def test_store_rejects_run_that_fails_schema_on_save(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    invalid = replace(run(), schema_version=None)  # type: ignore[arg-type]

    with pytest.raises(StorageError, match="does not match schema"):
        store.save_run(invalid)

    assert not store.has_run("run-0001")


def test_store_rejects_missing_condition_field_on_save(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    invalid = replace(
        run(),
        condition_manifest=replace(manifest(), budgets=None),  # type: ignore[arg-type]
    )

    with pytest.raises(StorageError, match="budgets"):
        store.save_run(invalid)


def test_validate_run_payload_rejects_unknown_top_level_field() -> None:
    payload = run().to_dict()
    payload["unexpected"] = True

    with pytest.raises(RunSchemaError, match="unexpected"):
        validate_run_payload(payload)


def test_store_rejects_invalid_persisted_run_on_load(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    payload = run().to_dict()
    payload["status"] = "not-a-status"
    path = store.run_manifest_path("run-0001")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(StorageError, match="does not match schema"):
        store.load_run("run-0001")


def test_store_honors_explicit_schema_path(tmp_path: Path) -> None:
    schema = load_run_schema()
    schema["properties"]["status"]["enum"] = ["planned"]
    schema_path = tmp_path / "run.schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    store = RunStore(tmp_path / "runs", schema_path=schema_path)

    with pytest.raises(StorageError, match="does not match schema"):
        store.save_run(run(status=RunStatus.SUCCESS))


def test_store_redacts_secrets_in_manifest_and_artifacts(tmp_path: Path) -> None:
    store = RunStore(tmp_path, secrets=("super-secret-key",))
    secret_run = replace(
        run(),
        condition_manifest=replace(
            manifest(),
            model={"endpoint": "https://user:super-secret-key@example.invalid/v1"},
        ),
        failure_detail={"message": "request used super-secret-key"},
    )

    path = store.save_run(secret_run)
    store.save_artifact("run-0001", "trace.txt", b"token=super-secret-key")

    assert "super-secret-key" not in path.read_text(encoding="utf-8")
    assert store.read_artifact("run-0001", "trace.txt") == b"token=[REDACTED]"


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
