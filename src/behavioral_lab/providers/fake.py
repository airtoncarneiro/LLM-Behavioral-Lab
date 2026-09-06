from __future__ import annotations

from collections.abc import Iterable

from behavioral_lab.providers.openrouter import ProviderResponse


class FakeLLMProvider:
    """Deterministic provider used by tests and CI; it never performs I/O."""

    def __init__(self, responses: Iterable[str]) -> None:
        self._responses = iter(responses)
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> ProviderResponse:
        self.calls.append(messages)
        try:
            content = next(self._responses)
        except StopIteration as exc:
            raise RuntimeError("FakeLLMProvider has no response left") from exc
        return ProviderResponse(
            content=content,
            model="fake-model",
            provider="fake",
            preset="fake",
        )
