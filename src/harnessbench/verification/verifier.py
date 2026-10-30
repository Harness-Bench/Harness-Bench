"""Independent evidence-based verification for file-oriented task criteria."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from harnessbench.domain.run import RunStatus
from harnessbench.domain.task import Task


class VerificationStatus(StrEnum):
    """Overall verifier outcome."""

    PASSED = "passed"
    FAILED = "failed"
    INVALID = "invalid"


class CheckStatus(StrEnum):
    """Outcome of one success-criterion check."""

    PASSED = "passed"
    FAILED = "failed"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One criterion evaluation with an evidence reference where available."""

    criterion_id: str
    kind: str
    status: CheckStatus
    detail: str
    evidence_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "criterion_id": self.criterion_id,
            "kind": self.kind,
            "status": self.status.value,
            "detail": self.detail,
        }
        if self.evidence_ref is not None:
            data["evidence_ref"] = self.evidence_ref
        return data


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Structured verdict for one run; never derived from agent self-report."""

    status: VerificationStatus
    verifier_version: str
    checks: tuple[CheckResult, ...]
    evidence_refs: tuple[str, ...]
    detail: str | None = None

    def to_run_status(self) -> RunStatus:
        """Map the verdict onto the terminal run status."""
        if self.status is VerificationStatus.PASSED:
            return RunStatus.SUCCESS
        if self.status is VerificationStatus.FAILED:
            return RunStatus.TASK_FAILED
        return RunStatus.VERIFIER_INVALID

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "status": self.status.value,
            "verifier_version": self.verifier_version,
            "checks": [check.to_dict() for check in self.checks],
            "evidence_refs": list(self.evidence_refs),
        }
        if self.detail is not None:
            data["detail"] = self.detail
        return data


class FileVerifier:
    """Evaluate file success criteria against a workspace directory.

    Supported criterion kinds are ``file_exists`` and ``content_equals``.
    Unknown kinds, malformed criteria, or paths escaping the workspace make the
    verification result invalid rather than a task failure.
    """

    def __init__(self, version: str = "0.1.0") -> None:
        self.version = version

    def verify(self, task: Task, workspace: str | Path) -> VerificationResult:
        """Verify all task criteria against files under ``workspace``."""
        root = Path(workspace).resolve()
        if not root.is_dir():
            return VerificationResult(
                status=VerificationStatus.INVALID,
                verifier_version=self.version,
                checks=(),
                evidence_refs=(),
                detail=f"workspace does not exist: {workspace}",
            )

        checks = tuple(
            self._check(criterion, index, root)
            for index, criterion in enumerate(task.success_criteria)
        )
        if not checks:
            return VerificationResult(
                status=VerificationStatus.INVALID,
                verifier_version=self.version,
                checks=(),
                evidence_refs=(),
                detail="task has no success criteria",
            )
        evidence_refs = tuple(
            dict.fromkeys(
                check.evidence_ref for check in checks if check.evidence_ref is not None
            )
        )

        if any(check.status is CheckStatus.INVALID for check in checks):
            status = VerificationStatus.INVALID
        elif all(check.status is CheckStatus.PASSED for check in checks):
            status = VerificationStatus.PASSED
        else:
            status = VerificationStatus.FAILED

        return VerificationResult(
            status=status,
            verifier_version=self.version,
            checks=checks,
            evidence_refs=evidence_refs,
        )

    def _check(self, criterion: object, index: int, root: Path) -> CheckResult:
        if not isinstance(criterion, dict):
            return CheckResult(
                criterion_id=f"criterion-{index}",
                kind="unknown",
                status=CheckStatus.INVALID,
                detail="criterion must be an object",
            )

        criterion_id = criterion.get("criterion_id")
        kind = criterion.get("kind")
        if not isinstance(criterion_id, str) or not criterion_id:
            return CheckResult(
                criterion_id=f"criterion-{index}",
                kind=str(kind),
                status=CheckStatus.INVALID,
                detail="criterion_id must be a non-empty string",
            )
        if not isinstance(kind, str) or not kind:
            return CheckResult(
                criterion_id=criterion_id,
                kind="unknown",
                status=CheckStatus.INVALID,
                detail="kind must be a non-empty string",
            )

        if kind == "file_exists":
            return self._check_file_exists(criterion_id, kind, criterion, root)
        if kind == "content_equals":
            return self._check_content_equals(criterion_id, kind, criterion, root)
        return CheckResult(
            criterion_id=criterion_id,
            kind=kind,
            status=CheckStatus.INVALID,
            detail=f"unsupported criterion kind: {kind}",
        )

    def _resolve(self, criterion_id: str, kind: str, criterion: dict[str, Any], root: Path):
        raw_path = criterion.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            return None, CheckResult(
                criterion_id=criterion_id,
                kind=kind,
                status=CheckStatus.INVALID,
                detail="path must be a non-empty string",
            )

        path = (root / raw_path).resolve()
        if not path.is_relative_to(root):
            return None, CheckResult(
                criterion_id=criterion_id,
                kind=kind,
                status=CheckStatus.INVALID,
                detail=f"path escapes the workspace: {raw_path}",
            )
        return path, None

    def _check_file_exists(
        self, criterion_id: str, kind: str, criterion: dict[str, Any], root: Path
    ) -> CheckResult:
        path, invalid = self._resolve(criterion_id, kind, criterion, root)
        if invalid is not None:
            return invalid
        assert path is not None
        evidence_ref = path.relative_to(root).as_posix()
        if path.is_file():
            return CheckResult(
                criterion_id=criterion_id,
                kind=kind,
                status=CheckStatus.PASSED,
                detail="file exists",
                evidence_ref=evidence_ref,
            )
        return CheckResult(
            criterion_id=criterion_id,
            kind=kind,
            status=CheckStatus.FAILED,
            detail="file does not exist",
            evidence_ref=evidence_ref,
        )

    def _check_content_equals(
        self, criterion_id: str, kind: str, criterion: dict[str, Any], root: Path
    ) -> CheckResult:
        expected = criterion.get("expected")
        if not isinstance(expected, str):
            return CheckResult(
                criterion_id=criterion_id,
                kind=kind,
                status=CheckStatus.INVALID,
                detail="expected must be a string",
            )

        path, invalid = self._resolve(criterion_id, kind, criterion, root)
        if invalid is not None:
            return invalid
        assert path is not None
        evidence_ref = path.relative_to(root).as_posix()
        try:
            actual = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return CheckResult(
                criterion_id=criterion_id,
                kind=kind,
                status=CheckStatus.FAILED,
                detail="file does not exist",
                evidence_ref=evidence_ref,
            )
        except (OSError, UnicodeDecodeError) as exc:
            return CheckResult(
                criterion_id=criterion_id,
                kind=kind,
                status=CheckStatus.FAILED,
                detail=f"file could not be read as UTF-8: {exc}",
                evidence_ref=evidence_ref,
            )

        if actual == expected:
            return CheckResult(
                criterion_id=criterion_id,
                kind=kind,
                status=CheckStatus.PASSED,
                detail="content matches",
                evidence_ref=evidence_ref,
            )
        return CheckResult(
            criterion_id=criterion_id,
            kind=kind,
            status=CheckStatus.FAILED,
            detail="content does not match",
            evidence_ref=evidence_ref,
        )
