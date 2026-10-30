"""Unit tests for verifier calibration metrics."""

from __future__ import annotations

from pathlib import Path

from harnessbench.verification.calibration import evaluate_calibration
from harnessbench.verification.calibration_loader import load_calibration_pack
from harnessbench.verification.verifier import VerificationResult, VerificationStatus

ROOT = Path(__file__).resolve().parents[2]
PACK_PATH = ROOT / "benchmarks" / "examples" / "verifier-calibration" / "pack.json"


class FixedVerifier:
    def __init__(self, status: VerificationStatus) -> None:
        self.status = status

    def verify(self, task: object, workspace: Path) -> VerificationResult:
        return VerificationResult(
            status=self.status,
            verifier_version="stub",
            checks=(),
            evidence_refs=(),
        )


def test_example_pack_is_fully_correct() -> None:
    report = evaluate_calibration(load_calibration_pack(PACK_PATH))

    assert report.all_correct is True
    assert report.metrics["cases"] == 6
    assert report.metrics["correct"] == 6
    assert report.metrics["accuracy"] == 1.0
    assert report.metrics["false_acceptance"] == 0
    assert report.metrics["false_rejection"] == 0
    assert report.metrics["invalid_results"] == 3
    assert report.metrics["unexpected_invalid"] == 0


def test_always_passing_verifier_shows_false_acceptance() -> None:
    report = evaluate_calibration(
        load_calibration_pack(PACK_PATH),
        FixedVerifier(VerificationStatus.PASSED),
    )

    assert report.metrics["false_acceptance"] == 2
    assert report.metrics["false_acceptance_rate"] == 1.0
    assert report.metrics["correct"] == 1
    assert report.metrics["cases"] == 6


def test_always_failing_verifier_shows_false_rejection() -> None:
    report = evaluate_calibration(
        load_calibration_pack(PACK_PATH),
        FixedVerifier(VerificationStatus.FAILED),
    )

    assert report.metrics["false_rejection"] == 1
    assert report.metrics["false_rejection_rate"] == 1.0
    assert report.metrics["true_reject"] == 2
    assert report.metrics["correct"] == 2
    assert report.metrics["cases"] == 6
