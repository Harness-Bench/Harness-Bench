"""Unit tests for the N1 allowlist egress proxy."""

from __future__ import annotations

import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from harnessbench.runtime.network import (
    ControlledEgressProxy,
    normalize_allowlist,
)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Length", "5")
        self.end_headers()
        self.wfile.write(b"hello")

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def http_server() -> Iterator[int]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextmanager
def _echo_server() -> Iterator[int]:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def run() -> None:
        connection, _ = server.accept()
        with connection:
            while True:
                data = connection.recv(4096)
                if not data:
                    break
                connection.sendall(data)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        server.close()
        thread.join(timeout=2)


def _client(proxy: ControlledEgressProxy) -> socket.socket:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(2)
    client.connect(str(proxy.socket_path))
    return client


def _read_until(sock: socket.socket, marker: bytes) -> bytes:
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


def _read_all(sock: socket.socket) -> bytes:
    chunks = []
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def test_allowlist_normalization_matches_exact_host_and_port() -> None:
    allowlist = normalize_allowlist(
        ["Example.COM.", "127.0.0.1:8080", "[::1]:443", "example.org"]
    )

    proxy = ControlledEgressProxy(["Example.COM.", "127.0.0.1:8080"])

    try:
        assert proxy.is_allowed("example.com", 443, 443) is True
        assert proxy.is_allowed("example.com", 80, 80) is True
        assert proxy.is_allowed("example.com", 8443, 443) is False
        assert proxy.is_allowed("127.0.0.1", 8080, 80) is True
        assert proxy.is_allowed("127.0.0.1", 80, 80) is False
    finally:
        proxy.stop()

    assert allowlist == (
        ("example.com", None),
        ("127.0.0.1", 8080),
        ("::1", 443),
        ("example.org", None),
    )


def test_http_proxy_forwards_allowed_request(http_server: int) -> None:
    proxy = ControlledEgressProxy([f"127.0.0.1:{http_server}"])
    proxy.start()
    try:
        client = _client(proxy)
        try:
            client.sendall(
                (
                    f"GET http://127.0.0.1:{http_server}/ HTTP/1.1\r\n"
                    f"Host: 127.0.0.1:{http_server}\r\n"
                    "Connection: close\r\n\r\n"
                ).encode("ascii")
            )
            response = _read_all(client)
        finally:
            client.close()

        assert b"200 OK" in response
        assert response.endswith(b"hello")
        assert proxy.events == (
            {
                "method": "GET",
                "host": "127.0.0.1",
                "port": http_server,
                "allowed": True,
            },
        )
    finally:
        proxy.stop()


def test_http_proxy_denies_unlisted_host(http_server: int) -> None:
    proxy = ControlledEgressProxy(["example.com"])
    proxy.start()
    try:
        client = _client(proxy)
        try:
            client.sendall(
                (
                    f"GET http://127.0.0.1:{http_server}/ HTTP/1.1\r\n"
                    f"Host: 127.0.0.1:{http_server}\r\n"
                    "Connection: close\r\n\r\n"
                ).encode("ascii")
            )
            response = _read_all(client)
        finally:
            client.close()

        assert b"403 Forbidden" in response
        assert proxy.events[0]["allowed"] is False
        assert "allowlist" in (proxy.events[0].get("reason") or "")
    finally:
        proxy.stop()


def test_connect_tunnel_is_allowed_for_listed_port() -> None:
    with _echo_server() as echo_port:
        proxy = ControlledEgressProxy([f"127.0.0.1:{echo_port}"])
        proxy.start()
        try:
            client = _client(proxy)
            try:
                client.sendall(
                    (
                        f"CONNECT 127.0.0.1:{echo_port} HTTP/1.1\r\n"
                        f"Host: 127.0.0.1:{echo_port}\r\n\r\n"
                    ).encode("ascii")
                )
                headers = _read_until(client, b"\r\n\r\n")
                assert b"200 Connection Established" in headers

                client.sendall(b"ping")
                assert client.recv(4) == b"ping"
            finally:
                client.close()
        finally:
            proxy.stop()


@pytest.mark.parametrize(
    "entry",
    ["", " ", "example.com:notaport", "example.com:70000", "bad/host", "::1"],
)
def test_invalid_allowlist_entries_are_rejected(entry: str) -> None:
    with pytest.raises((TypeError, ValueError)):
        normalize_allowlist([entry])


def test_empty_allowlist_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one allowlist entry"):
        ControlledEgressProxy([])
