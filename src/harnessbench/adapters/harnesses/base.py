"""Harness adapter contract and result value object."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from harnessbench.adapters.models.base import ModelResponse


class HarnessError(Exception):
    """A harness could not apply a model response to the workspace."""


@dataclass(frozen=True, slots=True)
class HarnessResult:
    """Observable effects produced by a harness invocation."""

    actions_applied: tuple[str, ...]
    detail: str


class HarnessAdapter(Protocol):
    """Boundary between the runner and an executable harness implementation."""

    version: str

    def run(self, response: ModelResponse, workspace: str | Path) -> HarnessResult:
        """Apply one model response inside the workspace."""
        ...
