"""Integration tests for command execution through the isolated runtime."""

from __future__ import annotations

import json
import shutil
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from harnessbench.cli.command_workflows import run_command_task
from harnessbench.domain.run import RunStatus
from harnessbench.runtime.isolated import ExecutionPolicy, RuntimeStatus
from harnessbench.storage.store import RunStore
from harnessbench.verification.verifier import VerificationStatus

pytestmark = pytest.mark.skipif(
    shutil.which("bwrap") is None,
    reason="bubblewrap is not installed",
)


class _GreetingHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"hello harnessbench\n")

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def http_endpoint() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _GreetingHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_TASK_PATH = ROOT / "benchmarks" / "examples" / "echo" / "task.json"


def test_command_task_succeeds_and_persists_trace(tmp_path: Path) -> None:
    outcome = run_command_task(
        EXAMPLE_TASK_PATH,
        ["sh", "-c", "printf 'hello harnessbench\\n' > greeting.txt"],
        runs_root=tmp_path,
        run_id="run-command-success",
        policy=ExecutionPolicy(timeout_seconds=5),
    )

    assert outcome.run.status is RunStatus.SUCCESS
    assert outcome.verification is not None
    assert outcome.verification.status is VerificationStatus.PASSED
    assert outcome.runtime_result is not None
    assert outcome.runtime_result.status is RuntimeStatus.COMPLETED
    assert "runtime_trace.json" in outcome.run.artifact_refs
    assert "greeting.txt" in outcome.run.artifact_refs
    assert outcome.run.condition_manifest.runtime["isolation"] == "namespaces"
    assert outcome.run.condition_manifest.network["egress"] == "blocked"

    store = RunStore(tmp_path)
    trace = json.loads(store.read_artifact("run-command-success", "runtime_trace.json"))
    assert trace["status"] == "completed"
    assert store.read_artifact("run-command-success", "greeting.txt") == (
        b"hello harnessbench\n"
    )


def test_command_timeout_preserves_distinct_status_and_trace(tmp_path: Path) -> None:
    outcome = run_command_task(
        EXAMPLE_TASK_PATH,
        ["sh", "-c", "sleep 2"],
        runs_root=tmp_path,
        run_id="run-command-timeout",
        policy=ExecutionPolicy(timeout_seconds=0.2),
    )

    assert outcome.run.status is RunStatus.TIMED_OUT
    assert outcome.verification is None
    assert outcome.runtime_result is not None
    assert outcome.runtime_result.status is RuntimeStatus.TIMED_OUT
    assert outcome.run.failure_detail is not None
    assert outcome.run.failure_detail["runtime_status"] == "timed_out"
    assert "runtime_trace.json" in outcome.run.artifact_refs


def test_command_nonzero_exit_is_execution_failure(tmp_path: Path) -> None:
    outcome = run_command_task(
        EXAMPLE_TASK_PATH,
        ["sh", "-c", "exit 7"],
        runs_root=tmp_path,
        run_id="run-command-exit",
        policy=ExecutionPolicy(timeout_seconds=5),
    )

    assert outcome.run.status is RunStatus.EXECUTION_FAILED
    assert outcome.runtime_result is not None
    assert outcome.runtime_result.exit_code == 7
    assert outcome.run.failure_detail is not None
    assert outcome.run.failure_detail["runtime_status"] == "execution_failed"


def test_command_policy_violation_is_distinct(tmp_path: Path) -> None:
    policy = ExecutionPolicy(network_profile="N1")

    outcome = run_command_task(
        EXAMPLE_TASK_PATH,
        ["sh", "-c", "true"],
        runs_root=tmp_path,
        run_id="run-command-policy",
        policy=policy,
    )

    assert outcome.run.status is RunStatus.POLICY_VIOLATION
    assert outcome.runtime_result is not None
    assert outcome.runtime_result.status is RuntimeStatus.POLICY_VIOLATION
    assert "requires at least one allowlist entry" in (
        outcome.runtime_result.detail or ""
    )
    assert outcome.run.failure_detail is not None
    assert outcome.run.failure_detail["runtime_status"] == "policy_violation"


