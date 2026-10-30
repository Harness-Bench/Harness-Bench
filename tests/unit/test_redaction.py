"""Unit tests for persisted-evidence secret redaction."""

from __future__ import annotations

from harnessbench.storage.redaction import REDACTED, SecretRedactor


def test_redacts_text_and_bytes() -> None:
    redactor = SecretRedactor(("super-secret-key",))

    assert redactor.redact_text("token=super-secret-key") == f"token={REDACTED}"
    assert redactor.redact_bytes(b"token=super-secret-key") == f"token={REDACTED}".encode()


def test_redacts_nested_payload_values() -> None:
    redactor = SecretRedactor(("super-secret-key",))

    payload = {
        "message": "super-secret-key",
        "items": ["prefix-super-secret-key", {"nested": "super-secret-key"}],
        "count": 3,
    }

    assert redactor.redact_payload(payload) == {
        "message": REDACTED,
        "items": [f"prefix-{REDACTED}", {"nested": REDACTED}],
        "count": 3,
    }


def test_ignores_short_and_empty_secrets() -> None:
    redactor = SecretRedactor(("abc", "", "abcd"))

    assert redactor.redact_text("abc abcd") == "abc [REDACTED]"
    assert redactor.secrets == ("abcd",)
