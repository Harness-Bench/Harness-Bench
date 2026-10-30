"""Integration tests for the run and report CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harnessbench.cli.main import main

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_TASK_PATH = ROOT / "benchmarks" / "examples" / "echo" / "task.json"
EXAMPLE_RESPONSE_PATH = ROOT / "benchmarks" / "examples" / "echo" / "model_response.json"


def test_run_task_cli_succeeds(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        [
            "run-task",
            str(EXAMPLE_TASK_PATH),
            "--model-response",
            str(EXAMPLE_RESPONSE_PATH),
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-0001",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Run run-0001: success" in captured.out
    assert "Verification: passed" in captured.out
    assert captured.err == ""


def test_run_task_cli_returns_nonzero_for_task_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    response = tmp_path / "response.json"
    response.write_text(
        json.dumps(
            {
                "actions": [
                    {"type": "write_file", "path": "greeting.txt", "content": "wrong\n"}
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "run-task",
            str(EXAMPLE_TASK_PATH),
            "--model-response",
            str(response),
            "--runs-root",
            str(tmp_path / "runs"),
            "--run-id",
            "run-failed",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Run run-failed: task_failed" in captured.out
    assert "Verification: failed" in captured.out


def test_show_run_cli_renders_stored_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(
        [
            "run-task",
            str(EXAMPLE_TASK_PATH),
            "--model-response",
            str(EXAMPLE_RESPONSE_PATH),
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-0001",
        ]
    )
    capsys.readouterr()

    exit_code = main(["show-run", "run-0001", "--runs-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Run run-0001: success" in captured.out
    assert "Verification: passed" in captured.out
    assert "greeting.txt" in captured.out


def test_show_run_json_is_machine_readable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(
        [
            "run-task",
            str(EXAMPLE_TASK_PATH),
            "--model-response",
            str(EXAMPLE_RESPONSE_PATH),
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-0001",
        ]
    )
    capsys.readouterr()

    exit_code = main(["show-run", "run-0001", "--runs-root", str(tmp_path), "--json"])
    captured = capsys.readouterr()

    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["run"]["status"] == "success"
    assert payload["verification"]["status"] == "passed"


def test_show_run_reports_missing_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["show-run", "run-missing", "--runs-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "cannot read run" in captured.err
