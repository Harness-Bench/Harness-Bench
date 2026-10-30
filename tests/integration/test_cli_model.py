"""Integration tests for the OpenAI-compatible model task CLI path."""

from __future__ import annotations

import json
import shutil
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from harnessbench.cli.main import main
from harnessbench.domain.run import RunStatus
from harnessbench.storage.store import RunStore

pytestmark = pytest.mark.skipif(
    shutil.which("bwrap") is None,
    reason="bubblewrap is not installed",
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_TASK_PATH = ROOT / "benchmarks" / "examples" / "echo" / "task.json"


class _Handler(BaseHTTPRequestHandler):
    response_status = 200
    response_body = b"{}"
    last_path: str | None = None
    last_headers: dict[str, str] | None = None
    last_body: bytes | None = None

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        type(self).last_path = self.path
        type(self).last_headers = dict(self.headers)
        type(self).last_body = self.rfile.read(length)
        self.send_response(type(self).response_status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(type(self).response_body)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def endpoint() -> Iterator[tuple[str, type[_Handler]]]:
    _Handler.response_status = 200
    _Handler.response_body = b"{}"
    _Handler.last_path = None
    _Handler.last_headers = None
    _Handler.last_body = None
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", _Handler
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def action_response(
    path: str,
    content: str,
    *,
    response_id: str = "chatcmpl-test",
) -> bytes:
    model_text = json.dumps(
        {"actions": [{"type": "write_file", "path": path, "content": content}]}
    )
    return json.dumps(
        {
            "id": response_id,
            "choices": [
                {
                    "message": {"role": "assistant", "content": model_text},
                    "finish_reason": "stop",
                }
            ],
        }
    ).encode("utf-8")


def test_run_model_task_cli_succeeds(
    tmp_path: Path,
    endpoint: tuple[str, type[_Handler]],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url, handler = endpoint
    handler.response_body = action_response("greeting.txt", "hello harnessbench\n")
    monkeypatch.setenv("TEST_MODEL_KEY", "super-secret-key")

    exit_code = main(
        [
            "run-model-task",
            str(EXAMPLE_TASK_PATH),
            "--endpoint",
            url,
            "--model",
            "mock-model",
            "--api-key-env",
            "TEST_MODEL_KEY",
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-model",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Run run-model: success" in captured.out
    assert "Verification: passed" in captured.out
    assert captured.err == ""

    store = RunStore(tmp_path)
    run = store.load_run("run-model")
    assert run.status is RunStatus.SUCCESS
    assert run.condition_manifest.model["provider"] == "openai-compatible"
    assert run.condition_manifest.model["name"] == "mock-model"
    assert "model_response.txt" in run.artifact_refs
    assert "model_metadata.json" in run.artifact_refs
    assert "runtime_trace.json" in run.artifact_refs
    assert store.read_artifact("run-model", "model_response.txt").startswith(b'{"actions"')
    metadata = json.loads(store.read_artifact("run-model", "model_metadata.json"))
    assert metadata["model"] == "mock-model"
    assert metadata["response_id"] == "chatcmpl-test"
    trace = json.loads(store.read_artifact("run-model", "runtime_trace.json"))
    assert trace["status"] == "completed"

    run_record = (tmp_path / "run-model" / "run.json").read_text(encoding="utf-8")
    assert "super-secret-key" not in run_record

    payload = json.loads(handler.last_body or b"{}")
    prompt = payload["messages"][0]["content"]
    assert "Create greeting.txt" in prompt
    assert "JSON object" in prompt
    headers = {key.lower(): value for key, value in (handler.last_headers or {}).items()}
    assert headers["authorization"] == "Bearer super-secret-key"


def test_run_model_task_redacts_secret_from_persisted_evidence(
    tmp_path: Path,
    endpoint: tuple[str, type[_Handler]],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url, handler = endpoint
    handler.response_body = action_response(
        "greeting.txt",
        "hello harnessbench\n",
        response_id="super-secret-key",
    )
    monkeypatch.setenv("TEST_MODEL_KEY", "super-secret-key")

    exit_code = main(
        [
            "run-model-task",
            str(EXAMPLE_TASK_PATH),
            "--endpoint",
            url,
            "--model",
            "mock-model",
            "--api-key-env",
            "TEST_MODEL_KEY",
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-model-redacted",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    store = RunStore(tmp_path)
    run_record = (tmp_path / "run-model-redacted" / "run.json").read_text(encoding="utf-8")
    assert "super-secret-key" not in run_record
    for name in (
        "model_response.txt",
        "model_metadata.json",
        "runtime_trace.json",
        "verification.json",
    ):
        content = store.read_artifact("run-model-redacted", name)
        assert b"super-secret-key" not in content
    metadata = json.loads(store.read_artifact("run-model-redacted", "model_metadata.json"))
    assert metadata["response_id"] == "[REDACTED]"


def test_run_model_task_cli_reports_invalid_actions(
    tmp_path: Path,
    endpoint: tuple[str, type[_Handler]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    url, handler = endpoint
    handler.response_body = json.dumps(
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "not a file action"},
                    "finish_reason": "stop",
                }
            ]
        }
    ).encode("utf-8")

    exit_code = main(
        [
            "run-model-task",
            str(EXAMPLE_TASK_PATH),
            "--endpoint",
            url,
            "--model",
            "mock-model",
            "--api-key-env",
            "",
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-model-invalid",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Run run-model-invalid: adapter_failed" in captured.out
    store = RunStore(tmp_path)
    run = store.load_run("run-model-invalid")
    assert run.status is RunStatus.ADAPTER_FAILED
    assert run.failure_detail is not None
    assert run.failure_detail["stage"] == "harness_adapter"
    assert "model_response.txt" in run.artifact_refs


def test_run_model_task_cli_reports_endpoint_error(
    tmp_path: Path,
    endpoint: tuple[str, type[_Handler]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    url, handler = endpoint
    handler.response_status = 503
    handler.response_body = b'{"error": "unavailable"}'

    exit_code = main(
        [
            "run-model-task",
            str(EXAMPLE_TASK_PATH),
            "--endpoint",
            url,
            "--model",
            "mock-model",
            "--api-key-env",
            "",
            "--runs-root",
            str(tmp_path),
            "--run-id",
            "run-model-error",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Run run-model-error: adapter_failed" in captured.out
    store = RunStore(tmp_path)
    run = store.load_run("run-model-error")
    assert run.status is RunStatus.ADAPTER_FAILED
    assert run.failure_detail is not None
    assert run.failure_detail["stage"] == "model_adapter"
