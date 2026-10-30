"""Integration tests for the isolated command CLI path."""

from __future__ import annotations

import shutil
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from harnessbench.cli.main import main

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


def test_run_command_cli_succeeds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "run-command",
            str(EXAMPLE_TASK_PATH),
            "--command",
            "sh -c \"printf 'hello harnessbench\\n' > greeting.txt\"",
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-command",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Run run-command: success" in captured.out
    assert "Runtime: completed" in captured.out
    assert "Verification: passed" in captured.out
    assert captured.err == ""


def test_run_command_cli_timeout_returns_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "run-command",
            str(EXAMPLE_TASK_PATH),
            "--command",
            "sh -c 'sleep 2'",
            "--timeout",
            "0.2",
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-command-timeout",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Run run-command-timeout: timed_out" in captured.out
    assert "Runtime: timed_out" in captured.out


def test_run_command_cli_rejects_invalid_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "run-command",
            str(EXAMPLE_TASK_PATH),
            "--command",
            "'",
            "--runs-root",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "invalid command" in captured.err


def test_run_command_cli_n1_without_allowlist_is_policy_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "run-command",
            str(EXAMPLE_TASK_PATH),
            "--command",
            "sh -c 'true'",
            "--network-profile",
            "N1",
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-command-n1",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Run run-command-n1: policy_violation" in captured.out
    assert "requires at least one allowlist entry" in captured.out


def test_run_command_cli_n1_allow_host(
    tmp_path: Path,
    http_endpoint: str,
    capsys: pytest.CaptureFixture[str],
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

    exit_code = main(
        [
            "run-command",
            str(EXAMPLE_TASK_PATH),
            "--command",
            f"python3 -c \"{code}\"",
            "--network-profile",
            "N1",
            "--allow-host",
            f"127.0.0.1:{port}",
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-command-n1-allowed",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Run run-command-n1-allowed: success" in captured.out
    assert "Verification: passed" in captured.out


def test_show_run_includes_runtime_trace_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(
        [
            "run-command",
            str(EXAMPLE_TASK_PATH),
            "--command",
            "sh -c \"printf 'hello harnessbench\\n' > greeting.txt\"",
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-command",
        ]
    )
    capsys.readouterr()

    exit_code = main(["show-run", "run-command", "--runs-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Run run-command: success" in captured.out
    assert "runtime_trace.json" in captured.out
