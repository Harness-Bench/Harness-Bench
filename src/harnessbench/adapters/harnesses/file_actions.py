"""Baseline harness that applies declared file actions from a model response."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harnessbench.adapters.harnesses.base import HarnessError, HarnessResult
from harnessbench.adapters.models.base import ModelResponse
from harnessbench.runtime.isolated import IsolatedRuntime, RuntimeResult

SUPPORTED_MECHANISMS = frozenset({"append_trailing_newline"})

_APPLY_PLAN_SCRIPT = r"""
import json
import pathlib
import sys

root = pathlib.Path("/workspace").resolve()
try:
    plan = json.load(sys.stdin)
except Exception as exc:
    print(f"invalid action plan: {exc}", file=sys.stderr)
    raise SystemExit(2)

actions = plan.get("actions") if isinstance(plan, dict) else None
if not isinstance(actions, list):
    print("action plan must contain an actions list", file=sys.stderr)
    raise SystemExit(2)

for index, action in enumerate(actions):
    if not isinstance(action, dict):
        print(f"action {index} must be an object", file=sys.stderr)
        raise SystemExit(2)
    raw_path = action.get("path")
    content = action.get("content")
    if not isinstance(raw_path, str) or not raw_path:
        print(f"action {index} path must be a non-empty string", file=sys.stderr)
        raise SystemExit(2)
    if not isinstance(content, str):
        print(f"action {index} content must be a string", file=sys.stderr)
        raise SystemExit(2)
    path = (root / raw_path).resolve()
    if not path.is_relative_to(root):
        print(f"action {index} path escapes the workspace", file=sys.stderr)
        raise SystemExit(2)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
"""


@dataclass(frozen=True, slots=True)
class PlannedAction:
    """One validated file write, before it is applied in a workspace."""

    path: str
    content: str


class FileActionHarness:
    """Validate a recorded JSON response containing ``write_file`` actions.

    The action plan is validated before any file is written. Paths must stay
    inside the workspace, so the harness cannot edit the host or run record.
    Optional mechanisms transform content before writing; unknown mechanisms
    fail closed instead of being silently ignored.

    ``run`` applies actions in-process for unit-level contract tests. The CLI
    baseline uses :meth:`execute` so writes happen inside the isolated runtime.
    """

    version = "0.3.0"

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

    def plan(
        self, response: ModelResponse, workspace: str | Path
    ) -> tuple[PlannedAction, ...]:
        """Parse and validate a response into a workspace-relative write plan."""
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

        planned: list[PlannedAction] = []
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
                PlannedAction(
                    path=path.relative_to(root).as_posix(),
                    content=self._transform(content),
                )
            )
        return tuple(planned)

    def apply(
        self, planned: Sequence[PlannedAction], workspace: str | Path
    ) -> HarnessResult:
        """Apply an already validated plan inside ``workspace`` in-process."""
        root = Path(workspace).resolve()
        if not root.is_dir():
            raise HarnessError(f"workspace does not exist: {workspace}")

        for action in planned:
            path = (root / action.path).resolve()
            if not path.is_relative_to(root):
                raise HarnessError(f"action path escapes the workspace: {action.path}")
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(action.content, encoding="utf-8")
            except OSError as exc:
                raise HarnessError(f"cannot write {path}: {exc}") from exc

        applied = tuple(action.path for action in planned)
        return HarnessResult(
            actions_applied=applied,
            detail=f"applied {len(applied)} file actions",
        )

    def run(self, response: ModelResponse, workspace: str | Path) -> HarnessResult:
        """Validate and apply the response's file actions in-process."""
        return self.apply(self.plan(response, workspace), workspace)

    def execute(
        self,
        planned: Sequence[PlannedAction],
        runtime: IsolatedRuntime,
    ) -> RuntimeResult:
        """Apply a validated plan inside an isolated runtime workspace."""
        payload = {
            "actions": [
                {"path": action.path, "content": action.content}
                for action in planned
            ]
        }
        return runtime.execute(
            ["python3", "-c", _APPLY_PLAN_SCRIPT],
            input_data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )
