from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ai_privacy_gateway.providers.base import LLMProvider, ProviderError, ProviderResponse


class AzureOpenAIProvider(LLMProvider):
    """Adapter for Azure OpenAI Service.

    Azure's API is OpenAI-shaped but routes by *deployment name* rather
    than model name, and authenticates via an `api-key` header plus an
    `api-version` query parameter instead of a Bearer token — hence a
    separate adapter rather than reusing `OpenAIProvider` with a
    different base URL.
    """

    name = "azure_openai"

    def __init__(self, api_key: str, endpoint: str, api_version: str = "2024-10-21", timeout: float = 60.0) -> None:
        self._api_version = api_version
        self._client = httpx.AsyncClient(
            base_url=endpoint.rstrip("/"),
            headers={"api-key": api_key},
            timeout=timeout,
        )

    def _url(self, deployment: str) -> str:
        return f"/openai/deployments/{deployment}/chat/completions?api-version={self._api_version}"

    async def complete(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> ProviderResponse:
        # `model` is treated as the Azure *deployment name* for this adapter.
        payload = {"messages": messages, **kwargs}
        resp = await self._client.post(self._url(model), json=payload)
        if resp.status_code >= 400:
            raise ProviderError(self.name, resp.status_code, resp.text)
        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return ProviderResponse(
            text=choice["message"].get("content") or "",
            raw=data,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            model=data.get("model", model),
            finish_reason=choice.get("finish_reason"),
        )

    async def stream_complete(
        self, messages: list[dict[str, Any]], model: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        payload = {"messages": messages, "stream": True, **kwargs}
        async with self._client.stream("POST", self._url(model), json=payload) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                raise ProviderError(self.name, resp.status_code, body.decode(errors="replace"))
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = line[len("data:") :].strip()
                if chunk == "[DONE]":
                    break
                try:
                    event = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                delta = event.get("choices", [{}])[0].get("delta", {})
                text = delta.get("content")
                if text:
                    yield text

    async def aclose(self) -> None:
        await self._client.aclose()
