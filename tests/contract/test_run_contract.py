"""Contract tests tying domain run types to the run schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harnessbench.domain.run import REQUIRED_CONDITION_FIELDS, RunStatus

ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA_PATH = ROOT / "schemas" / "run.schema.json"


def load_schema() -> dict[str, Any]:
    with RUN_SCHEMA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_run_status_enum_matches_schema() -> None:
    schema = load_schema()
    expected = set(schema["properties"]["status"]["enum"])

    assert {status.value for status in RunStatus} == expected


def test_required_condition_fields_match_schema() -> None:
    schema = load_schema()
    expected = set(schema["properties"]["condition_manifest"]["required"])

    assert set(REQUIRED_CONDITION_FIELDS) == expected
