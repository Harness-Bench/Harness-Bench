"""Harness adapter that executes a command inside the isolated runtime."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Self

from harnessbench.adapters.harnesses.base import HarnessError
from harnessbench.runtime.isolated import ExecutionPolicy, IsolatedRuntime, RuntimeResult


class CommandHarness:
    """Run a declared command in a disposable bubblewrap workspace."""

    version = "0.1.0"

    def __init__(
        self,
        command: Sequence[str],
        policy: ExecutionPolicy | None = None,
    ) -> None:
        if not command:
            raise HarnessError("command must not be empty")
        self.command = tuple(command)
        self.policy = policy or ExecutionPolicy()
        self.runtime = IsolatedRuntime(self.policy)

    def __enter__(self) -> Self:
        self.runtime.__enter__()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.runtime.cleanup()

    def prepare(self, initial_state: Mapping[str, Any] | None = None) -> Path:
        """Prepare the isolated workspace from the declared initial state."""
        return self.runtime.prepare(initial_state)

    @property
    def workspace(self) -> Path:
        if self.runtime.workspace is None:
            raise HarnessError("workspace has not been prepared")
        return self.runtime.workspace

    def run(self) -> RuntimeResult:
        """Execute the command and return its captured runtime trace."""
        return self.runtime.execute(self.command)
