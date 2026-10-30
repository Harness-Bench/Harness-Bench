"""Tests for the OpenAI-compatible model adapter using a local mock endpoint."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from harnessbench.adapters.models.base import ModelAdapterError
from harnessbench.adapters.models.openai_compatible import OpenAICompatibleModelAdapter


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


def completion_body(content: str) -> bytes:
    return json.dumps(
        {
            "id": "chatcmpl-1",
            "choices": [
                {
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 5},
        }
    ).encode("utf-8")


def test_posts_chat_completion_and_parses_response(
    endpoint: tuple[str, type[_Handler]],
) -> None:
    url, handler = endpoint
    handler.response_body = completion_body('{"actions": []}')
    adapter = OpenAICompatibleModelAdapter(
        url,
        "mock-model",
        api_key="secret",
        timeout_seconds=5,
    )

    response = adapter.invoke("hello")

    assert response.text == '{"actions": []}'
    assert handler.last_path == "/v1/chat/completions"
    headers = {key.lower(): value for key, value in (handler.last_headers or {}).items()}
    assert headers["authorization"] == "Bearer secret"
    payload = json.loads(handler.last_body or b"{}")
    assert payload["model"] == "mock-model"
    assert payload["messages"] == [{"role": "user", "content": "hello"}]
    assert payload["temperature"] == 0.0
    assert response.metadata["response_id"] == "chatcmpl-1"
    assert response.metadata["usage"] == {"prompt_tokens": 3, "completion_tokens": 5}


def test_omits_authorization_without_api_key(
    endpoint: tuple[str, type[_Handler]],
) -> None:
    url, handler = endpoint
    handler.response_body = completion_body("ok")
    adapter = OpenAICompatibleModelAdapter(url, "mock-model", timeout_seconds=5)

    adapter.invoke("hello")

    headers = {key.lower(): value for key, value in (handler.last_headers or {}).items()}
    assert "authorization" not in headers


def test_http_error_is_reported(endpoint: tuple[str, type[_Handler]]) -> None:
    url, handler = endpoint
    handler.response_status = 500
    handler.response_body = b'{"error": "boom"}'
    adapter = OpenAICompatibleModelAdapter(url, "mock-model", timeout_seconds=5)

    with pytest.raises(ModelAdapterError, match="HTTP 500"):
        adapter.invoke("hello")


def test_invalid_json_is_reported(endpoint: tuple[str, type[_Handler]]) -> None:
    url, handler = endpoint
    handler.response_body = b"not json"
    adapter = OpenAICompatibleModelAdapter(url, "mock-model", timeout_seconds=5)

    with pytest.raises(ModelAdapterError, match="invalid JSON"):
        adapter.invoke("hello")


def test_missing_content_is_reported(endpoint: tuple[str, type[_Handler]]) -> None:
    url, handler = endpoint
    handler.response_body = b'{"choices": []}'
    adapter = OpenAICompatibleModelAdapter(url, "mock-model", timeout_seconds=5)

    with pytest.raises(ModelAdapterError, match="missing choices"):
        adapter.invoke("hello")
