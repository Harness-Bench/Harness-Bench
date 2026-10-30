"""Experiment execution and report-loading workflows for the CLI."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harnessbench.analysis.compare import analyze_experiment
from harnessbench.cli.workflows import DEFAULT_RUNS_ROOT, run_task
from harnessbench.domain.experiment import Condition, Experiment
from harnessbench.domain.run import Run
from harnessbench.registry.experiment_loader import load_experiment


class ExperimentRunError(Exception):
    """An experiment cannot be executed as declared."""


@dataclass(frozen=True, slots=True)
class ExperimentOutcome:
    """Experiment definition, persisted runs, and generated analysis."""

    experiment: Experiment
    runs: tuple[Run, ...]
    analysis: dict[str, Any]
    analysis_path: Path


def _response_path(condition: Condition) -> Path:
    value = condition.model.get("response_path")
    if not isinstance(value, str) or not value:
        raise ExperimentRunError(
            f"condition {condition.condition_id!r} requires model.response_path"
        )
    return Path(value)


def _report_dir(experiment_id: str, runs_root: str | Path) -> Path:
    return Path(runs_root) / "experiments" / experiment_id


def run_experiment(
    experiment_path: str | Path,
    *,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
) -> ExperimentOutcome:
    """Run every task/condition/repetition and persist the comparison report."""
    experiment = load_experiment(experiment_path)
    runs: list[Run] = []

    for task_ref in experiment.task_refs:
        task_path = Path(task_ref)
        for condition in experiment.conditions:
            response_path = _response_path(condition)
            for repetition in range(1, experiment.repetitions + 1):
                run_id = (
                    f"{experiment.experiment_id}-{condition.condition_id}-r{repetition}"
                )
                outcome = run_task(
                    task_path,
                    response_path,
                    runs_root=runs_root,
                    run_id=run_id,
                    experiment_id=experiment.experiment_id,
                    condition=condition,
                )
                runs.append(outcome.run)

    analysis = analyze_experiment(experiment, runs)
    directory = _report_dir(experiment.experiment_id, runs_root)
    directory.mkdir(parents=True, exist_ok=True)
    analysis_path = directory / "analysis.json"
    analysis_path.write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(experiment_path, directory / "experiment.json")

    return ExperimentOutcome(
        experiment=experiment,
        runs=tuple(runs),
        analysis=analysis,
        analysis_path=analysis_path,
    )


def load_experiment_report(
    experiment_id: str,
    *,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
) -> dict[str, Any]:
    """Load a stored experiment analysis report."""
    path = _report_dir(experiment_id, runs_root) / "analysis.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ExperimentRunError(f"cannot read experiment report {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ExperimentRunError(f"experiment report is not valid JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ExperimentRunError(f"experiment report must be a JSON object: {path}")
    return payload
