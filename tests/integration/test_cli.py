"""Integration tests for the command-line validation path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harnessbench.cli.main import main

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_TASK_PATH = ROOT / "benchmarks" / "examples" / "echo" / "task.json"


def test_validate_task_accepts_example(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["validate-task", str(EXAMPLE_TASK_PATH)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Valid task example.echo.v1" in captured.out
    assert captured.err == ""


def test_validate_task_reports_invalid_task(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "task.json"
    path.write_text(json.dumps({"task_id": "incomplete"}), encoding="utf-8")

    exit_code = main(["validate-task", str(path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "task does not match schema" in captured.err
    assert captured.out == ""


def test_validate_task_reports_missing_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["validate-task", str(tmp_path / "missing.json")])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "cannot read task" in captured.err


def test_cli_requires_a_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])

    assert exc_info.value.code == 2
    assert "usage:" in capsys.readouterr().err
