"""Redact known secret values from persisted run records and artifacts.

Secrets are supplied by the caller. Values shorter than
``MIN_SECRET_LENGTH`` are ignored to avoid accidental broad replacement.
This is a last line of defence for persisted evidence, not a substitute for
keeping credentials out of prompts and sandboxes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

REDACTED = "[REDACTED]"
MIN_SECRET_LENGTH = 4


@dataclass(frozen=True, slots=True)
class SecretRedactor:
    """Replace known secret strings in text, bytes, and nested payloads."""

    secrets: tuple[str, ...] = ()

    def __init__(self, secrets: Sequence[str] = ()) -> None:
        normalized = {
            secret
            for secret in secrets
            if isinstance(secret, str) and len(secret) >= MIN_SECRET_LENGTH
        }
        # Replace longer secrets first so a shorter suffix cannot split them.
        object.__setattr__(self, "secrets", tuple(sorted(normalized, key=len, reverse=True)))

    def redact_text(self, text: str) -> str:
        """Replace every known secret in ``text``."""
        for secret in self.secrets:
            text = text.replace(secret, REDACTED)
        return text

    def redact_bytes(self, content: bytes) -> bytes:
        """Replace every known secret in raw bytes without decoding them."""
        for secret in self.secrets:
            content = content.replace(secret.encode("utf-8"), REDACTED.encode("utf-8"))
        return content

    def redact_payload(self, payload: Any) -> Any:
        """Recursively redact string values in a JSON-like payload."""
        if isinstance(payload, str):
            return self.redact_text(payload)
        if isinstance(payload, Mapping):
            return {
                key: self.redact_payload(value)
                for key, value in payload.items()
            }
        if isinstance(payload, (list, tuple)):
            return [self.redact_payload(value) for value in payload]
        return payload
