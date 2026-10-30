"""Integration tests for the isolated runtime."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

from harnessbench.runtime.isolated import (
    ExecutionPolicy,
    IsolatedRuntime,
    RuntimeStatus,
)

pytestmark = pytest.mark.skipif(
    shutil.which("bwrap") is None,
    reason="bubblewrap is not installed",
)


def test_executes_in_workspace_and_captures_trace() -> None:
    with IsolatedRuntime() as runtime:
        runtime.prepare({"files": {"seed.txt": "one\n"}})

        result = runtime.execute(
            ["sh", "-c", "cat seed.txt; echo two > output.txt; echo err >&2"]
        )

        assert result.status is RuntimeStatus.COMPLETED
        assert result.exit_code == 0
        assert result.stdout == "one\n"
        assert result.stderr == "err\n"
        assert (runtime.workspace / "output.txt").read_text(encoding="utf-8") == "two\n"
        assert result.to_dict()["status"] == "completed"


def test_reset_restores_declared_initial_state() -> None:
    initial_state = {"files": {"seed.txt": "one\n"}}
    with IsolatedRuntime() as runtime:
        runtime.prepare(initial_state)
        runtime.execute(["sh", "-c", "echo extra > extra.txt"])
        assert (runtime.workspace / "extra.txt").exists()

        runtime.reset(initial_state)

        assert (runtime.workspace / "seed.txt").read_text(encoding="utf-8") == "one\n"
        assert not (runtime.workspace / "extra.txt").exists()


def test_timeout_is_distinct_from_execution_failure() -> None:
    policy = ExecutionPolicy(timeout_seconds=0.2)
    with IsolatedRuntime(policy) as runtime:
        runtime.prepare()
        started = time.perf_counter()

        result = runtime.execute(["sh", "-c", "sleep 2"])

        assert result.status is RuntimeStatus.TIMED_OUT
        assert time.perf_counter() - started < 1.5
        assert result.detail == "wall-clock timeout exceeded"


def test_nonzero_exit_is_execution_failure() -> None:
    with IsolatedRuntime() as runtime:
        runtime.prepare()

        result = runtime.execute(["sh", "-c", "exit 7"])

        assert result.status is RuntimeStatus.EXECUTION_FAILED
        assert result.exit_code == 7


def test_setup_failure_when_workspace_is_missing() -> None:
    runtime = IsolatedRuntime()

    result = runtime.execute(["sh", "-c", "true"])

    assert result.status is RuntimeStatus.SETUP_FAILED
    assert result.exit_code is None


def test_unsupported_network_policy_is_a_policy_violation() -> None:
    policy = ExecutionPolicy(
        network_profile="N1",
        allowed_network_profiles=frozenset({"N0", "N1"}),
    )
    with IsolatedRuntime(policy) as runtime:
        runtime.prepare()

        result = runtime.execute(["sh", "-c", "true"])

        assert result.status is RuntimeStatus.POLICY_VIOLATION
        assert "does not support network profile" in (result.detail or "")


def test_network_is_blocked_offline() -> None:
    with IsolatedRuntime() as runtime:
        runtime.prepare()

        result = runtime.execute(
            [
                "python",
                "-c",
                "import socket; socket.create_connection(('1.1.1.1', 53), timeout=1)",
            ]
        )

        assert result.status is RuntimeStatus.EXECUTION_FAILED
        assert "Network is unreachable" in result.stderr


def test_writes_outside_workspace_are_blocked() -> None:
    host_path = Path("/etc/harnessbench-runtime-escape")
    with IsolatedRuntime() as runtime:
        runtime.prepare()

        result = runtime.execute(
            ["sh", "-c", f"echo nope > {host_path}"]
        )

        assert result.status is RuntimeStatus.EXECUTION_FAILED
        assert not host_path.exists()


def test_cleanup_removes_workspace() -> None:
    runtime = IsolatedRuntime()
    workspace = runtime.prepare({"files": {"seed.txt": "one\n"}})

    runtime.cleanup()

    assert not workspace.exists()
    assert runtime.workspace is None


def test_file_size_limit_is_classified() -> None:
    policy = ExecutionPolicy(max_file_size_mb=1, timeout_seconds=5)
    with IsolatedRuntime(policy) as runtime:
        runtime.prepare()

        result = runtime.execute(
            ["sh", "-c", "dd if=/dev/zero of=big.bin bs=1M count=4"]
        )

        assert result.status is RuntimeStatus.RESOURCE_LIMITED
