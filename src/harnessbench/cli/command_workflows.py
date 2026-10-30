"""Run a command task inside the isolated runtime and persist its evidence."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from harnessbench.adapters.harnesses.command import CommandHarness
from harnessbench.cli.run_lifecycle import finish, json_bytes, save_status, utc_now
from harnessbench.cli.workflows import DEFAULT_EXPERIMENT_ID, DEFAULT_RUNS_ROOT
from harnessbench.domain.run import ConditionManifest, Run, RunStatus
from harnessbench.domain.task import Task
from harnessbench.registry.loader import load_task
from harnessbench.runtime.isolated import (
    ExecutionPolicy,
    RuntimeResult,
    RuntimeSetupError,
    RuntimeStatus,
)
from harnessbench.storage.store import RunStore
from harnessbench.verification.verifier import FileVerifier, VerificationResult

SCHEMA_VERSION = "0.1.0"
RUNTIME_VERSION = "0.1.0"

RUNTIME_STATUS_MAP = {
    RuntimeStatus.TIMED_OUT: RunStatus.TIMED_OUT,
    RuntimeStatus.RESOURCE_LIMITED: RunStatus.RESOURCE_LIMITED,
    RuntimeStatus.POLICY_VIOLATION: RunStatus.POLICY_VIOLATION,
    RuntimeStatus.SETUP_FAILED: RunStatus.SETUP_FAILED,
    RuntimeStatus.RUNTIME_UNAVAILABLE: RunStatus.SETUP_FAILED,
    RuntimeStatus.EXECUTION_FAILED: RunStatus.EXECUTION_FAILED,
}


@dataclass(frozen=True, slots=True)
class RunCommandOutcome:
    """Persisted run, verifier result, and captured runtime trace."""

    run: Run
    verification: VerificationResult | None
    runtime_result: RuntimeResult | None


def _build_manifest(
    task: Task, command: Sequence[str], policy: ExecutionPolicy
) -> ConditionManifest:
    return ConditionManifest(
        model={"provider": "none", "name": "command", "revision": "0.1.0"},
        harness={
            "name": "command",
            "version": CommandHarness.version,
            "command": list(command),
        },
        runtime={
            "name": "bubblewrap",
            "version": RUNTIME_VERSION,
            "isolation": "namespaces",
            "limits": "enforced",
        },
        environment={"profile": task.environment_level, "workspace": "temporary"},
        network={
            "profile": policy.network_profile,
            "egress": policy.network_egress,
            "mechanism": policy.network_mechanism,
            "allowlist": sorted(policy.network_allowlist),
            "monitoring": {
                "N0": "not_applicable",
                "N1": "proxy_events",
                "N2": "none",
            }.get(policy.network_profile, "none"),
        },
        budgets={
            "wall_seconds": policy.timeout_seconds,
            "cpu_seconds": policy.cpu_seconds,
            "memory_mb": policy.memory_mb,
            "max_file_size_mb": policy.max_file_size_mb,
            "max_processes": policy.max_processes,
        },
        language_profile=task.language_profile,
        verifier_version=FileVerifier().version,
        condition_id="command",
    )


def _collect_artifacts(store: RunStore, run_id: str, workspace: Path) -> tuple[str, ...]:
    for path in sorted(workspace.rglob("*")):
        if path.is_file():
            relative = path.relative_to(workspace).as_posix()
            store.save_artifact(run_id, relative, path.read_bytes())
    return store.list_artifacts(run_id)


def _runtime_failure_detail(result: RuntimeResult) -> dict[str, Any]:
    return {
        "stage": "runtime",
        "runtime_status": result.status.value,
        "message": result.detail or "runtime execution failed",
    }


def run_command_task(
    task_path: str | Path,
    command: Sequence[str],
    *,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
    run_id: str | None = None,
    experiment_id: str = DEFAULT_EXPERIMENT_ID,
    policy: ExecutionPolicy | None = None,
) -> RunCommandOutcome:
    """Execute a command task under the isolated runtime and verify artifacts."""
    task = load_task(task_path)
    active_policy = policy or ExecutionPolicy()
    store = RunStore(runs_root)
    run_id = run_id or f"run-{uuid4().hex}"

    run = Run(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        experiment_id=experiment_id,
        task_id=task.task_id,
        status=RunStatus.PLANNED,
        condition_manifest=_build_manifest(task, command, active_policy),
        timestamps={"created_at": utc_now()},
    )
    store.save_run(run)
    run = save_status(store, run, RunStatus.PREPARED, timestamp_key="prepared_at")

    try:
        with CommandHarness(command, active_policy) as harness:
            harness.prepare(task.initial_state)
            run = save_status(store, run, RunStatus.RUNNING, timestamp_key="running_at")
            result = harness.run()
            store.save_artifact(run_id, "runtime_trace.json", json_bytes(result.to_dict()))

            try:
                artifact_refs = _collect_artifacts(store, run_id, harness.workspace)
            except OSError as exc:
                run = finish(
                    store,
                    run,
                    RunStatus.EXECUTION_FAILED,
                    detail={"stage": "artifact_collection", "message": str(exc)},
                )
                return RunCommandOutcome(run, None, result)

            run = replace(run, artifact_refs=artifact_refs)
            store.save_run(run)

            if result.status is not RuntimeStatus.COMPLETED:
                status = RUNTIME_STATUS_MAP.get(result.status, RunStatus.EXECUTION_FAILED)
                run = finish(
                    store,
                    run,
                    status,
                    detail=_runtime_failure_detail(result),
                )
                return RunCommandOutcome(run, None, result)

            run = save_status(
                store,
                run,
                RunStatus.COLLECTED,
                timestamp_key="collected_at",
                extra={"harness_duration_ms": result.duration_ms},
            )
            verification = FileVerifier().verify(task, harness.workspace)
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
            return RunCommandOutcome(run, verification, result)
    except (RuntimeSetupError, OSError) as exc:
        run = finish(
            store,
            run,
            RunStatus.SETUP_FAILED,
            detail={"stage": "workspace", "message": str(exc)},
        )
        return RunCommandOutcome(run, None, None)
