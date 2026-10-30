"""Model adapter contract and response value object."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


class ModelAdapterError(Exception):
    """A model adapter could not produce a response."""


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Opaque model output plus provenance metadata."""

    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ModelAdapter(Protocol):
    """Boundary between the runner and a model provider or recorded response."""

    version: str

    def invoke(self, prompt: str) -> ModelResponse:
        """Return one model response for the prompt."""
        ...
