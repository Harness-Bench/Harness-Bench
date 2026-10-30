"""Baseline harness that applies declared file actions from a model response."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from harnessbench.adapters.harnesses.base import HarnessError, HarnessResult
from harnessbench.adapters.models.base import ModelResponse

SUPPORTED_MECHANISMS = frozenset({"append_trailing_newline"})


class FileActionHarness:
    """Apply a recorded JSON response containing ``write_file`` actions.

    The action plan is validated before any file is written. Paths must stay
    inside the workspace, so the harness cannot edit the host or run record.
    Optional mechanisms transform content before writing; unknown mechanisms
    fail closed instead of being silently ignored.
    """

    version = "0.2.0"

    def __init__(self, mechanisms: Mapping[str, Any] | None = None) -> None:
        if mechanisms is not None and not isinstance(mechanisms, Mapping):
            raise HarnessError("harness mechanisms must be an object")
        self.mechanisms = dict(mechanisms or {})
        unknown = set(self.mechanisms) - SUPPORTED_MECHANISMS
        if unknown:
            names = ", ".join(sorted(unknown))
            raise HarnessError(f"unsupported harness mechanisms: {names}")
        append = self.mechanisms.get("append_trailing_newline", False)
        if not isinstance(append, bool):
            raise HarnessError("append_trailing_newline must be a boolean")

    def _transform(self, content: str) -> str:
        if self.mechanisms.get("append_trailing_newline") and not content.endswith("\n"):
            return content + "\n"
        return content

    def run(self, response: ModelResponse, workspace: str | Path) -> HarnessResult:
        """Validate and apply the response's file actions."""
        root = Path(workspace).resolve()
        if not root.is_dir():
            raise HarnessError(f"workspace does not exist: {workspace}")

        try:
            payload: Any = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise HarnessError(f"model response is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise HarnessError("model response must be a JSON object")

        actions = payload.get("actions")
        if not isinstance(actions, list) or not actions:
            raise HarnessError("model response must contain a non-empty actions list")

        planned: list[tuple[Path, str, str]] = []
        for index, action in enumerate(actions):
            if not isinstance(action, dict):
                raise HarnessError(f"action {index} must be an object")
            if action.get("type") != "write_file":
                raise HarnessError(f"action {index} has unsupported type")

            raw_path = action.get("path")
            content = action.get("content")
            if not isinstance(raw_path, str) or not raw_path:
                raise HarnessError(f"action {index} path must be a non-empty string")
            if not isinstance(content, str):
                raise HarnessError(f"action {index} content must be a string")

            path = (root / raw_path).resolve()
            if not path.is_relative_to(root):
                raise HarnessError(f"action {index} path escapes the workspace")
            planned.append(
                (path, self._transform(content), path.relative_to(root).as_posix())
            )

        for path, content, _ in planned:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            except OSError as exc:
                raise HarnessError(f"cannot write {path}: {exc}") from exc

        applied = tuple(relative for _, _, relative in planned)
        return HarnessResult(actions_applied=applied, detail=f"applied {len(applied)} file actions")

