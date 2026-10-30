"""Unit tests for task loading and schema validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from harnessbench.domain.task import Task
from harnessbench.registry.loader import (
    TaskLoadError,
    TaskValidationError,
    load_task,
    validate_task,
)

ROOT = Path(__file__).resolve().parents[2]
VALID_TASK_PATH = ROOT / "benchmarks" / "examples" / "echo" / "task.json"


def load_payload() -> dict[str, Any]:
    with VALID_TASK_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_load_task_returns_entity() -> None:
    task = load_task(VALID_TASK_PATH)

    assert isinstance(task, Task)
    assert task.task_id == "example.echo.v1"
    assert task.domains == ("D1",)
    assert isinstance(task.success_criteria, tuple)


def test_validate_task_accepts_fixture() -> None:
    validate_task(load_payload())


def test_validate_task_reports_missing_field() -> None:
    payload = load_payload()
    del payload["instructions"]

    with pytest.raises(TaskValidationError) as exc_info:
        validate_task(payload)

    assert "instructions" in str(exc_info.value)
    assert any("instructions" in message for message in exc_info.value.messages)


def test_load_task_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "task.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(TaskLoadError, match="not valid JSON"):
        load_task(path)


def test_load_task_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(TaskLoadError, match="cannot read task"):
        load_task(tmp_path / "missing.json")
