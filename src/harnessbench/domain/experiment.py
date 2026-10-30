"""Experiment definitions, conditions, and mechanism manifests."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from harnessbench.domain.run import ConditionManifest

JsonObject = Mapping[str, Any]
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True, slots=True)
class Condition:
    """One model/harness/runtime/environment combination in an experiment."""

    condition_id: str
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
    def from_dict(cls, data: Mapping[str, Any]) -> Condition:
        """Build a condition from a schema-validated experiment condition."""
        condition_id = data.get("condition_id")
        if not isinstance(condition_id, str) or not ID_PATTERN.fullmatch(condition_id):
            raise ValueError(f"invalid condition_id: {condition_id!r}")
        return cls(
            condition_id=condition_id,
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

    def to_manifest(self) -> ConditionManifest:
        """Convert this condition into the frozen run manifest."""
        return ConditionManifest(
            model=self.model,
            harness=self.harness,
            runtime=self.runtime,
            environment=self.environment,
            network=self.network,
            budgets=self.budgets,
            language_profile=self.language_profile,
            verifier_version=self.verifier_version,
            analysis_version=self.analysis_version,
            condition_id=self.condition_id,
        )


@dataclass(frozen=True, slots=True)
class Experiment:
    """A comparison or ablation plan with a condition matrix."""

    schema_version: str
    experiment_id: str
    purpose: str
    task_refs: tuple[str, ...]
    conditions: tuple[Condition, ...]
    repetitions: int
    analysis_plan: JsonObject | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Experiment:
        """Build an experiment from a schema-validated mapping."""
        experiment_id = data.get("experiment_id")
        if not isinstance(experiment_id, str) or not ID_PATTERN.fullmatch(experiment_id):
            raise ValueError(f"invalid experiment_id: {experiment_id!r}")

        conditions = tuple(Condition.from_dict(item) for item in data["conditions"])
        ids = [condition.condition_id for condition in conditions]
        if len(set(ids)) != len(ids):
            raise ValueError("condition ids must be unique")

        return cls(
            schema_version=str(data["schema_version"]),
            experiment_id=experiment_id,
            purpose=str(data["purpose"]),
            task_refs=tuple(data["task_refs"]),
            conditions=conditions,
            repetitions=int(data["repetitions"]),
            analysis_plan=data.get("analysis_plan"),
        )
