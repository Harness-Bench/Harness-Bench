"""Unit tests for matched comparison and uncertainty calculations."""

from __future__ import annotations

import pytest

from harnessbench.analysis.compare import (
    analyze_experiment,
    mismatched_fields,
    wilson_interval,
)
from harnessbench.domain.experiment import Condition, Experiment
from harnessbench.domain.run import Run, RunStatus


def condition(
    condition_id: str,
    *,
    response_path: str = "response.json",
    append_newline: bool = False,
) -> Condition:
    return Condition(
        condition_id=condition_id,
        model={"provider": "fixture", "response_path": response_path},
        harness={
            "name": "file-actions",
            "mechanisms": {"append_trailing_newline": append_newline},
        },
        runtime={"name": "in-process"},
        environment={"profile": "E0"},
        network={"profile": "N0"},
        budgets={"wall_seconds": 30},
        verifier_version="0.1.0",
    )


def run(condition_value: Condition, status: RunStatus) -> Run:
    return Run(
        schema_version="0.1.0",
        run_id=f"run-{condition_value.condition_id}",
        experiment_id="experiment-test",
        task_id="task-test",
        status=status,
        condition_manifest=condition_value.to_manifest(),
        timestamps={"harness_duration_ms": 1.0},
    )


def experiment(condition_a: Condition, condition_b: Condition) -> Experiment:
    return Experiment(
        schema_version="0.1.0",
        experiment_id="experiment-test",
        purpose="ablation",
        task_refs=("task.json",),
        conditions=(condition_a, condition_b),
        repetitions=1,
    )


def test_harness_mechanism_is_not_a_matched_field() -> None:
    baseline = condition("baseline")
    toggled = condition("toggled", append_newline=True)

    assert mismatched_fields(baseline.to_manifest(), toggled.to_manifest()) == ()


def test_model_difference_is_reported_as_unmatched() -> None:
    baseline = condition("baseline")
    changed = condition("changed", response_path="other.json")

    assert mismatched_fields(baseline.to_manifest(), changed.to_manifest()) == ("model",)


def test_wilson_interval_bounds() -> None:
    low, high = wilson_interval(0, 3)
    assert low == 0.0
    assert high == pytest.approx(0.5615, abs=0.001)

    low, high = wilson_interval(3, 3)
    assert low == pytest.approx(0.4385, abs=0.001)
    assert high == 1.0


def test_analysis_reports_matched_quality_and_cost() -> None:
    baseline = condition("baseline")
    toggled = condition("toggled", append_newline=True)

    analysis = analyze_experiment(
        experiment(baseline, toggled),
        [run(baseline, RunStatus.TASK_FAILED), run(toggled, RunStatus.SUCCESS)],
    )

    assert analysis["conditions"][0]["quality"]["pass_rate"] == 0.0
    assert analysis["conditions"][1]["quality"]["pass_rate"] == 1.0
    assert analysis["comparisons"][0]["label"] == "matched"
    assert analysis["comparisons"][0]["quality_delta"] == 1.0
    assert analysis["comparisons"][0]["cost_delta_mean_ms"] == 0.0


def test_analysis_labels_unmatched_comparisons() -> None:
    baseline = condition("baseline")
    changed = condition("changed", response_path="other.json")

    analysis = analyze_experiment(
        experiment(baseline, changed),
        [run(baseline, RunStatus.SUCCESS), run(changed, RunStatus.SUCCESS)],
    )

    comparison = analysis["comparisons"][0]
    assert comparison["matched"] is False
    assert comparison["label"] == "unmatched"
    assert comparison["mismatched_fields"] == ["model"]
