"""Map runtime outcomes onto persisted run statuses and failure details."""

from __future__ import annotations

from typing import Any

from harnessbench.domain.run import RunStatus
from harnessbench.runtime.isolated import RuntimeResult, RuntimeStatus

RUNTIME_STATUS_MAP = {
    RuntimeStatus.TIMED_OUT: RunStatus.TIMED_OUT,
    RuntimeStatus.RESOURCE_LIMITED: RunStatus.RESOURCE_LIMITED,
    RuntimeStatus.POLICY_VIOLATION: RunStatus.POLICY_VIOLATION,
    RuntimeStatus.SETUP_FAILED: RunStatus.SETUP_FAILED,
    RuntimeStatus.RUNTIME_UNAVAILABLE: RunStatus.SETUP_FAILED,
    RuntimeStatus.EXECUTION_FAILED: RunStatus.EXECUTION_FAILED,
}


def runtime_failure_detail(result: RuntimeResult) -> dict[str, Any]:
    """Return the persisted failure detail for a non-completed runtime result."""
    return {
        "stage": "runtime",
        "runtime_status": result.status.value,
        "message": result.detail or "runtime execution failed",
    }
