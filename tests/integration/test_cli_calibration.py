"""Integration tests for the verifier calibration CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harnessbench.cli.main import main

ROOT = Path(__file__).resolve().parents[2]
PACK_PATH = ROOT / "benchmarks" / "examples" / "verifier-calibration" / "pack.json"


def test_calibration_cli_reports_perfect_pack(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["calibrate-verifier", str(PACK_PATH)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Verifier calibration file-verifier-basic" in captured.out
    assert "accuracy: 100.0%" in captured.out
    assert "False acceptance: 0/2 (0.0%)" in captured.out
    assert "False rejection: 0/1 (0.0%)" in captured.out


def test_calibration_cli_returns_nonzero_for_mismatch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    payload["cases"][1]["expected"] = "passed"
    pack_path = tmp_path / "pack.json"
    pack_path.write_text(json.dumps(payload), encoding="utf-8")

    exit_code = main(["calibrate-verifier", str(pack_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "false_rejection" in captured.out


def test_calibration_cli_json_is_machine_readable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["calibrate-verifier", str(PACK_PATH), "--json"])
    captured = capsys.readouterr()

    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["metrics"]["accuracy"] == 1.0
    assert payload["pack_id"] == "file-verifier-basic"


def test_calibration_cli_reports_missing_pack(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["calibrate-verifier", str(tmp_path / "missing.json")])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "cannot read calibration pack" in captured.err
