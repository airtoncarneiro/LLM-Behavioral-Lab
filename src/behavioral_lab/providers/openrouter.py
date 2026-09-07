from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ACTION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "One action selected by the behavioral simulation agent.",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["move", "search", "take", "store", "give", "eat", "wait"],
            "description": "The single action to execute this turn.",
        },
        "arguments": {
            "type": "object",
            "description": "Action arguments. Unused fields must be null.",
            "properties": {
                "location": {"type": ["string", "null"], "description": "Destination for move."},
                "target": {"type": ["string", "null"], "description": "Recipient for give."},
                "quantity": {"type": ["integer", "null"], "description": "Food units for take, store, give, or eat."},
            },
            "required": ["location", "target", "quantity"],
            "additionalProperties": False,
        },
        "public_message": {
            "type": ["string", "null"],
            "description": "Optional message delivered to all agents in later observations.",
        },
        "private_message_to": {
            "type": ["string", "null"],
            "description": "Optional co-located recipient of the private message.",
        },
        "private_message": {
            "type": ["string", "null"],
            "description": "Optional message delivered only to private_message_to.",
        },
    },
    "required": ["action", "arguments", "public_message", "private_message_to", "private_message"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class ProviderResponse:
    content: str
    model: str | None
    provider: str
    preset: str


class OpenRouterProvider:
    """Small standard-library adapter for OpenRouter chat completions."""

    DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_PRESET = "@preset/mais-barato"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        preset: str = DEFAULT_PRESET,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_backoff: float = 0.25,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.preset = preset
        self.endpoint = endpoint
        self.timeout = timeout
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if retry_backoff < 0:
            raise ValueError("retry_backoff cannot be negative")
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def complete(self, messages: list[dict[str, str]]) -> ProviderResponse:
        if not self._api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouterProvider")

        payload = {
            "model": self.preset,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "behavioral_lab_action",
                    "strict": True,
                    "schema": ACTION_RESPONSE_SCHEMA,
                },
            },
            "provider": {"require_parameters": True},
        }
        request_body = json.dumps(payload).encode("utf-8")
        response_payload: dict[str, Any] | None = None
        for attempt in range(self.max_retries + 1):
            request = Request(
                self.endpoint,
                data=request_body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    response_payload = json.loads(response.read().decode("utf-8"))
                break
            except HTTPError as exc:
                retryable = exc.code == 408 or exc.code == 429 or 500 <= exc.code <= 599
                if not retryable or attempt == self.max_retries:
                    raise RuntimeError(f"OpenRouter request failed with HTTP {exc.code}") from exc
            except (TimeoutError, URLError) as exc:
                if attempt == self.max_retries:
                    raise RuntimeError("OpenRouter request could not be completed") from exc
            except json.JSONDecodeError as exc:
                raise RuntimeError("OpenRouter returned invalid JSON") from exc
            if self.retry_backoff:
                time.sleep(self.retry_backoff * (attempt + 1))

        if not isinstance(response_payload, dict):
            raise RuntimeError("OpenRouter returned an unexpected response")
        try:
            choices = response_payload["choices"]
            choice = choices[0]
            message = choice["message"]
            content = message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenRouter returned an unexpected response") from exc
        if not isinstance(content, str):
            raise RuntimeError("OpenRouter response content must be text")
        try:
            structured_content = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenRouter response content must be valid JSON") from exc
        if not isinstance(structured_content, dict):
            raise RuntimeError("OpenRouter response content must be a JSON object")

        return ProviderResponse(
            content=content,
            model=response_payload.get("model"),
            provider="openrouter",
            preset=self.preset,
        )
