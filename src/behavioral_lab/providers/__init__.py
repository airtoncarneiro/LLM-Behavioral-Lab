"""Model provider adapters used by behavioral agents."""

from behavioral_lab.providers.fake import FakeLLMProvider
from behavioral_lab.providers.openrouter import OpenRouterProvider, ProviderResponse

__all__ = ["FakeLLMProvider", "OpenRouterProvider", "ProviderResponse"]
