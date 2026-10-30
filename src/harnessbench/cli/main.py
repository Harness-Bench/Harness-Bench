"""Command-line entry points for HarnessBench."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from harnessbench.registry.loader import TaskLoadError, load_task


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level command parser."""
    parser = argparse.ArgumentParser(
        prog="harnessbench",
        description="Reproducible evaluation for agent harnesses.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate-task", help="validate a task definition")
    validate.add_argument("path", type=Path, help="path to a task JSON file")
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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    args = build_parser().parse_args(argv)
    if args.command == "validate-task":
        return _validate_task(args.path)
    raise AssertionError(f"unhandled command: {args.command}")
