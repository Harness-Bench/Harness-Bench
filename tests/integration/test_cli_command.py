"""Integration tests for the isolated command CLI path."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from harnessbench.cli.main import main

pytestmark = pytest.mark.skipif(
    shutil.which("bwrap") is None,
    reason="bubblewrap is not installed",
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_TASK_PATH = ROOT / "benchmarks" / "examples" / "echo" / "task.json"


def test_run_command_cli_succeeds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "run-command",
            str(EXAMPLE_TASK_PATH),
            "--command",
            "sh -c \"printf 'hello harnessbench\\n' > greeting.txt\"",
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-command",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Run run-command: success" in captured.out
    assert "Runtime: completed" in captured.out
    assert "Verification: passed" in captured.out
    assert captured.err == ""


def test_run_command_cli_timeout_returns_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "run-command",
            str(EXAMPLE_TASK_PATH),
            "--command",
            "sh -c 'sleep 2'",
            "--timeout",
            "0.2",
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-command-timeout",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Run run-command-timeout: timed_out" in captured.out
    assert "Runtime: timed_out" in captured.out


def test_run_command_cli_rejects_invalid_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "run-command",
            str(EXAMPLE_TASK_PATH),
            "--command",
            "'",
            "--runs-root",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "invalid command" in captured.err


def test_show_run_includes_runtime_trace_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(
        [
            "run-command",
            str(EXAMPLE_TASK_PATH),
            "--command",
            "sh -c \"printf 'hello harnessbench\\n' > greeting.txt\"",
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-command",
        ]
    )
    capsys.readouterr()

    exit_code = main(["show-run", "run-command", "--runs-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Run run-command: success" in captured.out
    assert "runtime_trace.json" in captured.out
