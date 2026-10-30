"""Baseline model adapter that returns a recorded response from disk."""

from __future__ import annotations

from pathlib import Path

from harnessbench.adapters.models.base import ModelAdapterError, ModelResponse


class FixtureModelAdapter:
    """Deterministic baseline adapter for reproducible vertical-slice runs."""

    version = "0.1.0"

    def __init__(self, response_path: str | Path) -> None:
        self.response_path = Path(response_path)

    def invoke(self, prompt: str) -> ModelResponse:
        """Return the recorded response; the prompt is not sent to a model."""
        try:
            text = self.response_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ModelAdapterError(
                f"cannot read model response {self.response_path}: {exc}"
            ) from exc

        return ModelResponse(
            text=text,
            metadata={
                "adapter": "fixture",
                "version": self.version,
                "response_path": str(self.response_path),
            },
        )
