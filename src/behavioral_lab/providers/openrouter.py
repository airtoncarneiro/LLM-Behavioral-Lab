from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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
    ) -> None:
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.preset = preset
        self.endpoint = endpoint
        self.timeout = timeout

    def complete(self, messages: list[dict[str, str]]) -> ProviderResponse:
        if not self._api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouterProvider")

        request = Request(
            self.endpoint,
            data=json.dumps({"model": self.preset, "messages": messages}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"OpenRouter request failed with HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError("OpenRouter request could not be completed") from exc

        try:
            choice = payload["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenRouter returned an unexpected response") from exc
        if not isinstance(content, str):
            raise RuntimeError("OpenRouter response content must be text")

        return ProviderResponse(
            content=content,
            model=payload.get("model"),
            provider="openrouter",
            preset=self.preset,
        )
