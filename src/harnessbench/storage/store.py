"""Filesystem persistence for run manifests and artifacts.

Run records are validated against the versioned run schema before they are
written and after they are read. See ``storage/index.md`` and
``docs/runtime-contract.md``.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessbench.domain.run import Run
from harnessbench.storage.redaction import SecretRedactor
from harnessbench.storage.run_schema import RunSchemaError, validate_run_payload

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class StorageError(Exception):
    """A run or artifact could not be persisted or read safely."""


def _safe_relative(name: str) -> Path:
    path = Path(name)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise StorageError(f"path must stay within the run directory: {name!r}")
    return path


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


class RunStore:
    """Persist runs as ``runs/<run_id>/run.json`` with a sibling artifact tree."""

    def __init__(
        self,
        root: str | Path = "runs",
        *,
        schema_path: str | Path | None = None,
        secrets: Sequence[str] = (),
    ) -> None:
        self.root = Path(root)
        self.schema_path = Path(schema_path) if schema_path is not None else None
        self.redactor = SecretRedactor(secrets)

    def run_dir(self, run_id: str) -> Path:
        """Return the run directory, rejecting ids that could escape the root."""
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise StorageError(f"invalid run id: {run_id!r}")
        return self.root / run_id

    def run_manifest_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "run.json"

    def artifact_dir(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "artifacts"

    def artifact_path(self, run_id: str, name: str) -> Path:
        """Return a safe artifact path inside the run directory."""
        return self.artifact_dir(run_id) / _safe_relative(name)

    def has_run(self, run_id: str) -> bool:
        return self.run_manifest_path(run_id).is_file()

    def save_run(self, run: Run) -> Path:
        """Validate and atomically write or replace the run manifest."""
        path = self.run_manifest_path(run.run_id)
        payload_dict = self.redactor.redact_payload(run.to_dict())
        try:
            validate_run_payload(payload_dict, schema_path=self.schema_path)
        except RunSchemaError as exc:
            raise StorageError(f"run {run.run_id!r} does not match schema: {exc}") from exc

        payload = (
            json.dumps(
                payload_dict,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        )
        _write_atomic(path, payload.encode("utf-8"))
        return path

    def load_run(self, run_id: str) -> Run:
        """Read and schema-validate a run manifest, then rebuild the domain entity."""
        path = self.run_manifest_path(run_id)
        try:
            payload: Any = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise StorageError(f"cannot read run {run_id!r}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise StorageError(f"run {run_id!r} is not valid JSON: {exc}") from exc

        try:
            validate_run_payload(payload, schema_path=self.schema_path)
        except RunSchemaError as exc:
            raise StorageError(f"run {run_id!r} does not match schema: {exc}") from exc

        try:
            return Run.from_dict(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise StorageError(f"run {run_id!r} is invalid: {exc}") from exc

    def save_artifact(self, run_id: str, name: str, content: bytes) -> Path:
        """Write redacted artifact bytes for an existing run."""
        if not self.has_run(run_id):
            raise StorageError(f"run {run_id!r} has no saved manifest")
        path = self.artifact_path(run_id, name)
        _write_atomic(path, self.redactor.redact_bytes(content))
        return path

    def read_artifact(self, run_id: str, name: str) -> bytes:
        """Read artifact bytes, rejecting unsafe paths."""
        path = self.artifact_path(run_id, name)
        try:
            return path.read_bytes()
        except OSError as exc:
            raise StorageError(f"cannot read artifact {name!r} for {run_id!r}: {exc}") from exc

    def list_artifacts(self, run_id: str) -> tuple[str, ...]:
        """Return sorted artifact paths relative to the run's artifact directory."""
        directory = self.artifact_dir(run_id)
        if not directory.is_dir():
            return ()
        return tuple(
            sorted(
                path.relative_to(directory).as_posix()
                for path in directory.rglob("*")
                if path.is_file()
            )
        )
