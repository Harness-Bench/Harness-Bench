"""Shared run lifecycle persistence helpers used by CLI workflows."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from harnessbench.domain.run import Run, RunStatus
from harnessbench.storage.store import RunStore


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def json_bytes(payload: object) -> bytes:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return text.encode("utf-8")


def save_status(
    store: RunStore,
    run: Run,
    status: RunStatus,
    *,
    timestamp_key: str | None = None,
    extra: dict[str, Any] | None = None,
) -> Run:
    timestamps = dict(run.timestamps)
    if timestamp_key is not None:
        timestamps[timestamp_key] = utc_now()
    if extra is not None:
        timestamps.update(store.redactor.redact_payload(extra))
    updated = replace(run, status=status, timestamps=timestamps)
    store.save_run(updated)
    return updated


def finish(
    store: RunStore,
    run: Run,
    status: RunStatus,
    *,
    detail: dict[str, Any] | None,
) -> Run:
    timestamps = {**run.timestamps, "finished_at": utc_now()}
    if detail is not None:
        detail = store.redactor.redact_payload(detail)
    updated = replace(run, status=status, failure_detail=detail, timestamps=timestamps)
    store.save_run(updated)
    return updated
