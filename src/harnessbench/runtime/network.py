"""Allowlist-enforcing egress proxy used by the N1 network policy.

The sandbox runs in a private network namespace. A small TCP-to-Unix bridge
inside the sandbox forwards proxy requests to this host-side server over a
read-only Unix socket. The host server allows only exact host/port entries and
records allowed and denied attempts.
"""

from __future__ import annotations

import os
import socket
import socketserver
import tempfile
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self
from urllib.parse import urlsplit, urlunsplit

MAX_HEADER_BYTES = 64 * 1024
MAX_EGRESS_EVENTS = 10_000
CONNECT_TIMEOUT_SECONDS = 10.0
IO_TIMEOUT_SECONDS = 30.0
BRIDGE_PORT = 3128

BRIDGE_SCRIPT = '''\
"""TCP-to-Unix bridge started inside the N1 sandbox."""

import os
import socket
import sys
import threading


def pipe(reader, writer):
    try:
        while True:
            data = reader.recv(65536)
            if not data:
                break
            writer.sendall(data)
    except OSError:
        pass
    finally:
        try:
            writer.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def handle(client, upstream_path):
    upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        upstream.connect(upstream_path)
    except OSError:
        try:
            client.sendall(
                b"HTTP/1.1 502 Bad Gateway\\r\\n"
                b"Content-Length: 0\\r\\nConnection: close\\r\\n\\r\\n"
            )
        finally:
            client.close()
        return
    threading.Thread(target=pipe, args=(client, upstream), daemon=True).start()
    pipe(upstream, client)
    client.close()
    upstream.close()


def main():
    if len(sys.argv) != 5:
        raise SystemExit("usage: bridge.py SOCKET HOST PORT READY")
    path, host, port_text, ready = sys.argv[1:]
    try:
        os.unlink(ready)
    except FileNotFoundError:
        pass
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, int(port_text)))
    server.listen(64)
    with open(ready, "w", encoding="utf-8"):
        pass
    while True:
        client, _ = server.accept()
        threading.Thread(
            target=handle, args=(client, path), daemon=True
        ).start()


if __name__ == "__main__":
    main()
'''


@dataclass(frozen=True, slots=True)
class EgressEvent:
    """One proxy decision, without request paths or payloads."""

    method: str
    host: str
    port: int
    allowed: bool
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "method": self.method,
            "host": self.host,
            "port": self.port,
            "allowed": self.allowed,
        }
        if self.reason is not None:
            data["reason"] = self.reason
        return data


def _split_host_port(value: str, default_port: int | None) -> tuple[str, int | None]:
    if not isinstance(value, str):
        raise TypeError("allowlist entries must be strings")
    entry = value.strip()
    if not entry:
        raise ValueError("allowlist entries must not be empty")

    if entry.startswith("["):
        end = entry.find("]")
        if end == -1:
            raise ValueError(f"invalid IPv6 allowlist entry: {value!r}")
        host = entry[1:end]
        remainder = entry[end + 1 :]
        if remainder and not remainder.startswith(":"):
            raise ValueError(f"invalid allowlist entry: {value!r}")
        port_text = remainder[1:] if remainder else ""
    else:
        if entry.count(":") > 1:
            raise ValueError(f"IPv6 allowlist entries must be bracketed: {value!r}")
        if ":" in entry:
            host, port_text = entry.rsplit(":", 1)
        else:
            host, port_text = entry, ""

    host = host.rstrip(".").lower()
    if not host or any(character.isspace() for character in host):
        raise ValueError(f"invalid allowlist host: {value!r}")
    if any(character in host for character in "/?#"):
        raise ValueError(f"invalid allowlist host: {value!r}")

    if port_text:
        if not port_text.isdigit():
            raise ValueError(f"invalid allowlist port: {value!r}")
        port = int(port_text)
        if not 1 <= port <= 65535:
            raise ValueError(f"allowlist port is out of range: {value!r}")
    else:
        port = default_port

    return host, port


