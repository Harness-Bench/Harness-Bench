"""Unit tests for the file-action harness and mechanism toggles."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harnessbench.adapters.harnesses.base import HarnessError
from harnessbench.adapters.harnesses.file_actions import FileActionHarness
from harnessbench.adapters.models.base import ModelResponse


def response(content: str) -> ModelResponse:
    payload = {
        "actions": [
            {"type": "write_file", "path": "greeting.txt", "content": content},
        ]
    }
    return ModelResponse(text=json.dumps(payload))


def test_writes_content_without_mechanism(tmp_path: Path) -> None:
    result = FileActionHarness().run(response("hello"), tmp_path)

    assert result.actions_applied == ("greeting.txt",)
    assert (tmp_path / "greeting.txt").read_text(encoding="utf-8") == "hello"


def test_append_trailing_newline_mechanism(tmp_path: Path) -> None:
    harness = FileActionHarness({"append_trailing_newline": True})

    harness.run(response("hello"), tmp_path)

    assert (tmp_path / "greeting.txt").read_text(encoding="utf-8") == "hello\n"


def test_append_trailing_newline_does_not_duplicate(tmp_path: Path) -> None:
    harness = FileActionHarness({"append_trailing_newline": True})

    harness.run(response("hello\n"), tmp_path)

    assert (tmp_path / "greeting.txt").read_text(encoding="utf-8") == "hello\n"


def test_unknown_mechanism_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(HarnessError, match="unsupported harness mechanisms"):
        FileActionHarness({"rewrite_everything": True})


def test_mechanism_values_must_be_boolean(tmp_path: Path) -> None:
    with pytest.raises(HarnessError, match="must be a boolean"):
        FileActionHarness({"append_trailing_newline": "yes"})


def test_mechanisms_must_be_an_object(tmp_path: Path) -> None:
    with pytest.raises(HarnessError, match="must be an object"):
        FileActionHarness(["append_trailing_newline"])  # type: ignore[arg-type]
