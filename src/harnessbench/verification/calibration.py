"""Verifier calibration packs and false-accept/reject metrics."""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harnessbench.domain.task import Task
from harnessbench.verification.verifier import VerificationResult, VerificationStatus


class CalibrationError(Exception):
    """A calibration pack or case is malformed."""


@dataclass(frozen=True, slots=True)
class CalibrationCase:
    """One expected verifier outcome with its task criteria and workspace files."""

    case_id: str
    expected: VerificationStatus
    task: Task
    files: Mapping[str, str]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CalibrationCase:
        case_id = data.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise CalibrationError("case_id must be a non-empty string")

        expected_raw = data.get("expected")
        try:
            expected = VerificationStatus(expected_raw)
        except ValueError as exc:
            raise CalibrationError(f"invalid expected status: {expected_raw!r}") from exc

        criteria = data.get("criteria", [])
        if not isinstance(criteria, list) or not all(
            isinstance(criterion, dict) for criterion in criteria
        ):
            raise CalibrationError("criteria must be an array of objects")

        files = data.get("files", {})
        if not isinstance(files, Mapping) or not all(
            isinstance(name, str) and isinstance(content, str)
            for name, content in files.items()
        ):
            raise CalibrationError("files must map strings to strings")

        task = Task(
            schema_version="0.1.0",
            task_id=f"calibration.{case_id}",
            title=f"Calibration case {case_id}",
            task_level="B0",
            environment_level="E0",
            instructions="",
            success_criteria=tuple(criteria),
            domains=("D5",),
            language_profile={
                "natural_languages": ["en"],
                "programming_languages": [],
                "artifact_languages": ["text"],
                "transformation_path": ["direct"],
            },
            provenance={"source": "verifier calibration", "split": "public_dev"},
        )
        return cls(case_id=case_id, expected=expected, task=task, files=dict(files))


@dataclass(frozen=True, slots=True)
class CalibrationPack:
    """A versioned collection of labeled verifier cases."""

    schema_version: str
    pack_id: str
    cases: tuple[CalibrationCase, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CalibrationPack:
        pack_id = data.get("pack_id")
        if not isinstance(pack_id, str) or not pack_id:
            raise CalibrationError("pack_id must be a non-empty string")
        cases_raw = data.get("cases")
        if not isinstance(cases_raw, list) or not cases_raw:
            raise CalibrationError("cases must be a non-empty array")
        cases = tuple(CalibrationCase.from_dict(case) for case in cases_raw)
        identifiers = [case.case_id for case in cases]
        if len(set(identifiers)) != len(identifiers):
            raise CalibrationError("case ids must be unique")
        return cls(
            schema_version=str(data.get("schema_version", "0.1.0")),
            pack_id=pack_id,
            cases=cases,
        )


@dataclass(frozen=True, slots=True)
class CalibrationOutcome:
    """Actual versus expected result for one case."""

    case_id: str
    expected: VerificationStatus
    actual: VerificationStatus
    category: str
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "case_id": self.case_id,
            "expected": self.expected.value,
            "actual": self.actual.value,
            "category": self.category,
        }
        if self.detail is not None:
            data["detail"] = self.detail
        return data


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    """Calibration outcomes plus aggregate error rates."""

    pack_id: str
    outcomes: tuple[CalibrationOutcome, ...]
    metrics: Mapping[str, Any]

    @property
    def all_correct(self) -> bool:
        return all(outcome.category == "correct" for outcome in self.outcomes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "metrics": dict(self.metrics),
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }


def _write_files(workspace: Path, files: Mapping[str, str]) -> None:
    for name, content in files.items():
        path = (workspace / name).resolve()
        if not path.is_relative_to(workspace):
            raise CalibrationError(f"case file escapes workspace: {name!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _category(expected: VerificationStatus, actual: VerificationStatus) -> str:
    if expected is actual:
        return "correct"
    if actual is VerificationStatus.INVALID:
        return "invalid"
    if expected is VerificationStatus.PASSED and actual is VerificationStatus.FAILED:
        return "false_rejection"
    if expected is VerificationStatus.FAILED and actual is VerificationStatus.PASSED:
        return "false_acceptance"
    return "mismatch"


def evaluate_calibration(
    pack: CalibrationPack,
    verifier: Any | None = None,
) -> CalibrationReport:
    """Run a verifier over every labeled case and compute error metrics."""
    from harnessbench.verification.verifier import FileVerifier

    active = verifier or FileVerifier()
    outcomes: list[CalibrationOutcome] = []

    for case in pack.cases:
        with tempfile.TemporaryDirectory(prefix="harnessbench-calibration-") as temporary:
            workspace = Path(temporary)
            _write_files(workspace, case.files)
            result: VerificationResult = active.verify(case.task, workspace)
            detail = result.detail
            if detail is None:
                detail = "; ".join(
                    f"{check.criterion_id}: {check.status.value}"
                    for check in result.checks
                ) or None
            outcomes.append(
                CalibrationOutcome(
                    case_id=case.case_id,
                    expected=case.expected,
                    actual=result.status,
                    category=_category(case.expected, result.status),
                    detail=detail,
                )
            )

    total = len(outcomes)
    correct = sum(outcome.category == "correct" for outcome in outcomes)
    expected_passed = sum(
        outcome.expected is VerificationStatus.PASSED for outcome in outcomes
    )
    expected_failed = sum(
        outcome.expected is VerificationStatus.FAILED for outcome in outcomes
    )
    true_accept = sum(
        outcome.expected is VerificationStatus.PASSED
        and outcome.actual is VerificationStatus.PASSED
        for outcome in outcomes
    )
    true_reject = sum(
        outcome.expected is VerificationStatus.FAILED
        and outcome.actual is VerificationStatus.FAILED
        for outcome in outcomes
    )
    false_accept = sum(
        outcome.category == "false_acceptance" for outcome in outcomes
    )
    false_reject = sum(
        outcome.category == "false_rejection" for outcome in outcomes
    )
    invalid_results = sum(
        outcome.actual is VerificationStatus.INVALID for outcome in outcomes
    )
    unexpected_invalid = sum(
        outcome.actual is VerificationStatus.INVALID
        and outcome.expected is not VerificationStatus.INVALID
        for outcome in outcomes
    )

    metrics = {
        "cases": total,
        "correct": correct,
        "accuracy": correct / total if total else None,
        "true_accept": true_accept,
        "true_reject": true_reject,
        "expected_passed": expected_passed,
        "expected_failed": expected_failed,
        "false_acceptance": false_accept,
        "false_rejection": false_reject,
        "false_acceptance_rate": (
            false_accept / expected_failed if expected_failed else None
        ),
        "false_rejection_rate": (
            false_reject / expected_passed if expected_passed else None
        ),
        "invalid_results": invalid_results,
        "unexpected_invalid": unexpected_invalid,
    }
    return CalibrationReport(
        pack_id=pack.pack_id,
        outcomes=tuple(outcomes),
        metrics=metrics,
    )
