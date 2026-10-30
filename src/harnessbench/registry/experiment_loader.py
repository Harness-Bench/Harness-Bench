"""Load and validate versioned experiment definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from harnessbench.domain.experiment import Experiment


class ExperimentLoadError(Exception):
    """An experiment could not be read or validated."""


class ExperimentValidationError(ExperimentLoadError):
    """An experiment payload does not satisfy the experiment schema."""

    def __init__(self, messages: list[str]) -> None:
        self.messages = tuple(messages)
        detail = "; ".join(self.messages)
        super().__init__(f"experiment does not match schema: {detail}")


def _default_schema_path() -> Path:
    return Path(__file__).resolve().parents[3] / "schemas" / "experiment.schema.json"


def _load_schema(schema_path: Path | None) -> dict[str, Any]:
    path = schema_path or _default_schema_path()
    try:
        with path.open(encoding="utf-8") as handle:
            schema = json.load(handle)
    except OSError as exc:
        raise ExperimentLoadError(f"cannot read experiment schema {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ExperimentLoadError(
            f"experiment schema is not valid JSON {path}: {exc}"
        ) from exc

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ExperimentLoadError(f"invalid experiment schema {path}: {exc.message}") from exc
    return schema


def _format_error(error: Any) -> str:
    location = "/".join(str(part) for part in error.absolute_path) or "<root>"
    return f"{location}: {error.message}"


def validate_experiment(
    payload: object, *, schema_path: str | Path | None = None
) -> None:
    """Validate an experiment payload, raising on schema failure."""
    path = Path(schema_path) if schema_path is not None else None
    validator = Draft202012Validator(_load_schema(path))
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    if errors:
        raise ExperimentValidationError([_format_error(error) for error in errors])


def load_experiment(
    path: str | Path, *, schema_path: str | Path | None = None
) -> Experiment:
    """Read, validate, and return the experiment at ``path``."""
    experiment_path = Path(path)
    try:
        with experiment_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except OSError as exc:
        raise ExperimentLoadError(f"cannot read experiment {experiment_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ExperimentLoadError(
            f"experiment is not valid JSON {experiment_path}: {exc}"
        ) from exc

    validate_experiment(payload, schema_path=schema_path)
    try:
        return Experiment.from_dict(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise ExperimentLoadError(f"experiment is invalid: {exc}") from exc
