"""Application workflows invoked by the CLI; argument parsing stays in main."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from harnessbench.adapters.harnesses.base import HarnessError
from harnessbench.adapters.harnesses.file_actions import FileActionHarness
from harnessbench.adapters.models.base import ModelAdapter, ModelAdapterError
from harnessbench.adapters.models.fixture import FixtureModelAdapter
from harnessbench.cli.run_lifecycle import finish, json_bytes, save_status, utc_now
from harnessbench.cli.runtime_outcomes import RUNTIME_STATUS_MAP, runtime_failure_detail
from harnessbench.domain.experiment import Condition
from harnessbench.domain.run import ConditionManifest, Run, RunStatus
from harnessbench.domain.task import Task
from harnessbench.registry.loader import load_task
from harnessbench.runtime.isolated import (
    ExecutionPolicy,
    IsolatedRuntime,
    RuntimeSetupError,
    RuntimeStatus,
)
from harnessbench.storage.store import RunStore, StorageError
from harnessbench.verification.verifier import FileVerifier, VerificationResult

DEFAULT_RUNS_ROOT = Path("runs")
DEFAULT_EXPERIMENT_ID = "experiment-local"
SCHEMA_VERSION = "0.1.0"
RUNTIME_VERSION = "0.1.0"
ACTION_PROTOCOL = (
    "\n\nReturn only a JSON object describing file actions, with no Markdown "
    "fences or commentary:\n"
    '{"actions": [{"type": "write_file", "path": "relative/path", '
    '"content": "exact text"}]}\n'
    "Paths must be relative to the workspace."
)


@dataclass(frozen=True, slots=True)
class RunTaskOutcome:
    """Persisted run plus the verifier result when verification was reached."""

    run: Run
    verification: VerificationResult | None


def _wall_seconds(budgets: Mapping[str, Any] | None) -> float:
    if budgets is not None:
        value = budgets.get("wall_seconds")
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return 30.0


def _execution_policy(task: Task, condition: Condition | None) -> ExecutionPolicy:
    network = condition.network if condition is not None else {}
    profile = network.get("profile", task.network_profile or "N0")
    if not isinstance(profile, str) or not profile:
        profile = task.network_profile or "N0"

    raw_allowlist = network.get("allowlist", ())
    allowlist: tuple[str, ...] = ()
    if isinstance(raw_allowlist, Sequence) and not isinstance(raw_allowlist, str):
        allowlist = tuple(str(entry) for entry in raw_allowlist)

    budgets = condition.budgets if condition is not None else task.budgets
    return ExecutionPolicy(
        timeout_seconds=_wall_seconds(budgets),
        network_profile=profile,
        network_allowlist=allowlist,
    )


def _network_manifest(policy: ExecutionPolicy) -> dict[str, Any]:
    return {
        "profile": policy.network_profile,
        "egress": policy.network_egress,
        "mechanism": policy.network_mechanism,
        "allowlist": sorted(policy.network_allowlist),
        "monitoring": {
            "N0": "not_applicable",
            "N1": "proxy_events",
            "N2": "none",
        }.get(policy.network_profile, "none"),
    }


def _build_manifest(
    task: Task,
    response_path: Path | None,
    condition: Condition | None,
    model_manifest: Mapping[str, Any] | None,
    policy: ExecutionPolicy,
) -> ConditionManifest:
    if condition is not None:
        return condition.to_manifest()
    if model_manifest is not None:
        model = dict(model_manifest)
    else:
        if response_path is None:
            raise ValueError("response_path is required without a model manifest")
        model = {
            "provider": "fixture",
            "name": "recorded-response",
            "revision": "0.1.0",
            "response_path": str(response_path),
        }
    return ConditionManifest(
        model=model,
        harness={"name": "file-actions", "version": FileActionHarness.version},
        runtime={
            "name": "bubblewrap",
            "version": RUNTIME_VERSION,
            "isolation": "namespaces",
            "limits": "enforced",
        },
        environment={"profile": task.environment_level, "workspace": "temporary"},
        network=_network_manifest(policy),
        budgets={
            "wall_seconds": policy.timeout_seconds,
            "cpu_seconds": policy.cpu_seconds,
            "memory_mb": policy.memory_mb,
            "max_file_size_mb": policy.max_file_size_mb,
            "max_processes": policy.max_processes,
        },
        language_profile=task.language_profile,
        verifier_version=FileVerifier().version,
    )


def run_task(
    task_path: str | Path,
    response_path: str | Path | None = None,
    *,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
    run_id: str | None = None,
    experiment_id: str = DEFAULT_EXPERIMENT_ID,
    condition: Condition | None = None,
    model_adapter: ModelAdapter | None = None,
    model_manifest: Mapping[str, Any] | None = None,
    prompt_suffix: str | None = None,
    store_model_response: bool = False,
    secrets: Sequence[str] = (),
) -> RunTaskOutcome:
    """Execute one task with the baseline adapters and persist the result."""
    task = load_task(task_path)
    response_path = Path(response_path) if response_path is not None else None
    if model_adapter is None and response_path is None:
        raise ValueError("response_path is required for the fixture adapter")
    policy = _execution_policy(task, condition)
    store = RunStore(runs_root, secrets=secrets)
    run_id = run_id or f"run-{uuid4().hex}"
    mechanisms = condition.harness.get("mechanisms") if condition is not None else None

    run = Run(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        experiment_id=experiment_id,
        task_id=task.task_id,
        status=RunStatus.PLANNED,
        condition_manifest=_build_manifest(
            task,
            response_path,
            condition,
            model_manifest,
            policy,
        ),
        timestamps={"created_at": utc_now()},
    )
    store.save_run(run)
    run = save_status(store, run, RunStatus.PREPARED, timestamp_key="prepared_at")

    runtime = IsolatedRuntime(policy)
    try:
        workspace = runtime.prepare(task.initial_state)

        prompt = task.instructions + (prompt_suffix or "")
        try:
            if model_adapter is None:
                assert response_path is not None
                active_adapter: ModelAdapter = FixtureModelAdapter(response_path)
            else:
                active_adapter = model_adapter
            response = active_adapter.invoke(prompt)
        except ModelAdapterError as exc:
            run = finish(
                store,
                run,
                RunStatus.ADAPTER_FAILED,
                detail={"stage": "model_adapter", "message": str(exc)},
            )
            return RunTaskOutcome(run, None)

        if store_model_response:
            store.save_artifact(
                run_id,
                "model_response.txt",
                response.text.encode("utf-8"),
            )
            if response.metadata:
                store.save_artifact(
                    run_id,
                    "model_metadata.json",
                    json_bytes(dict(response.metadata)),
                )
            run = replace(run, artifact_refs=store.list_artifacts(run_id))
            store.save_run(run)

        run = save_status(store, run, RunStatus.RUNNING, timestamp_key="running_at")

        started = perf_counter()
        try:
            harness = FileActionHarness(mechanisms=mechanisms)
            planned = harness.plan(response, workspace)
            runtime_result = harness.execute(planned, runtime)
        except HarnessError as exc:
            run = finish(
                store,
                run,
                RunStatus.ADAPTER_FAILED,
                detail={"stage": "harness_adapter", "message": str(exc)},
            )
            return RunTaskOutcome(run, None)
        duration_ms = round((perf_counter() - started) * 1000, 3)

        store.save_artifact(run_id, "runtime_trace.json", json_bytes(runtime_result.to_dict()))
        run = replace(run, artifact_refs=store.list_artifacts(run_id))
        store.save_run(run)

        if runtime_result.status is not RuntimeStatus.COMPLETED:
            status = RUNTIME_STATUS_MAP.get(
                runtime_result.status,
                RunStatus.EXECUTION_FAILED,
            )
            run = finish(
                store,
                run,
                status,
                detail=runtime_failure_detail(runtime_result),
            )
            return RunTaskOutcome(run, None)

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
    except (RuntimeSetupError, OSError) as exc:
        run = finish(
            store,
            run,
            RunStatus.SETUP_FAILED,
            detail={"stage": "workspace", "message": str(exc)},
        )
        return RunTaskOutcome(run, None)
    finally:
        runtime.cleanup()


def run_model_task(
    task_path: str | Path,
    *,
    adapter: ModelAdapter,
    model_manifest: Mapping[str, Any],
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
    run_id: str | None = None,
    experiment_id: str = DEFAULT_EXPERIMENT_ID,
    condition: Condition | None = None,
    secrets: Sequence[str] = (),
) -> RunTaskOutcome:
    """Invoke a model adapter, apply its file actions, and verify the result."""
    return run_task(
        task_path,
        None,
        runs_root=runs_root,
        run_id=run_id,
        experiment_id=experiment_id,
        condition=condition,
        model_adapter=adapter,
        model_manifest=model_manifest,
        prompt_suffix=ACTION_PROTOCOL,
        store_model_response=True,
        secrets=secrets,
    )


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
