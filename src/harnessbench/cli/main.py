"""Command-line entry points for HarnessBench."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessbench.adapters.harnesses.base import HarnessError
from harnessbench.adapters.models.openai_compatible import OpenAICompatibleModelAdapter
from harnessbench.cli.command_workflows import RunCommandOutcome, run_command_task
from harnessbench.cli.experiment_workflows import (
    ExperimentOutcome,
    ExperimentRunError,
    load_experiment_report,
    run_experiment,
)
from harnessbench.cli.workflows import (
    DEFAULT_EXPERIMENT_ID,
    DEFAULT_RUNS_ROOT,
    RunTaskOutcome,
    load_run_report,
    run_model_task,
    run_task,
)
from harnessbench.domain.run import Run, RunStatus
from harnessbench.registry.experiment_loader import ExperimentLoadError
from harnessbench.registry.loader import TaskLoadError, load_task
from harnessbench.runtime.isolated import ExecutionPolicy
from harnessbench.storage.store import StorageError
from harnessbench.verification.calibration import (
    CalibrationError,
    CalibrationReport,
    evaluate_calibration,
)
from harnessbench.verification.calibration_loader import load_calibration_pack


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

    experiment = commands.add_parser(
        "run-experiment",
        help="run an experiment and write a matched-comparison report",
    )
    experiment.add_argument("experiment", type=Path, help="path to an experiment JSON file")
    experiment.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    experiment.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    command = commands.add_parser(
        "run-command",
        help="run a trusted command inside the isolated runtime",
    )
    command.add_argument("task", type=Path, help="path to a task JSON file")
    command.add_argument(
        "--command",
        dest="command_line",
        required=True,
        help="command line to execute inside the sandbox",
    )
    command.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    command.add_argument("--run-id")
    command.add_argument("--experiment-id", default=DEFAULT_EXPERIMENT_ID)
    command.add_argument("--timeout", type=float, default=30.0)
    command.add_argument("--memory-mb", type=int, default=512)
    command.add_argument(
        "--network-profile",
        default="N0",
        help="network policy: N0 offline, N1 allowlist, or N2 host network",
    )
    command.add_argument(
        "--allow-host",
        dest="allow_hosts",
        action="append",
        default=[],
        metavar="HOST[:PORT]",
        help="N1 allowlist entry; repeat for multiple hosts",
    )

    model_task = commands.add_parser(
        "run-model-task",
        help="call an OpenAI-compatible model and apply its file actions",
    )
    model_task.add_argument("task", type=Path, help="path to a task JSON file")
    model_task.add_argument(
        "--endpoint",
        required=True,
        help="chat-completions base URL, for example http://localhost:8000/v1",
    )
    model_task.add_argument("--model", required=True, help="provider model name")
    model_task.add_argument(
        "--api-key-env",
        default="OPENAI_API_KEY",
        help="environment variable holding the API key; empty string disables auth",
    )
    model_task.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    model_task.add_argument("--run-id")
    model_task.add_argument("--experiment-id", default=DEFAULT_EXPERIMENT_ID)
    model_task.add_argument("--timeout", type=float, default=30.0)
    model_task.add_argument("--temperature", type=float, default=0.0)

    show_experiment = commands.add_parser(
        "show-experiment",
        help="show a stored experiment analysis report",
    )
    show_experiment.add_argument("experiment_id")
    show_experiment.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    show_experiment.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    calibrate = commands.add_parser(
        "calibrate-verifier",
        help="evaluate verifier error rates against a labeled case pack",
    )
    calibrate.add_argument("pack", type=Path, help="path to a calibration pack JSON file")
    calibrate.add_argument("--json", action="store_true", help="emit machine-readable JSON")
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


def _format_rate(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.1%}"
    return "n/a"


def _format_delta(value: object, unit: str) -> str:
    if isinstance(value, (int, float)):
        return f"{value:+.3f} {unit}" if unit == "ms" else f"{value:+.1%}"
    return "n/a"


def _format_interval(value: object) -> str:
    if isinstance(value, list) and len(value) == 2:
        return f"{_format_rate(value[0])}-{_format_rate(value[1])}"
    return "n/a"


def _print_experiment(analysis: dict[str, Any]) -> None:
    print(f"Experiment {analysis.get('experiment_id')}: {analysis.get('purpose')}")
    conditions = analysis.get("conditions", [])
    total_runs = 0
    for condition in conditions:
        if not isinstance(condition, dict):
            continue
        quality = condition.get("quality", {})
        total_runs += int(quality.get("runs", 0))
    print(f"Runs: {total_runs} across {len(conditions)} conditions")

    for condition in conditions:
        if not isinstance(condition, dict):
            continue
        quality = condition.get("quality", {})
        cost = condition.get("cost", {})
        mean = cost.get("mean_duration_ms")
        mean_text = f"{mean:.3f} ms" if isinstance(mean, (int, float)) else "n/a"
        print(
            f"  {condition.get('condition_id')}: "
            f"{quality.get('successes')}/{quality.get('runs')} success, "
            f"pass rate {_format_rate(quality.get('pass_rate'))} "
            f"(95% CI {_format_interval(quality.get('wilson_95'))}), "
            f"mean {mean_text}"
        )

    for comparison in analysis.get("comparisons", []):
        if not isinstance(comparison, dict):
            continue
        print(
            f"Comparison {comparison.get('condition_a')} vs "
            f"{comparison.get('condition_b')}: {comparison.get('label')}"
        )
        mismatched = comparison.get("mismatched_fields", [])
        if mismatched:
            print(f"  mismatched fields: {', '.join(mismatched)}")
        print(
            f"  quality delta: {_format_delta(comparison.get('quality_delta'), 'rate')}; "
            f"cost delta: {_format_delta(comparison.get('cost_delta_mean_ms'), 'ms')}"
        )


def _print_calibration(report: CalibrationReport) -> None:
    metrics = report.metrics
    print(f"Verifier calibration {report.pack_id}")
    print(
        f"Cases: {metrics.get('cases')}, correct: {metrics.get('correct')}, "
        f"accuracy: {_format_rate(metrics.get('accuracy'))}"
    )
    print(
        f"False acceptance: {metrics.get('false_acceptance')}/"
        f"{metrics.get('expected_failed')} "
        f"({_format_rate(metrics.get('false_acceptance_rate'))})"
    )
    print(
        f"False rejection: {metrics.get('false_rejection')}/"
        f"{metrics.get('expected_passed')} "
        f"({_format_rate(metrics.get('false_rejection_rate'))})"
    )
    print(
        f"Invalid results: {metrics.get('invalid_results')} "
        f"({metrics.get('unexpected_invalid')} unexpected)"
    )
    for outcome in report.outcomes:
        if outcome.category != "correct":
            print(
                f"  - {outcome.case_id}: expected {outcome.expected.value}, "
                f"actual {outcome.actual.value} ({outcome.category})"
            )


def _calibrate_verifier(args: argparse.Namespace) -> int:
    try:
        pack = load_calibration_pack(args.pack)
        report = evaluate_calibration(pack)
    except CalibrationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        _print_calibration(report)
    return 0 if report.all_correct else 1


def _run_experiment(args: argparse.Namespace) -> int:
    try:
        outcome: ExperimentOutcome = run_experiment(
            args.experiment,
            runs_root=args.runs_root,
        )
    except (ExperimentLoadError, ExperimentRunError, TaskLoadError, StorageError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(outcome.analysis, indent=2, sort_keys=True))
    else:
        _print_experiment(outcome.analysis)
    return 0


def _run_command(args: argparse.Namespace) -> int:
    try:
        tokens = shlex.split(args.command_line)
    except ValueError as exc:
        print(f"error: invalid command: {exc}", file=sys.stderr)
        return 1
    if not tokens:
        print("error: command must not be empty", file=sys.stderr)
        return 1

    try:
        policy = ExecutionPolicy(
            timeout_seconds=args.timeout,
            memory_mb=args.memory_mb,
            network_profile=args.network_profile,
            network_allowlist=tuple(args.allow_hosts),
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        outcome: RunCommandOutcome = run_command_task(
            args.task,
            tokens,
            runs_root=args.runs_root,
            run_id=args.run_id,
            experiment_id=args.experiment_id,
            policy=policy,
        )
    except (HarnessError, TaskLoadError, StorageError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_run_summary(outcome.run)
    if outcome.runtime_result is not None:
        runtime = outcome.runtime_result
        print(
            f"Runtime: {runtime.status.value} "
            f"(exit {runtime.exit_code}, {runtime.duration_ms:.3f} ms)"
        )
    if outcome.verification is not None:
        _print_verification(outcome.verification.to_dict())
    return 0 if outcome.run.status is RunStatus.SUCCESS else 1


def _run_model_task(args: argparse.Namespace) -> int:
    api_key = os.environ.get(args.api_key_env) if args.api_key_env else None
    try:
        adapter = OpenAICompatibleModelAdapter(
            args.endpoint,
            args.model,
            api_key=api_key,
            timeout_seconds=args.timeout,
            temperature=args.temperature,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    model_manifest = {
        "provider": "openai-compatible",
        "name": args.model,
        "revision": args.model,
        "endpoint": args.endpoint,
        "temperature": args.temperature,
        "adapter_version": adapter.version,
    }
    try:
        outcome: RunTaskOutcome = run_model_task(
            args.task,
            adapter=adapter,
            model_manifest=model_manifest,
            runs_root=args.runs_root,
            run_id=args.run_id,
            experiment_id=args.experiment_id,
            secrets=(api_key,) if api_key else (),
        )
    except (TaskLoadError, StorageError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_run_summary(outcome.run)
    if outcome.verification is not None:
        _print_verification(outcome.verification.to_dict())
    return 0 if outcome.run.status is RunStatus.SUCCESS else 1


def _show_experiment(args: argparse.Namespace) -> int:
    try:
        analysis = load_experiment_report(
            args.experiment_id,
            runs_root=args.runs_root,
        )
    except ExperimentRunError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(analysis, indent=2, sort_keys=True))
    else:
        _print_experiment(analysis)
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
    if args.command == "run-experiment":
        return _run_experiment(args)
    if args.command == "run-command":
        return _run_command(args)
    if args.command == "run-model-task":
        return _run_model_task(args)
    if args.command == "show-experiment":
        return _show_experiment(args)
    if args.command == "calibrate-verifier":
        return _calibrate_verifier(args)
    raise AssertionError(f"unhandled command: {args.command}")
