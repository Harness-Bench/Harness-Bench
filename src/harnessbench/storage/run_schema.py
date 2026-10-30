"""Validate persisted run records against the versioned run schema.

The storage boundary is authoritative for serialized run records. This module
applies ``schemas/run.schema.json`` before a record is written or trusted after
being read. See ``storage/index.md`` and ``docs/runtime-contract.md``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


class RunSchemaError(Exception):
    """A run payload or the run schema itself is invalid."""


def default_schema_path() -> Path:
    """Return the repository run-schema path."""
    return Path(__file__).resolve().parents[3] / "schemas" / "run.schema.json"


def load_run_schema(schema_path: str | Path | None = None) -> dict[str, Any]:
    """Read and check the run schema, raising :class:`RunSchemaError` on failure."""
    path = Path(schema_path) if schema_path is not None else default_schema_path()
    try:
        with path.open(encoding="utf-8") as handle:
            schema = json.load(handle)
    except OSError as exc:
        raise RunSchemaError(f"cannot read run schema {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RunSchemaError(f"run schema is not valid JSON {path}: {exc}") from exc

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise RunSchemaError(f"invalid run schema {path}: {exc.message}") from exc
    return schema


def _format_error(error: Any) -> str:
    location = "/".join(str(part) for part in error.absolute_path) or "<root>"
    return f"{location}: {error.message}"


def validate_run_payload(
    payload: object, *, schema_path: str | Path | None = None
) -> None:
    """Validate a serialized run payload, raising on schema failure."""
    validator = Draft202012Validator(load_run_schema(schema_path))
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    if errors:
        detail = "; ".join(_format_error(error) for error in errors)
        raise RunSchemaError(f"run does not match schema: {detail}")
