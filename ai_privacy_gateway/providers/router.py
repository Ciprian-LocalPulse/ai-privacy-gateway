"""Provider routing.

Resolves which upstream adapter to use for a given request, either from
an explicit `provider` field in the request or by inferring it from the
model name (`gpt-*` -> OpenAI, `claude-*` -> Anthropic, `azure/*` ->
Azure OpenAI). Adapters are constructed lazily and cached — most
deployments only ever touch one or two providers, so there's no reason
to eagerly open HTTP clients for all of them at startup.
"""

from __future__ import annotations

from ai_privacy_gateway.config import ProviderSettings
from ai_privacy_gateway.providers.anthropic_provider import AnthropicProvider
from ai_privacy_gateway.providers.azure_openai_provider import AzureOpenAIProvider
from ai_privacy_gateway.providers.base import LLMProvider
from ai_privacy_gateway.providers.openai_provider import OpenAIProvider


class UnknownProviderError(ValueError):
    pass


class ProviderRouter:
    def __init__(self, settings: ProviderSettings) -> None:
        self._settings = settings
        self._instances: dict[str, LLMProvider] = {}

    def _build(self, name: str) -> LLMProvider:
        if name == "openai":
            return OpenAIProvider(self._settings.openai_api_key, self._settings.openai_base_url)
        if name == "anthropic":
            return AnthropicProvider(self._settings.anthropic_api_key, self._settings.anthropic_base_url)
        if name == "azure_openai":
            return AzureOpenAIProvider(
                self._settings.azure_openai_api_key,
                self._settings.azure_openai_endpoint,
                self._settings.azure_openai_api_version,
            )
        raise UnknownProviderError(f"Unknown provider: {name!r}. Expected one of: openai, anthropic, azure_openai.")

    def get(self, name: str) -> LLMProvider:
        if name not in self._instances:
            self._instances[name] = self._build(name)
        return self._instances[name]

    @staticmethod
    def infer_provider_name(model: str) -> str:
        lowered = model.lower()
        if lowered.startswith("claude"):
            return "anthropic"
        if lowered.startswith("azure/"):
            return "azure_openai"
        return "openai"

    def resolve(self, model: str, explicit_provider: str | None = None) -> tuple[LLMProvider, str]:
        """Returns (provider_instance, model_name_to_send_upstream)."""
        provider_name = explicit_provider or self.infer_provider_name(model)
        provider = self.get(provider_name)
        resolved_model = model.split("/", 1)[1] if provider_name == "azure_openai" and "/" in model else model
        return provider, resolved_model

    async def aclose_all(self) -> None:
        for provider in self._instances.values():
            await provider.aclose()
