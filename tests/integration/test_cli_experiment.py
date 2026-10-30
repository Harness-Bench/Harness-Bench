"""Integration tests for experiment CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harnessbench.cli.main import main

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_EXPERIMENT_PATH = ROOT / "benchmarks" / "examples" / "echo" / "experiment.json"


def test_run_experiment_cli_renders_comparison(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "run-experiment",
            str(EXAMPLE_EXPERIMENT_PATH),
            "--runs-root",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Experiment experiment-echo-newline: ablation" in captured.out
    assert "Comparison baseline vs append-newline: matched" in captured.out
    assert "quality delta: +100.0%" in captured.out
    assert captured.err == ""


def test_show_experiment_cli_renders_stored_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(
        [
            "run-experiment",
            str(EXAMPLE_EXPERIMENT_PATH),
            "--runs-root",
            str(tmp_path),
        ]
    )
    capsys.readouterr()

    exit_code = main(
        ["show-experiment", "experiment-echo-newline", "--runs-root", str(tmp_path)]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Experiment experiment-echo-newline: ablation" in captured.out
    assert "pass rate 0.0%" in captured.out
    assert "pass rate 100.0%" in captured.out


def test_show_experiment_json_is_machine_readable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(
        [
            "run-experiment",
            str(EXAMPLE_EXPERIMENT_PATH),
            "--runs-root",
            str(tmp_path),
        ]
    )
    capsys.readouterr()

    exit_code = main(
        [
            "show-experiment",
            "experiment-echo-newline",
            "--runs-root",
            str(tmp_path),
            "--json",
        ]
    )
    captured = capsys.readouterr()

    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["experiment_id"] == "experiment-echo-newline"
    assert payload["comparisons"][0]["matched"] is True


def test_show_experiment_reports_missing_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        ["show-experiment", "experiment-missing", "--runs-root", str(tmp_path)]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "cannot read experiment report" in captured.err