def test_command_network_is_blocked_offline(tmp_path: Path) -> None:
    outcome = run_command_task(
        EXAMPLE_TASK_PATH,
        [
            "python",
            "-c",
            "import socket; socket.create_connection(('1.1.1.1', 53), timeout=1)",
        ],
        runs_root=tmp_path,
        run_id="run-command-network",
        policy=ExecutionPolicy(timeout_seconds=5),
    )

    assert outcome.run.status is RunStatus.EXECUTION_FAILED
    assert outcome.runtime_result is not None
    assert "Network is unreachable" in outcome.runtime_result.stderr

    store = RunStore(tmp_path)
    trace = json.loads(store.read_artifact("run-command-network", "runtime_trace.json"))
    assert "Network is unreachable" in trace["stderr"]


def test_command_n1_allowlist_permits_listed_host(
    tmp_path: Path, http_endpoint: str
) -> None:
    port = urlsplit(http_endpoint).port
    assert port is not None
    code = (
        "import http.client; "
        "connection = http.client.HTTPConnection('127.0.0.1', 3128, timeout=2); "
        f"connection.request('GET', {http_endpoint!r}); "
        "response = connection.getresponse(); "
        "open('greeting.txt', 'wb').write(response.read())"
    )
    outcome = run_command_task(
        EXAMPLE_TASK_PATH,
        ["python", "-c", code],
        runs_root=tmp_path,
        run_id="run-command-n1",
        policy=ExecutionPolicy(
            network_profile="N1",
            network_allowlist=(f"127.0.0.1:{port}",),
            timeout_seconds=5,
        ),
    )

    assert outcome.run.status is RunStatus.SUCCESS
    assert outcome.runtime_result is not None
    assert outcome.runtime_result.status is RuntimeStatus.COMPLETED
    assert outcome.run.condition_manifest.network["profile"] == "N1"
    assert outcome.run.condition_manifest.network["egress"] == "allowlist"
    assert outcome.run.condition_manifest.network["mechanism"] == (
        "network_namespace+unix_proxy"
    )
    assert outcome.run.condition_manifest.network["allowlist"] == [
        f"127.0.0.1:{port}"
    ]
    assert outcome.run.condition_manifest.network["monitoring"] == "proxy_events"

    store = RunStore(tmp_path)
    trace = json.loads(store.read_artifact("run-command-n1", "runtime_trace.json"))
    assert trace["policy"]["network_profile"] == "N1"
    assert trace["policy"]["network_egress"] == "allowlist"
    assert trace["network_events"] == [
        {
            "method": "GET",
            "host": "127.0.0.1",
            "port": port,
            "allowed": True,
        }
    ]


def test_command_n2_profile_uses_host_network(
    tmp_path: Path, http_endpoint: str
) -> None:
    code = (
        "import urllib.request; "
        f"open('greeting.txt', 'wb').write("
        f"urllib.request.urlopen({http_endpoint!r}, timeout=2).read())"
    )
    outcome = run_command_task(
        EXAMPLE_TASK_PATH,
        ["python", "-c", code],
        runs_root=tmp_path,
        run_id="run-command-n2",
        policy=ExecutionPolicy(network_profile="N2", timeout_seconds=5),
    )

    assert outcome.run.status is RunStatus.SUCCESS
    assert outcome.runtime_result is not None
    assert outcome.runtime_result.status is RuntimeStatus.COMPLETED
    assert outcome.run.condition_manifest.network["profile"] == "N2"
    assert outcome.run.condition_manifest.network["egress"] == "host_network"
    assert outcome.run.condition_manifest.network["mechanism"] == (
        "host_network_namespace"
    )
    assert outcome.run.condition_manifest.network["monitoring"] == "none"

    store = RunStore(tmp_path)
    trace = json.loads(store.read_artifact("run-command-n2", "runtime_trace.json"))
    assert trace["policy"]["network_profile"] == "N2"
    assert trace["policy"]["network_egress"] == "host_network"


def test_command_artifacts_are_verified_task_failure(tmp_path: Path) -> None:
    outcome = run_command_task(
        EXAMPLE_TASK_PATH,
        ["sh", "-c", "printf 'wrong\\n' > greeting.txt"],
        runs_root=tmp_path,
        run_id="run-command-task-failed",
        policy=ExecutionPolicy(timeout_seconds=5),
    )

    assert outcome.runtime_result is not None
    assert outcome.runtime_result.status is RuntimeStatus.COMPLETED
    assert outcome.run.status is RunStatus.TASK_FAILED
    assert outcome.verification is not None
    assert outcome.verification.status is VerificationStatus.FAILED
