"""Contract tests for the experiment JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "experiment.schema.json"
EXAMPLE_PATH = ROOT / "benchmarks" / "examples" / "echo" / "experiment.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validator() -> Draft202012Validator:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def errors_for(payload: object) -> list[str]:
    return [error.message for error in validator().iter_errors(payload)]


def test_experiment_schema_is_valid() -> None:
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))


def test_example_experiment_passes_schema() -> None:
    assert errors_for(load_json(EXAMPLE_PATH)) == []


def test_missing_conditions_are_rejected() -> None:
    payload = load_json(EXAMPLE_PATH)
    del payload["conditions"]
    assert errors_for(payload)


def test_unknown_experiment_property_is_rejected() -> None:
    payload = load_json(EXAMPLE_PATH)
    payload["unexpected"] = True
    assert errors_for(payload)


def test_repetitions_must_be_positive() -> None:
    payload = load_json(EXAMPLE_PATH)
    payload["repetitions"] = 0
    assert errors_for(payload)
