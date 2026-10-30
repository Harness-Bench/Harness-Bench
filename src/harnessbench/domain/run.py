"""Run lifecycle statuses and immutable condition/run records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

JsonObject = Mapping[str, Any]

REQUIRED_CONDITION_FIELDS = (
    "model",
    "harness",
    "runtime",
    "environment",
    "network",
    "budgets",
)


class RunStatus(StrEnum):
    """Run lifecycle stages and terminal outcomes from the run schema."""

    PLANNED = "planned"
    PREPARED = "prepared"
    RUNNING = "running"
    COLLECTED = "collected"
    VERIFIED = "verified"
    ANALYZED = "analyzed"
    SETUP_FAILED = "setup_failed"
    EXECUTION_FAILED = "execution_failed"
    TIMED_OUT = "timed_out"
    POLICY_VIOLATION = "policy_violation"
    VERIFIER_FAILED = "verifier_failed"
    TASK_FAILED = "task_failed"
    INVALID = "invalid"
    RESOURCE_LIMITED = "resource_limited"
    ADAPTER_FAILED = "adapter_failed"
    PARTIAL_SUCCESS = "partial_success"
    SUCCESS = "success"
    COLLECTED_INVALID = "collected_invalid"
    VERIFIER_INVALID = "verifier_invalid"


TERMINAL_STATUSES = frozenset(
    {
        RunStatus.ANALYZED,
        RunStatus.SETUP_FAILED,
        RunStatus.EXECUTION_FAILED,
        RunStatus.TIMED_OUT,
        RunStatus.POLICY_VIOLATION,
        RunStatus.VERIFIER_FAILED,
        RunStatus.TASK_FAILED,
        RunStatus.INVALID,
        RunStatus.RESOURCE_LIMITED,
        RunStatus.ADAPTER_FAILED,
        RunStatus.PARTIAL_SUCCESS,
        RunStatus.SUCCESS,
        RunStatus.COLLECTED_INVALID,
        RunStatus.VERIFIER_INVALID,
    }
)


def _copy(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _copy(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_copy(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class ConditionManifest:
    """Frozen model, harness, runtime, and environment conditions for one run."""

    model: JsonObject
    harness: JsonObject
    runtime: JsonObject
    environment: JsonObject
    network: JsonObject
    budgets: JsonObject
    language_profile: JsonObject | None = None
    verifier_version: str | None = None
    analysis_version: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ConditionManifest:
        """Build a manifest from a mapping that already passed schema validation."""
        return cls(
            model=data["model"],
            harness=data["harness"],
            runtime=data["runtime"],
            environment=data["environment"],
            network=data["network"],
            budgets=data["budgets"],
            language_profile=data.get("language_profile"),
            verifier_version=data.get("verifier_version"),
            analysis_version=data.get("analysis_version"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable mapping with optional nulls omitted."""
        data: dict[str, Any] = {
            field: _copy(getattr(self, field)) for field in REQUIRED_CONDITION_FIELDS
        }
        if self.language_profile is not None:
            data["language_profile"] = _copy(self.language_profile)
        if self.verifier_version is not None:
            data["verifier_version"] = self.verifier_version
        if self.analysis_version is not None:
            data["analysis_version"] = self.analysis_version
        return data


@dataclass(frozen=True, slots=True)
class Run:
    """One concrete execution attempt under one frozen condition."""

    schema_version: str
    run_id: str
    experiment_id: str
    task_id: str
    status: RunStatus
    condition_manifest: ConditionManifest
    timestamps: JsonObject
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    verification_ref: str | None = None
    failure_detail: JsonObject | None = None

    @property
    def is_terminal(self) -> bool:
        """Whether the run has reached a terminal lifecycle outcome."""
        return self.status in TERMINAL_STATUSES

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Run:
        """Build a run from a mapping that already passed schema validation."""
        return cls(
            schema_version=str(data["schema_version"]),
            run_id=str(data["run_id"]),
            experiment_id=str(data["experiment_id"]),
            task_id=str(data["task_id"]),
            status=RunStatus(data["status"]),
            condition_manifest=ConditionManifest.from_dict(data["condition_manifest"]),
            timestamps=data["timestamps"],
            artifact_refs=tuple(data.get("artifact_refs", ())),
            evidence_refs=tuple(data.get("evidence_refs", ())),
            verification_ref=data.get("verification_ref"),
            failure_detail=data.get("failure_detail"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable mapping for storage or schema validation."""
        data: dict[str, Any] = {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "task_id": self.task_id,
            "status": self.status.value,
            "condition_manifest": self.condition_manifest.to_dict(),
            "timestamps": _copy(self.timestamps),
            "artifact_refs": list(self.artifact_refs),
            "evidence_refs": list(self.evidence_refs),
        }
        if self.verification_ref is not None:
            data["verification_ref"] = self.verification_ref
        if self.failure_detail is not None:
            data["failure_detail"] = _copy(self.failure_detail)
        return data