def normalize_allowlist(entries: Sequence[str]) -> tuple[tuple[str, int | None], ...]:
    """Validate and normalize exact host/port allowlist entries."""
    normalized: list[tuple[str, int | None]] = []
    for entry in entries:
        normalized.append(_split_host_port(entry, None))
    return tuple(normalized)


class _ThreadingUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    block_on_close = False
    proxy: ControlledEgressProxy


class _ProxyHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        proxy: ControlledEgressProxy = self.server.proxy  # type: ignore[attr-defined]
        request_line = self.rfile.readline(MAX_HEADER_BYTES + 1)
        if not request_line:
            return
        if len(request_line) > MAX_HEADER_BYTES:
            self._respond(431, "Request Header Fields Too Large")
            return

        headers: list[bytes] = []
        total = len(request_line)
        while True:
            line = self.rfile.readline(MAX_HEADER_BYTES + 1)
            if not line:
                break
            total += len(line)
            if total > MAX_HEADER_BYTES:
                self._respond(431, "Request Header Fields Too Large")
                return
            if line in (b"\r\n", b"\n"):
                break
            headers.append(line)

        try:
            method, target, version = request_line.decode("iso-8859-1").strip().split(
                " ", 2
            )
        except ValueError:
            self._respond(400, "Bad Request")
            return

        if method.upper() == "CONNECT":
            self._handle_connect(proxy, method, target)
            return
        self._handle_http(proxy, method, target, version, headers)

    def _handle_connect(
        self, proxy: ControlledEgressProxy, method: str, target: str
    ) -> None:
        try:
            host, port = _split_host_port(target, 443)
        except ValueError:
            self._respond(400, "Bad Request")
            return
        assert port is not None
        if not proxy.is_allowed(host, port, 443):
            proxy.record(method, host, port, False, "host is not in the allowlist")
            self._respond(403, "Forbidden")
            return
        try:
            upstream = socket.create_connection(
                (host, port), timeout=proxy.connect_timeout_seconds
            )
        except OSError as exc:
            proxy.record(method, host, port, False, f"connect failed: {exc}")
            self._respond(502, "Bad Gateway")
            return

        proxy.record(method, host, port, True)
        self.connection.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        self._relay(upstream)
        self._close_client()

    def _handle_http(
        self,
        proxy: ControlledEgressProxy,
        method: str,
        target: str,
        version: str,
        headers: list[bytes],
    ) -> None:
        try:
            parsed = urlsplit(target)
        except ValueError:
            self._respond(400, "Bad Request")
            return
        if parsed.scheme.lower() != "http" or parsed.hostname is None:
            self._respond(400, "Bad Request")
            return
        host = parsed.hostname.rstrip(".").lower()
        try:
            port = parsed.port or 80
        except ValueError:
            self._respond(400, "Bad Request")
            return
        if not proxy.is_allowed(host, port, 80):
            proxy.record(method, host, port, False, "host is not in the allowlist")
            self._respond(403, "Forbidden")
            return
        try:
            upstream = socket.create_connection(
                (host, port), timeout=proxy.connect_timeout_seconds
            )
        except OSError as exc:
            proxy.record(method, host, port, False, f"connect failed: {exc}")
            self._respond(502, "Bad Gateway")
            return

        path = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        forwarded = [f"{method} {path} {version}\r\n".encode("iso-8859-1")]
        for line in headers:
            name = line.split(b":", 1)[0].strip().lower()
            if name in (b"proxy-connection", b"connection", b"proxy-authorization"):
                continue
            forwarded.append(line)
        forwarded.append(b"Connection: close\r\n\r\n")
        try:
            upstream.sendall(b"".join(forwarded))
        except OSError:
            proxy.record(method, host, port, False, "upstream closed")
            self._respond(502, "Bad Gateway")
            upstream.close()
            return
        proxy.record(method, host, port, True)
        self._relay(upstream)
        self._close_client()

    def _relay(self, upstream: socket.socket) -> None:
        proxy: ControlledEgressProxy = self.server.proxy  # type: ignore[attr-defined]
        upstream.settimeout(proxy.io_timeout_seconds)
        self.connection.settimeout(proxy.io_timeout_seconds)
        thread = threading.Thread(
            target=self._client_to_upstream,
            args=(upstream,),
            daemon=True,
        )
        thread.start()
        try:
            while True:
                data = upstream.recv(65536)
                if not data:
                    break
                self.connection.sendall(data)
        except OSError:
            pass
        finally:
            try:
                upstream.close()
            except OSError:
                pass

    def _close_client(self) -> None:
        try:
            self.connection.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        try:
            self.connection.close()
        except OSError:
            pass

    def _client_to_upstream(self, upstream: socket.socket) -> None:
        try:
            while True:
                data = self.rfile.read1(65536)
                if not data:
                    break
                upstream.sendall(data)
        except OSError:
            pass
        finally:
            try:
                upstream.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    def _respond(self, status: int, message: str) -> None:
        body = message.encode("ascii", errors="replace")
        response = (
            f"HTTP/1.1 {status} {message}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "\r\n"
        ).encode("ascii") + body
        try:
            self.connection.sendall(response)
        except OSError:
            pass


