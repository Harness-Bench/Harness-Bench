"""Unit tests for run lifecycle and condition manifest records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from harnessbench.domain.run import ConditionManifest, Run, RunStatus

ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA_PATH = ROOT / "schemas" / "run.schema.json"


def manifest() -> ConditionManifest:
    return ConditionManifest(
        model={"provider": "example", "name": "baseline", "revision": "0.1.0"},
        harness={"name": "direct", "version": "0.1.0"},
        runtime={"name": "local", "version": "0.1.0"},
        environment={"profile": "E0", "image": None},
        network={"profile": "N0", "egress": "disabled"},
        budgets={"wall_seconds": 30},
        language_profile={"natural_languages": ["en"]},
        verifier_version="0.1.0",
    )


def run(status: RunStatus = RunStatus.PLANNED) -> Run:
    return Run(
        schema_version="0.1.0",
        run_id="run-0001",
        experiment_id="experiment-0001",
        task_id="example.echo.v1",
        status=status,
        condition_manifest=manifest(),
        timestamps={"created_at": "2026-10-30T00:00:00Z"},
    )


def load_run_schema() -> dict[str, Any]:
    with RUN_SCHEMA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_run_round_trips_through_mapping() -> None:
    original = run()

    restored = Run.from_dict(original.to_dict())

    assert restored == original


def test_run_mapping_passes_run_schema() -> None:
    errors = list(Draft202012Validator(load_run_schema()).iter_errors(run().to_dict()))

    assert errors == []


def test_active_and_terminal_statuses_are_distinct() -> None:
    assert not run(RunStatus.RUNNING).is_terminal
    assert run(RunStatus.SUCCESS).is_terminal
    assert run(RunStatus.EXECUTION_FAILED).is_terminal


def test_infrastructure_and_task_failures_are_distinct() -> None:
    assert RunStatus.EXECUTION_FAILED != RunStatus.TASK_FAILED
    assert RunStatus.SETUP_FAILED != RunStatus.TASK_FAILED
