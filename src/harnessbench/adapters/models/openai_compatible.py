"""OpenAI-compatible chat-completions model adapter."""

from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from harnessbench.adapters.models.base import ModelAdapterError, ModelResponse


class OpenAICompatibleModelAdapter:
    """Call a chat-completions endpoint without committing to one provider."""

    version = "0.1.0"

    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        api_key: str | None = None,
        timeout_seconds: float = 30.0,
        temperature: float | None = 0.0,
    ) -> None:
        if not base_url:
            raise ValueError("base_url must not be empty")
        if not model:
            raise ValueError("model must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if temperature is not None and not 0 <= temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    def invoke(self, prompt: str) -> ModelResponse:
        """Send one chat-completions request and return its text response."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        http_request = request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise ModelAdapterError(
                f"model endpoint returned HTTP {exc.code}: {detail}"
            ) from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            raise ModelAdapterError(
                f"cannot reach model endpoint {self.base_url}: {exc}"
            ) from exc

        try:
            data: Any = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ModelAdapterError(f"model endpoint returned invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ModelAdapterError("model response must be a JSON object")

        try:
            choice = data["choices"][0]
            message = choice["message"]
            content = message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelAdapterError(
                "model response is missing choices[0].message.content"
            ) from exc
        if not isinstance(content, str):
            raise ModelAdapterError("model response content must be a string")

        usage = data.get("usage")
        return ModelResponse(
            text=content,
            metadata={
                "adapter": "openai-compatible",
                "version": self.version,
                "model": self.model,
                "endpoint": self.base_url,
                "response_id": data.get("id"),
                "finish_reason": choice.get("finish_reason"),
                "usage": usage if isinstance(usage, dict) else {},
            },
        )
