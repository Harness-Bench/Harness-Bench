"""Contract tests for the task JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "task.schema.json"
VALID_TASK_PATH = ROOT / "benchmarks" / "examples" / "echo" / "task.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validator() -> Draft202012Validator:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def errors_for(payload: object) -> list[str]:
    return [error.message for error in validator().iter_errors(payload)]


def test_task_schema_is_valid() -> None:
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))


def test_example_task_passes_task_schema() -> None:
    assert errors_for(load_json(VALID_TASK_PATH)) == []


def test_missing_required_field_is_rejected() -> None:
    payload = load_json(VALID_TASK_PATH)
    del payload["task_id"]
    assert errors_for(payload)


def test_unknown_property_is_rejected() -> None:
    payload = load_json(VALID_TASK_PATH)
    payload["unexpected"] = True
    assert errors_for(payload)


def test_invalid_domain_is_rejected() -> None:
    payload = load_json(VALID_TASK_PATH)
    payload["domains"] = ["D14"]
    assert errors_for(payload)
