"""Integration tests for the isolated runtime."""

from __future__ import annotations

import shutil
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

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


class _GreetingHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"n2-ok")

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


def test_allowlist_requires_n1_profile() -> None:
    with pytest.raises(ValueError, match="only valid for the N1 profile"):
        ExecutionPolicy(
            network_profile="N2",
            network_allowlist=("example.com",),
        )


def test_n1_without_allowlist_is_a_policy_violation() -> None:
    policy = ExecutionPolicy(network_profile="N1", timeout_seconds=5)
    with IsolatedRuntime(policy) as runtime:
        runtime.prepare()

        result = runtime.execute(["sh", "-c", "true"])

        assert result.status is RuntimeStatus.POLICY_VIOLATION
        assert "requires at least one allowlist entry" in (result.detail or "")
        assert result.policy["network_egress"] == "allowlist"
        assert result.network_events == ()


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


def test_n2_profile_uses_host_network(http_endpoint: str) -> None:
    policy = ExecutionPolicy(network_profile="N2", timeout_seconds=5)
    code = (
        "import urllib.request; "
        f"print(urllib.request.urlopen({http_endpoint!r}, timeout=2).read().decode())"
    )
    with IsolatedRuntime(policy) as runtime:
        runtime.prepare()

        result = runtime.execute(["python", "-c", code])

        assert result.status is RuntimeStatus.COMPLETED
        assert result.stdout == "n2-ok\n"
        assert result.policy["network_profile"] == "N2"
        assert result.policy["network_egress"] == "host_network"
        assert result.policy["network_mechanism"] == "host_network_namespace"


def _proxy_get_code(url: str) -> str:
    return (
        "import http.client; "
        "connection = http.client.HTTPConnection('127.0.0.1', 3128, timeout=2); "
        f"connection.request('GET', {url!r}); "
        "response = connection.getresponse(); "
        "print(response.status); "
        "print(response.read().decode(), end='')"
    )


def test_n1_allowlist_permits_listed_host(http_endpoint: str) -> None:
    port = urlsplit(http_endpoint).port
    assert port is not None
    policy = ExecutionPolicy(
        network_profile="N1",
        network_allowlist=(f"127.0.0.1:{port}",),
        timeout_seconds=5,
    )
    with IsolatedRuntime(policy) as runtime:
        runtime.prepare()

        result = runtime.execute(["python", "-c", _proxy_get_code(http_endpoint)])

        assert result.status is RuntimeStatus.COMPLETED
        assert result.stdout == "200\nn2-ok"
        assert result.policy["network_mechanism"] == "network_namespace+unix_proxy"
        assert result.network_events == (
            {
                "method": "GET",
                "host": "127.0.0.1",
                "port": port,
                "allowed": True,
            },
        )


def test_n1_blocks_direct_host_network(http_endpoint: str) -> None:
    port = urlsplit(http_endpoint).port
    assert port is not None
    policy = ExecutionPolicy(
        network_profile="N1",
        network_allowlist=(f"127.0.0.1:{port}",),
        timeout_seconds=5,
    )
    code = (
        "import socket; "
        f"socket.create_connection(('127.0.0.1', {port}), timeout=1)"
    )
    with IsolatedRuntime(policy) as runtime:
        runtime.prepare()

        result = runtime.execute(["python", "-c", code])

        assert result.status is RuntimeStatus.EXECUTION_FAILED
        assert "Connection refused" in result.stderr
        assert result.network_events == ()


def test_n1_allowlist_denies_unlisted_host(http_endpoint: str) -> None:
    policy = ExecutionPolicy(
        network_profile="N1",
        network_allowlist=("example.com",),
        timeout_seconds=5,
    )
    with IsolatedRuntime(policy) as runtime:
        runtime.prepare()

        result = runtime.execute(["python", "-c", _proxy_get_code(http_endpoint)])

        assert result.status is RuntimeStatus.COMPLETED
        assert result.stdout == "403\nForbidden"
        assert result.network_events[0]["allowed"] is False
        assert "allowlist" in (result.network_events[0].get("reason") or "")


def test_trace_includes_policy_limits() -> None:
    policy = ExecutionPolicy(timeout_seconds=5, memory_mb=256)
    with IsolatedRuntime(policy) as runtime:
        runtime.prepare()

        result = runtime.execute(["sh", "-c", "true"])

        assert result.to_dict()["policy"]["timeout_seconds"] == 5
        assert result.to_dict()["policy"]["memory_mb"] == 256
        assert result.to_dict()["policy"]["network_egress"] == "blocked"


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
