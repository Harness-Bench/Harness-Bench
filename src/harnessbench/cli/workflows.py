"""Application workflows invoked by the CLI; argument parsing stays in main."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from harnessbench.adapters.harnesses.base import HarnessError
from harnessbench.adapters.harnesses.file_actions import FileActionHarness
from harnessbench.adapters.models.base import ModelAdapterError
from harnessbench.adapters.models.fixture import FixtureModelAdapter
from harnessbench.cli.run_lifecycle import finish, json_bytes, save_status, utc_now
from harnessbench.domain.experiment import Condition
from harnessbench.domain.run import ConditionManifest, Run, RunStatus
from harnessbench.domain.task import Task
from harnessbench.registry.loader import load_task
from harnessbench.storage.store import RunStore, StorageError
from harnessbench.verification.verifier import FileVerifier, VerificationResult

DEFAULT_RUNS_ROOT = Path("runs")
DEFAULT_EXPERIMENT_ID = "experiment-local"
SCHEMA_VERSION = "0.1.0"
RUNTIME_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class RunTaskOutcome:
    """Persisted run plus the verifier result when verification was reached."""

    run: Run
    verification: VerificationResult | None


def _wall_seconds(task: Task) -> float:
    if task.budgets is not None:
        value = task.budgets.get("wall_seconds")
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return 30.0


def _build_manifest(
    task: Task, response_path: Path, condition: Condition | None = None
) -> ConditionManifest:
    if condition is not None:
        return condition.to_manifest()
    return ConditionManifest(
        model={
            "provider": "fixture",
            "name": "recorded-response",
            "revision": "0.1.0",
            "response_path": str(response_path),
        },
        harness={"name": "file-actions", "version": FileActionHarness.version},
        runtime={
            "name": "in-process",
            "version": RUNTIME_VERSION,
            "isolation": "none",
            "limits": "not_enforced",
        },
        environment={"profile": task.environment_level, "workspace": "temporary"},
        network={"profile": task.network_profile or "N0", "egress": "not_enforced"},
        budgets={"wall_seconds": _wall_seconds(task)},
        language_profile=task.language_profile,
        verifier_version=FileVerifier().version,
    )


def run_task(
    task_path: str | Path,
    response_path: str | Path,
    *,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
    run_id: str | None = None,
    experiment_id: str = DEFAULT_EXPERIMENT_ID,
    condition: Condition | None = None,
) -> RunTaskOutcome:
    """Execute one task with the baseline adapters and persist the result."""
    task = load_task(task_path)
    response_path = Path(response_path)
    store = RunStore(runs_root)
    run_id = run_id or f"run-{uuid4().hex}"
    mechanisms = condition.harness.get("mechanisms") if condition is not None else None

    run = Run(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        experiment_id=experiment_id,
        task_id=task.task_id,
        status=RunStatus.PLANNED,
        condition_manifest=_build_manifest(task, response_path, condition),
        timestamps={"created_at": utc_now()},
    )
    store.save_run(run)
    run = save_status(store, run, RunStatus.PREPARED, timestamp_key="prepared_at")

    try:
        with tempfile.TemporaryDirectory(prefix="harnessbench-") as temporary:
            workspace = Path(temporary) / "workspace"
            workspace.mkdir()

            try:
                response = FixtureModelAdapter(response_path).invoke(task.instructions)
            except ModelAdapterError as exc:
                run = finish(
                    store,
                    run,
                    RunStatus.ADAPTER_FAILED,
                    detail={"stage": "model_adapter", "message": str(exc)},
                )
                return RunTaskOutcome(run, None)

            run = save_status(store, run, RunStatus.RUNNING, timestamp_key="running_at")

            started = perf_counter()
            try:
                FileActionHarness(mechanisms=mechanisms).run(response, workspace)
            except HarnessError as exc:
                run = finish(
                    store,
                    run,
                    RunStatus.ADAPTER_FAILED,
                    detail={"stage": "harness_adapter", "message": str(exc)},
                )
                return RunTaskOutcome(run, None)
            duration_ms = round((perf_counter() - started) * 1000, 3)

            try:
                for path in sorted(workspace.rglob("*")):
                    if path.is_file():
                        relative = path.relative_to(workspace).as_posix()
                        store.save_artifact(run_id, relative, path.read_bytes())
            except OSError as exc:
                run = finish(
                    store,
                    run,
                    RunStatus.EXECUTION_FAILED,
                    detail={"stage": "artifact_collection", "message": str(exc)},
                )
                return RunTaskOutcome(run, None)

            run = save_status(
                store,
                run,
                RunStatus.COLLECTED,
                timestamp_key="collected_at",
                extra={"harness_duration_ms": duration_ms},
            )
            run = replace(run, artifact_refs=store.list_artifacts(run_id))
            store.save_run(run)

            verification = FileVerifier().verify(task, workspace)
            store.save_artifact(
                run_id,
                "verification.json",
                json_bytes(verification.to_dict()),
            )
            run = replace(
                run,
                verification_ref="verification.json",
                evidence_refs=verification.evidence_refs,
                artifact_refs=store.list_artifacts(run_id),
            )
            run = save_status(store, run, RunStatus.VERIFIED, timestamp_key="verified_at")

            final_status = verification.to_run_status()
            detail = None
            if final_status is not RunStatus.SUCCESS:
                detail = {
                    "stage": "verification",
                    "verifier_status": verification.status.value,
                    "message": verification.detail or "task verification failed",
                }
            run = finish(store, run, final_status, detail=detail)
            return RunTaskOutcome(run, verification)
    except OSError as exc:
        run = finish(
            store,
            run,
            RunStatus.SETUP_FAILED,
            detail={"stage": "workspace", "message": str(exc)},
        )
        return RunTaskOutcome(run, None)


def load_run_report(
    run_id: str,
    *,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
) -> tuple[Run, dict[str, Any] | None]:
    """Load a stored run and its verification record, if present."""
    store = RunStore(runs_root)
    run = store.load_run(run_id)
    verification = None
    if run.verification_ref is not None:
        try:
            payload = json.loads(store.read_artifact(run_id, run.verification_ref))
        except (StorageError, json.JSONDecodeError):
            payload = None
        if isinstance(payload, dict):
            verification = payload
    return run, verification
