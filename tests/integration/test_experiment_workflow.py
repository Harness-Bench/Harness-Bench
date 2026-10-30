"""Integration tests for experiment execution and analysis reports."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from harnessbench.cli.experiment_workflows import (
    ExperimentRunError,
    load_experiment_report,
    run_experiment,
)
from harnessbench.domain.run import RunStatus
from harnessbench.storage.store import RunStore

pytestmark = pytest.mark.skipif(
    shutil.which("bwrap") is None,
    reason="bubblewrap is not installed",
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_EXPERIMENT_PATH = ROOT / "benchmarks" / "examples" / "echo" / "experiment.json"


def test_example_experiment_reports_matched_ablation(tmp_path: Path) -> None:
    outcome = run_experiment(EXAMPLE_EXPERIMENT_PATH, runs_root=tmp_path)

    assert len(outcome.runs) == 6
    assert outcome.analysis_path.is_file()
    assert (outcome.analysis_path.parent / "experiment.json").is_file()

    baseline = outcome.analysis["conditions"][0]
    normalized = outcome.analysis["conditions"][1]
    assert baseline["quality"]["successes"] == 0
    assert baseline["quality"]["runs"] == 3
    assert baseline["quality"]["pass_rate"] == 0.0
    assert normalized["quality"]["successes"] == 3
    assert normalized["quality"]["pass_rate"] == 1.0
    assert normalized["quality"]["wilson_95"][1] == 1.0
    assert baseline["cost"]["samples"] == 3
    assert normalized["cost"]["samples"] == 3

    comparison = outcome.analysis["comparisons"][0]
    assert comparison["label"] == "matched"
    assert comparison["mismatched_fields"] == []
    assert comparison["quality_delta"] == 1.0

    store = RunStore(tmp_path)
    assert store.load_run("experiment-echo-newline-baseline-r1").status is RunStatus.TASK_FAILED
    assert store.load_run("experiment-echo-newline-append-newline-r1").status is RunStatus.SUCCESS

    report = load_experiment_report("experiment-echo-newline", runs_root=tmp_path)
    assert report["experiment_id"] == "experiment-echo-newline"


def test_unmatched_conditions_are_labelled(tmp_path: Path) -> None:
    payload = json.loads(EXAMPLE_EXPERIMENT_PATH.read_text(encoding="utf-8"))
    payload["experiment_id"] = "experiment-echo-unmatched"
    payload["conditions"][1]["model"]["response_path"] = (
        "benchmarks/examples/echo/model_response.json"
    )
    experiment_path = tmp_path / "experiment.json"
    experiment_path.write_text(json.dumps(payload), encoding="utf-8")

    outcome = run_experiment(experiment_path, runs_root=tmp_path / "runs")

    comparison = outcome.analysis["comparisons"][0]
    assert comparison["matched"] is False
    assert comparison["label"] == "unmatched"
    assert comparison["mismatched_fields"] == ["model"]


def test_experiment_without_model_response_is_rejected(tmp_path: Path) -> None:
    payload = json.loads(EXAMPLE_EXPERIMENT_PATH.read_text(encoding="utf-8"))
    del payload["conditions"][0]["model"]["response_path"]
    experiment_path = tmp_path / "experiment.json"
    experiment_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExperimentRunError, match="requires model.response_path"):
        run_experiment(experiment_path, runs_root=tmp_path / "runs")