class ControlledEgressProxy:
    """Host-side allowlist proxy reached through a sandbox-mounted Unix socket."""

    def __init__(
        self,
        allowlist: Sequence[str],
        *,
        connect_timeout_seconds: float = CONNECT_TIMEOUT_SECONDS,
        io_timeout_seconds: float = IO_TIMEOUT_SECONDS,
    ) -> None:
        normalized = normalize_allowlist(allowlist)
        if not normalized:
            raise ValueError("N1 requires at least one allowlist entry")
        if connect_timeout_seconds <= 0:
            raise ValueError("connect_timeout_seconds must be positive")
        if io_timeout_seconds <= 0:
            raise ValueError("io_timeout_seconds must be positive")

        self._allowlist = normalized
        self.connect_timeout_seconds = connect_timeout_seconds
        self.io_timeout_seconds = io_timeout_seconds
        self._events: list[EgressEvent] = []
        self._lock = threading.Lock()
        self._temporary = tempfile.TemporaryDirectory(prefix="harnessbench-egress-")
        try:
            self.directory = Path(self._temporary.name)
            self.socket_path = self.directory / "proxy.sock"
            self.bridge_path = self.directory / "bridge.py"
            self.bridge_path.write_text(BRIDGE_SCRIPT, encoding="utf-8")
            self.bridge_path.chmod(0o600)
            self._server = _ThreadingUnixServer(str(self.socket_path), _ProxyHandler)
            self._server.proxy = self
            os.chmod(self.socket_path, 0o600)
        except Exception:
            self._temporary.cleanup()
            raise
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="harnessbench-egress",
            daemon=True,
        )
        self._started = False
        self._closed = False

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.stop()

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(event.to_dict() for event in self._events)

    def start(self) -> None:
        if self._closed:
            raise RuntimeError("egress proxy has already been stopped")
        if not self._started:
            self._thread.start()
            self._started = True

    def stop(self) -> None:
        if self._closed:
            return
        if self._started:
            self._server.shutdown()
            self._started = False
        self._server.server_close()
        self._closed = True
        self._temporary.cleanup()

    def is_allowed(self, host: str, port: int, default_port: int) -> bool:
        normalized_host = host.rstrip(".").lower()
        for allowed_host, allowed_port in self._allowlist:
            if allowed_host != normalized_host:
                continue
            if allowed_port is None:
                if port == default_port:
                    return True
            elif allowed_port == port:
                return True
        return False

    def record(
        self,
        method: str,
        host: str,
        port: int,
        allowed: bool,
        reason: str | None = None,
    ) -> None:
        event = EgressEvent(
            method=method.upper(),
            host=host.rstrip(".").lower(),
            port=port,
            allowed=allowed,
            reason=reason,
        )
        with self._lock:
            if len(self._events) < MAX_EGRESS_EVENTS:
                self._events.append(event)
