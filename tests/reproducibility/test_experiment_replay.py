"""Reproducibility tests for experiment replay and recorded provenance."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from harnessbench.cli.experiment_workflows import run_experiment

pytestmark = pytest.mark.skipif(
    shutil.which("bwrap") is None,
    reason="bubblewrap is not installed",
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_EXPERIMENT_PATH = ROOT / "benchmarks" / "examples" / "echo" / "experiment.json"


def quality_summary(analysis: dict[str, Any]) -> list[tuple[str, Any]]:
    return [
        (condition["condition_id"], condition["quality"])
        for condition in analysis["conditions"]
    ]


def comparison_summary(analysis: dict[str, Any]) -> list[tuple[Any, ...]]:
    return [
        (
            comparison["condition_a"],
            comparison["condition_b"],
            comparison["matched"],
            tuple(comparison["mismatched_fields"]),
            comparison["quality_delta"],
        )
        for comparison in analysis["comparisons"]
    ]


def test_experiment_replay_preserves_quality_and_comparisons(tmp_path: Path) -> None:
    first = run_experiment(EXAMPLE_EXPERIMENT_PATH, runs_root=tmp_path / "first")
    second = run_experiment(EXAMPLE_EXPERIMENT_PATH, runs_root=tmp_path / "second")

    assert [run.run_id for run in first.runs] == [run.run_id for run in second.runs]
    assert [run.status for run in first.runs] == [run.status for run in second.runs]
    assert quality_summary(first.analysis) == quality_summary(second.analysis)
    assert comparison_summary(first.analysis) == comparison_summary(second.analysis)


def test_every_run_records_provenance_and_verifier_version(tmp_path: Path) -> None:
    outcome = run_experiment(EXAMPLE_EXPERIMENT_PATH, runs_root=tmp_path)

    assert len(outcome.runs) == 6
    for run in outcome.runs:
        manifest = run.condition_manifest
        assert manifest.model["revision"]
        assert manifest.harness["version"]
        assert manifest.runtime["version"]
        assert manifest.verifier_version
        assert manifest.condition_id
        assert run.experiment_id == "experiment-echo-newline"


def test_condition_matrix_repeats_the_declared_number_of_times(tmp_path: Path) -> None:
    outcome = run_experiment(EXAMPLE_EXPERIMENT_PATH, runs_root=tmp_path)

    counts: dict[str, int] = {}
    for run in outcome.runs:
        condition_id = run.condition_manifest.condition_id or "unknown"
        counts[condition_id] = counts.get(condition_id, 0) + 1

    assert counts == {"baseline": 3, "append-newline": 3}
