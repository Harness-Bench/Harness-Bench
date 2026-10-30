"""Isolated subprocess runtime using bubblewrap where available."""

from __future__ import annotations

import os
import resource
import shutil
import signal
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import Any, Self

from harnessbench.runtime.network import (
    BRIDGE_PORT,
    ControlledEgressProxy,
    normalize_allowlist,
)


class RuntimeStatus(StrEnum):
    """Outcome of one runtime execution."""

    COMPLETED = "completed"
    EXECUTION_FAILED = "execution_failed"
    TIMED_OUT = "timed_out"
    RESOURCE_LIMITED = "resource_limited"
    SETUP_FAILED = "setup_failed"
    POLICY_VIOLATION = "policy_violation"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"


class RuntimeSetupError(Exception):
    """The runtime workspace or initial state could not be prepared."""


SUPPORTED_NETWORK_PROFILES = frozenset({"N0", "N1", "N2"})

_PROXY_WRAPPER = (
    "python3 /egress/bridge.py /egress/proxy.sock 127.0.0.1 "
    f"{BRIDGE_PORT} /tmp/.harnessbench-proxy-ready & "
    "attempts=0; "
    "while [ ! -e /tmp/.harnessbench-proxy-ready ] && [ $attempts -lt 500 ]; do "
    "attempts=$((attempts+1)); sleep 0.01; done; "
    "[ -e /tmp/.harnessbench-proxy-ready ] || exit 1; "
    'exec "$@"'
)


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    """Declared limits and network policy for one execution."""

    timeout_seconds: float = 30.0
    cpu_seconds: int = 10
    memory_mb: int = 512
    max_processes: int = 2048
    max_file_size_mb: int = 16
    network_profile: str = "N0"
    network_allowlist: tuple[str, ...] = ()
    allowed_network_profiles: frozenset[str] = field(
        default_factory=lambda: frozenset({"N0", "N1", "N2"})
    )
    max_output_chars: int = 100_000

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        for name in ("cpu_seconds", "memory_mb", "max_processes", "max_file_size_mb"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.network_profile not in self.allowed_network_profiles:
            raise ValueError(
                f"network profile {self.network_profile} is not allowed; "
                f"allowed: {sorted(self.allowed_network_profiles)}"
            )
        if self.network_allowlist and self.network_profile != "N1":
            raise ValueError("network_allowlist is only valid for the N1 profile")
        normalize_allowlist(self.network_allowlist)

    @property
    def network_supported(self) -> bool:
        return self.network_profile in SUPPORTED_NETWORK_PROFILES

    @property
    def network_egress(self) -> str:
        if self.network_profile == "N0":
            return "blocked"
        if self.network_profile == "N1":
            return "allowlist"
        if self.network_profile == "N2":
            return "host_network"
        return "unsupported"

    @property
    def network_mechanism(self) -> str:
        if self.network_profile == "N0":
            return "network_namespace"
        if self.network_profile == "N1":
            return "network_namespace+unix_proxy"
        if self.network_profile == "N2":
            return "host_network_namespace"
        return "none"

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable policy snapshot for traces and manifests."""
        return {
            "timeout_seconds": self.timeout_seconds,
            "cpu_seconds": self.cpu_seconds,
            "memory_mb": self.memory_mb,
            "max_processes": self.max_processes,
            "max_file_size_mb": self.max_file_size_mb,
            "network_profile": self.network_profile,
            "network_allowlist": sorted(self.network_allowlist),
            "allowed_network_profiles": sorted(self.allowed_network_profiles),
            "network_egress": self.network_egress,
            "network_mechanism": self.network_mechanism,
            "max_output_chars": self.max_output_chars,
        }


@dataclass(frozen=True, slots=True)
class RuntimeResult:
    """Captured execution trace and classified outcome."""

    status: RuntimeStatus
    command: tuple[str, ...]
    exit_code: int | None
    duration_ms: float
    stdout: str
    stderr: str
    network_profile: str
    policy: Mapping[str, Any] = field(default_factory=dict)
    network_events: tuple[Mapping[str, Any], ...] = ()
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "status": self.status.value,
            "command": list(self.command),
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "network_profile": self.network_profile,
            "policy": dict(self.policy),
            "network_events": [dict(event) for event in self.network_events],
        }
        if self.detail is not None:
            data["detail"] = self.detail
        return data


def _decode(data: bytes, limit: int) -> str:
    text = data.decode("utf-8", errors="replace")
    if len(text) > limit:
        return text[:limit] + "\n...[truncated]"
    return text


def _resource_limiter(policy: ExecutionPolicy):
    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (policy.cpu_seconds, policy.cpu_seconds))
        memory = policy.memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        file_size = policy.max_file_size_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_size, file_size))
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (policy.max_processes, policy.max_processes),
        )
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    return apply


def _resolve_within(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise RuntimeSetupError(f"initial state path escapes workspace: {name!r}")
    return path


class IsolatedRuntime:
    """Prepare a disposable workspace and execute commands inside bubblewrap.

    The runtime fails closed when bubblewrap is unavailable or the requested
    network policy is unsupported. It does not silently execute on the host.
    """

    def __init__(self, policy: ExecutionPolicy | None = None) -> None:
        self.policy = policy or ExecutionPolicy()
        self.workspace: Path | None = None
        self._temporary: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.cleanup()

    def prepare(self, initial_state: Mapping[str, Any] | None = None) -> Path:
        """Create a fresh workspace and apply declared initial state."""
        self.cleanup()
        try:
            self._temporary = tempfile.TemporaryDirectory(prefix="harnessbench-runtime-")
            workspace = Path(self._temporary.name) / "workspace"
            workspace.mkdir()
            self._apply_initial_state(workspace, initial_state)
        except Exception:
            self.cleanup()
            raise
        self.workspace = workspace
        return workspace

    def reset(self, initial_state: Mapping[str, Any] | None = None) -> Path:
        """Discard prior state and prepare the declared initial state again."""
        return self.prepare(initial_state)

    def _apply_initial_state(
        self, workspace: Path, initial_state: Mapping[str, Any] | None
    ) -> None:
        if initial_state is None:
            return

        source_dir = initial_state.get("source_dir")
        if source_dir is not None:
            if not isinstance(source_dir, str):
                raise RuntimeSetupError("source_dir must be a string")
            source = Path(source_dir)
            if not source.is_dir():
                raise RuntimeSetupError(f"source_dir does not exist: {source}")
            shutil.copytree(source, workspace, dirs_exist_ok=True)

        files = initial_state.get("files", {})
        if not isinstance(files, Mapping):
            raise RuntimeSetupError("initial state files must be an object")
        for name, content in files.items():
            if not isinstance(name, str) or not isinstance(content, str):
                raise RuntimeSetupError("initial state files must map strings to strings")
            path = _resolve_within(workspace, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def cleanup(self) -> None:
        """Remove the workspace and all files created during execution."""
        if self._temporary is not None:
            self._temporary.cleanup()
        self._temporary = None
        self.workspace = None

    def _bwrap_command(
        self,
        bwrap: str,
        workspace: Path,
        policy: ExecutionPolicy,
        command: Sequence[str],
        *,
        proxy: ControlledEgressProxy | None = None,
    ) -> list[str]:
        args = [
            bwrap,
            "--unshare-user",
            "--die-with-parent",
            "--new-session",
            "--unshare-pid",
            "--unshare-ipc",
            "--unshare-uts",
            "--unshare-cgroup",
            "--cap-drop",
            "ALL",
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/etc",
            "/etc",
            "--symlink",
            "/usr/bin",
            "/bin",
            "--symlink",
            "/usr/bin",
            "/sbin",
            "--symlink",
            "/usr/lib",
            "/lib",
            "--dev",
            "/dev",
            "--proc",
            "/proc",
            "--tmpfs",
            "/tmp",
            "--bind",
            str(workspace),
            "/workspace",
            "--chdir",
            "/workspace",
            "--clearenv",
            "--setenv",
            "PATH",
            "/usr/bin:/bin",
            "--setenv",
            "HOME",
            "/workspace",
            "--setenv",
            "TMPDIR",
            "/tmp",
            "--setenv",
            "LANG",
            "C.UTF-8",
        ]
        if policy.network_profile in {"N0", "N1"}:
            args.append("--unshare-net")
        if policy.network_profile == "N1":
            if proxy is None:
                raise ValueError("N1 requires a controlled egress proxy")
            args.extend(["--ro-bind", str(proxy.directory), "/egress"])
            proxy_url = f"http://127.0.0.1:{BRIDGE_PORT}"
            for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
                args.extend(["--setenv", name, proxy_url])
            for name in ("http_proxy", "https_proxy", "all_proxy"):
                args.extend(["--setenv", name, proxy_url])
            for name in ("NO_PROXY", "no_proxy"):
                args.extend(["--setenv", name, ""])
            args.extend(["--", "/bin/sh", "-c", _PROXY_WRAPPER, "sh", *command])
            return args
        args.append("--")
        args.extend(command)
        return args

    def execute(
        self,
        command: Sequence[str],
        *,
        policy: ExecutionPolicy | None = None,
        input_data: bytes | None = None,
    ) -> RuntimeResult:
        """Execute a command in the prepared workspace and capture its trace."""
        active = policy or self.policy
        command_tuple = tuple(command)
        if input_data is not None and not isinstance(input_data, bytes):
            raise TypeError("input_data must be bytes")
        if not active.network_supported:
            return self._result(
                RuntimeStatus.POLICY_VIOLATION,
                command_tuple,
                active,
                detail=f"runtime does not support network profile {active.network_profile}",
            )
        if active.network_profile == "N1" and not active.network_allowlist:
            return self._result(
                RuntimeStatus.POLICY_VIOLATION,
                command_tuple,
                active,
                detail="N1 controlled egress requires at least one allowlist entry",
            )
        if self.workspace is None or not self.workspace.is_dir():
            return self._result(
                RuntimeStatus.SETUP_FAILED,
                command_tuple,
                active,
                detail="workspace has not been prepared",
            )
        bwrap = shutil.which("bwrap")
        if bwrap is None:
            return self._result(
                RuntimeStatus.RUNTIME_UNAVAILABLE,
                command_tuple,
                active,
                detail="bubblewrap (bwrap) is not installed",
            )

        proxy: ControlledEgressProxy | None = None
        if active.network_profile == "N1":
            try:
                proxy = ControlledEgressProxy(active.network_allowlist)
                proxy.start()
            except (OSError, ValueError) as exc:
                if proxy is not None:
                    proxy.stop()
                return self._result(
                    RuntimeStatus.POLICY_VIOLATION,
                    command_tuple,
                    active,
                    detail=f"cannot start N1 egress proxy: {exc}",
                )

        try:
            started = perf_counter()
            try:
                process = subprocess.Popen(
                    self._bwrap_command(
                        bwrap,
                        self.workspace,
                        active,
                        command_tuple,
                        proxy=proxy,
                    ),
                    stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                    # Single-threaded CLI; limits must be set before exec.
                    preexec_fn=_resource_limiter(active),  # noqa: PLW1509
                    env={},
                )
            except OSError as exc:
                return self._result(
                    RuntimeStatus.SETUP_FAILED,
                    command_tuple,
                    active,
                    detail=f"cannot start runtime: {exc}",
                    network_events=proxy.events if proxy is not None else (),
                )

            timed_out = False
            try:
                stdout_bytes, stderr_bytes = process.communicate(
                    input=input_data,
                    timeout=active.timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout_bytes, stderr_bytes = process.communicate()

            duration_ms = round((perf_counter() - started) * 1000, 3)
            stdout = _decode(stdout_bytes, active.max_output_chars)
            stderr = _decode(stderr_bytes, active.max_output_chars)
            status, detail = self._classify(
                process.returncode,
                timed_out=timed_out,
                stderr=stderr,
            )
            return RuntimeResult(
                status=status,
                command=command_tuple,
                exit_code=process.returncode,
                duration_ms=duration_ms,
                stdout=stdout,
                stderr=stderr,
                network_profile=active.network_profile,
                policy=active.to_dict(),
                network_events=proxy.events if proxy is not None else (),
                detail=detail,
            )
        finally:
            if proxy is not None:
                proxy.stop()

    def _classify(
        self, returncode: int, *, timed_out: bool, stderr: str
    ) -> tuple[RuntimeStatus, str | None]:
        if timed_out:
            return RuntimeStatus.TIMED_OUT, "wall-clock timeout exceeded"
        if returncode == 0:
            return RuntimeStatus.COMPLETED, None
        if returncode in (-signal.SIGXCPU, -signal.SIGXFSZ):
            return RuntimeStatus.RESOURCE_LIMITED, "resource limit exceeded"
        if returncode > 128 and (returncode - 128) in (signal.SIGXCPU, signal.SIGXFSZ):
            return RuntimeStatus.RESOURCE_LIMITED, "resource limit exceeded"
        if stderr.startswith("bwrap:"):
            return RuntimeStatus.SETUP_FAILED, stderr.splitlines()[0]
        if returncode < 0:
            return RuntimeStatus.EXECUTION_FAILED, f"terminated by signal {-returncode}"
        return RuntimeStatus.EXECUTION_FAILED, f"exit code {returncode}"

    def _result(
        self,
        status: RuntimeStatus,
        command: tuple[str, ...],
        policy: ExecutionPolicy,
        *,
        detail: str,
        network_events: tuple[Mapping[str, Any], ...] = (),
    ) -> RuntimeResult:
        return RuntimeResult(
            status=status,
            command=command,
            exit_code=None,
            duration_ms=0.0,
            stdout="",
            stderr="",
            network_profile=policy.network_profile,
            policy=policy.to_dict(),
            network_events=network_events,
            detail=detail,
        )
