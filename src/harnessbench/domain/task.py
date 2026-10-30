"""Immutable task definition shared by registry, runtime, and verification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

JsonObject = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Task:
    """A schema-validated task definition.

    Construct with :meth:`from_dict` after schema validation. Array fields are
    tuples to prevent accidental mutation; nested mappings are retained as
    provided.
    """

    schema_version: str
    task_id: str
    title: str
    task_level: str
    environment_level: str
    instructions: str
    success_criteria: tuple[JsonObject, ...]
    domains: tuple[str, ...]
    language_profile: JsonObject
    provenance: JsonObject
    network_profile: str | None = None
    initial_state: JsonObject | None = None
    budgets: JsonObject | None = None
    verifier: JsonObject | None = None
    tags: tuple[str, ...] = ()
    risk_level: str | None = None
    critical_invariants: tuple[JsonObject, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Task:
        """Build a task from a mapping that already passed schema validation."""
        return cls(
            schema_version=str(data["schema_version"]),
            task_id=str(data["task_id"]),
            title=str(data["title"]),
            task_level=str(data["task_level"]),
            environment_level=str(data["environment_level"]),
            instructions=str(data["instructions"]),
            success_criteria=tuple(data["success_criteria"]),
            domains=tuple(data["domains"]),
            language_profile=data["language_profile"],
            provenance=data["provenance"],
            network_profile=data.get("network_profile"),
            initial_state=data.get("initial_state"),
            budgets=data.get("budgets"),
            verifier=data.get("verifier"),
            tags=tuple(data.get("tags", ())),
            risk_level=data.get("risk_level"),
            critical_invariants=tuple(data.get("critical_invariants", ())),
        )
