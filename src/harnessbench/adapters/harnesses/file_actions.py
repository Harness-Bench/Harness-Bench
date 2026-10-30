"""Baseline harness that applies declared file actions from a model response."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harnessbench.adapters.harnesses.base import HarnessError, HarnessResult
from harnessbench.adapters.models.base import ModelResponse


class FileActionHarness:
    """Apply a recorded JSON response containing ``write_file`` actions.

    The action plan is validated before any file is written. Paths must stay
    inside the workspace, so the harness cannot edit the host or run record.
    """

    version = "0.1.0"

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
            planned.append((path, content, path.relative_to(root).as_posix()))

        for path, content, _ in planned:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            except OSError as exc:
                raise HarnessError(f"cannot write {path}: {exc}") from exc

        applied = tuple(relative for _, _, relative in planned)
        return HarnessResult(actions_applied=applied, detail=f"applied {len(applied)} file actions")
