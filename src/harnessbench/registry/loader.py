"""Load and validate versioned task definitions against the task schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from harnessbench.domain.task import Task


class TaskLoadError(Exception):
    """A task could not be read or validated."""


class TaskValidationError(TaskLoadError):
    """A task payload does not satisfy the task schema."""

    def __init__(self, messages: list[str]) -> None:
        self.messages = tuple(messages)
        detail = "; ".join(self.messages)
        super().__init__(f"task does not match schema: {detail}")


def _default_schema_path() -> Path:
    return Path(__file__).resolve().parents[3] / "schemas" / "task.schema.json"


def _load_schema(schema_path: Path | None) -> dict[str, Any]:
    path = schema_path or _default_schema_path()
    try:
        with path.open(encoding="utf-8") as handle:
            schema = json.load(handle)
    except OSError as exc:
        raise TaskLoadError(f"cannot read task schema {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise TaskLoadError(f"task schema is not valid JSON {path}: {exc}") from exc

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise TaskLoadError(f"invalid task schema {path}: {exc.message}") from exc
    return schema


def _format_error(error: Any) -> str:
    location = "/".join(str(part) for part in error.absolute_path) or "<root>"
    return f"{location}: {error.message}"


def validate_task(payload: object, *, schema_path: str | Path | None = None) -> None:
    """Validate a task payload, raising :class:`TaskValidationError` on failure."""
    path = Path(schema_path) if schema_path is not None else None
    validator = Draft202012Validator(_load_schema(path))
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    if errors:
        raise TaskValidationError([_format_error(error) for error in errors])


def load_task(path: str | Path, *, schema_path: str | Path | None = None) -> Task:
    """Read, validate, and return the task at ``path``."""
    task_path = Path(path)
    try:
        with task_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except OSError as exc:
        raise TaskLoadError(f"cannot read task {task_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise TaskLoadError(f"task is not valid JSON {task_path}: {exc}") from exc

    validate_task(payload, schema_path=schema_path)
    return Task.from_dict(payload)
