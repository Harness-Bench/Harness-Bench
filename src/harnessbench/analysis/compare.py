"""Matched comparison and ablation summaries over stored runs."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from harnessbench.domain.experiment import Condition, Experiment
from harnessbench.domain.run import ConditionManifest, Run, RunStatus

ANALYSIS_VERSION = "0.1.0"
MATCHED_FIELDS = (
    "model",
    "runtime",
    "environment",
    "network",
    "budgets",
    "language_profile",
    "verifier_version",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def mismatched_fields(
    condition_a: ConditionManifest, condition_b: ConditionManifest
) -> tuple[str, ...]:
    """Return matched-condition fields that differ between two manifests."""
    return tuple(
        field
        for field in MATCHED_FIELDS
        if _canonical(getattr(condition_a, field)) != _canonical(getattr(condition_b, field))
    )


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Return the Wilson score interval for a binomial pass rate."""
    if total <= 0:
        return (0.0, 1.0)
    proportion = successes / total
    denominator = 1 + (z * z / total)
    center = (proportion + (z * z / (2 * total))) / denominator
    margin = (
        z
        * math.sqrt((proportion * (1 - proportion) + (z * z / (4 * total))) / total)
        / denominator
    )
    return (max(0.0, center - margin), min(1.0, center + margin))


def _duration_ms(run: Run) -> float | None:
    value = run.timestamps.get("harness_duration_ms")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _quality(runs: Sequence[Run]) -> dict[str, Any]:
    total = len(runs)
    successes = sum(run.status is RunStatus.SUCCESS for run in runs)
    if total == 0:
        return {
            "successes": 0,
            "runs": 0,
            "pass_rate": None,
            "wilson_95": None,
        }
    low, high = wilson_interval(successes, total)
    return {
        "successes": successes,
        "runs": total,
        "pass_rate": successes / total,
        "wilson_95": [low, high],
    }


def _cost(runs: Sequence[Run]) -> dict[str, Any]:
    durations = [duration for run in runs if (duration := _duration_ms(run)) is not None]
    if not durations:
        return {
            "samples": 0,
            "mean_duration_ms": None,
            "min_duration_ms": None,
            "max_duration_ms": None,
        }
    return {
        "samples": len(durations),
        "mean_duration_ms": sum(durations) / len(durations),
        "min_duration_ms": min(durations),
        "max_duration_ms": max(durations),
    }


def summarize_condition(condition: Condition, runs: Sequence[Run]) -> dict[str, Any]:
    """Summarize quality and cost separately for one condition."""
    return {
        "condition_id": condition.condition_id,
        "harness": dict(condition.harness),
        "quality": _quality(runs),
        "cost": _cost(runs),
        "status_counts": dict(Counter(run.status.value for run in runs)),
    }


def analyze_experiment(experiment: Experiment, runs: Sequence[Run]) -> dict[str, Any]:
    """Build a versioned matched-comparison report from experiment runs."""
    grouped: dict[str, list[Run]] = defaultdict(list)
    for run in runs:
        grouped[run.condition_manifest.condition_id or "unknown"].append(run)

    summaries = [
        summarize_condition(condition, grouped.get(condition.condition_id, ()))
        for condition in experiment.conditions
    ]
    by_id = {summary["condition_id"]: summary for summary in summaries}

    comparisons = []
    for index, condition_a in enumerate(experiment.conditions):
        for condition_b in experiment.conditions[index + 1 :]:
            mismatched = mismatched_fields(
                condition_a.to_manifest(),
                condition_b.to_manifest(),
            )
            quality_a = by_id[condition_a.condition_id]["quality"]["pass_rate"]
            quality_b = by_id[condition_b.condition_id]["quality"]["pass_rate"]
            cost_a = by_id[condition_a.condition_id]["cost"]["mean_duration_ms"]
            cost_b = by_id[condition_b.condition_id]["cost"]["mean_duration_ms"]
            comparisons.append(
                {
                    "condition_a": condition_a.condition_id,
                    "condition_b": condition_b.condition_id,
                    "label": "matched" if not mismatched else "unmatched",
                    "matched": not mismatched,
                    "mismatched_fields": list(mismatched),
                    "quality_delta": (
                        None if quality_a is None or quality_b is None else quality_b - quality_a
                    ),
                    "cost_delta_mean_ms": (
                        None if cost_a is None or cost_b is None else cost_b - cost_a
                    ),
                }
            )

    return {
        "schema_version": "0.1.0",
        "analysis_version": ANALYSIS_VERSION,
        "experiment_id": experiment.experiment_id,
        "purpose": experiment.purpose,
        "repetitions": experiment.repetitions,
        "task_refs": list(experiment.task_refs),
        "conditions": summaries,
        "comparisons": comparisons,
        "unlinked_runs": len(grouped.get("unknown", ())),
        "generated_at": datetime.now(UTC).isoformat(),
    }
