"""Command-line entry points for HarnessBench."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessbench.cli.workflows import (
    DEFAULT_EXPERIMENT_ID,
    DEFAULT_RUNS_ROOT,
    RunTaskOutcome,
    load_run_report,
    run_task,
)
from harnessbench.domain.run import Run, RunStatus
from harnessbench.registry.loader import TaskLoadError, load_task
from harnessbench.storage.store import StorageError


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level command parser."""
    parser = argparse.ArgumentParser(
        prog="harnessbench",
        description="Reproducible evaluation for agent harnesses.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate-task", help="validate a task definition")
    validate.add_argument("path", type=Path, help="path to a task JSON file")

    run = commands.add_parser("run-task", help="run one task with the baseline adapters")
    run.add_argument("task", type=Path, help="path to a task JSON file")
    run.add_argument(
        "--model-response",
        type=Path,
        required=True,
        help="recorded model response containing file actions",
    )
    run.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    run.add_argument("--run-id", help="explicit run id; defaults to a random id")
    run.add_argument("--experiment-id", default=DEFAULT_EXPERIMENT_ID)

    show = commands.add_parser("show-run", help="show a stored run and verification")
    show.add_argument("run_id")
    show.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    show.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def _validate_task(path: Path) -> int:
    try:
        task = load_task(path)
    except TaskLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    network = task.network_profile or "N/A"
    print(
        f"Valid task {task.task_id}: {task.title} "
        f"({task.task_level}/{task.environment_level}/{network})"
    )
    return 0


def _print_run_summary(run: Run) -> None:
    artifacts = ", ".join(run.artifact_refs) if run.artifact_refs else "none"
    print(f"Run {run.run_id}: {run.status.value}")
    print(f"Task: {run.task_id}")
    print(f"Artifacts: {artifacts}")
    if run.failure_detail:
        stage = run.failure_detail.get("stage", "unknown")
        message = run.failure_detail.get("message", "")
        print(f"Failure: {stage}: {message}")


def _print_verification(verification: dict[str, Any] | None) -> None:
    if verification is None:
        print("Verification: not available")
        return
    status = verification.get("status", "unknown")
    version = verification.get("verifier_version", "unknown")
    checks = verification.get("checks", [])
    print(f"Verification: {status} (verifier {version}, {len(checks)} checks)")
    for check in checks:
        if isinstance(check, dict):
            print(
                f"  - {check.get('criterion_id')}: "
                f"{check.get('status')} ({check.get('detail')})"
            )


def _run_task(args: argparse.Namespace) -> int:
    try:
        outcome: RunTaskOutcome = run_task(
            args.task,
            args.model_response,
            runs_root=args.runs_root,
            run_id=args.run_id,
            experiment_id=args.experiment_id,
        )
    except (TaskLoadError, StorageError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_run_summary(outcome.run)
    if outcome.verification is not None:
        _print_verification(outcome.verification.to_dict())
    return 0 if outcome.run.status is RunStatus.SUCCESS else 1


def _show_run(args: argparse.Namespace) -> int:
    try:
        run, verification = load_run_report(args.run_id, runs_root=args.runs_root)
    except (StorageError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        payload = {"run": run.to_dict(), "verification": verification}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    _print_run_summary(run)
    _print_verification(verification)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    args = build_parser().parse_args(argv)
    if args.command == "validate-task":
        return _validate_task(args.path)
    if args.command == "run-task":
        return _run_task(args)
    if args.command == "show-run":
        return _show_run(args)
    raise AssertionError(f"unhandled command: {args.command}")
