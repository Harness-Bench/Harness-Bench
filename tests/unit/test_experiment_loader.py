"""Unit tests for experiment loading and condition conversion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from harnessbench.domain.experiment import Experiment
from harnessbench.registry.experiment_loader import (
    ExperimentLoadError,
    ExperimentValidationError,
    load_experiment,
    validate_experiment,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = ROOT / "benchmarks" / "examples" / "echo" / "experiment.json"


def load_payload() -> dict[str, Any]:
    with EXAMPLE_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_load_experiment_returns_entity() -> None:
    experiment = load_experiment(EXAMPLE_PATH)

    assert isinstance(experiment, Experiment)
    assert experiment.experiment_id == "experiment-echo-newline"
    assert experiment.purpose == "ablation"
    assert experiment.repetitions == 3
    assert [condition.condition_id for condition in experiment.conditions] == [
        "baseline",
        "append-newline",
    ]


def test_condition_converts_to_run_manifest() -> None:
    experiment = load_experiment(EXAMPLE_PATH)

    manifest = experiment.conditions[0].to_manifest()

    assert manifest.condition_id == "baseline"
    assert manifest.harness["mechanisms"] == {"append_trailing_newline": False}
    assert manifest.verifier_version == "0.1.0"


def test_validate_experiment_accepts_example() -> None:
    validate_experiment(load_payload())


def test_validate_experiment_reports_missing_field() -> None:
    payload = load_payload()
    del payload["purpose"]

    with pytest.raises(ExperimentValidationError) as exc_info:
        validate_experiment(payload)

    assert "purpose" in str(exc_info.value)


def test_duplicate_condition_ids_are_rejected(tmp_path: Path) -> None:
    payload = load_payload()
    payload["conditions"][1]["condition_id"] = payload["conditions"][0]["condition_id"]
    path = tmp_path / "experiment.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExperimentLoadError, match="condition ids must be unique"):
        load_experiment(path)


def test_unsafe_experiment_id_is_rejected(tmp_path: Path) -> None:
    payload = load_payload()
    payload["experiment_id"] = "../escape"
    path = tmp_path / "experiment.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExperimentLoadError, match="invalid experiment_id"):
        load_experiment(path)


def test_load_experiment_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "experiment.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ExperimentLoadError, match="not valid JSON"):
        load_experiment(path)
