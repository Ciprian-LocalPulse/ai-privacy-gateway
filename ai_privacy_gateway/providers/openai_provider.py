from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ai_privacy_gateway.providers.base import LLMProvider, ProviderError, ProviderResponse


class OpenAIProvider(LLMProvider):
    """Adapter for OpenAI's `/chat/completions` API. Also works unmodified
    against any OpenAI-API-compatible endpoint (many self-hosted/local
    model servers mimic this exact wire format) — just point `base_url`
    at it."""

    name = "openai"

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", timeout: float = 60.0) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    async def complete(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> ProviderResponse:
        payload = {"model": model, "messages": messages, **kwargs}
        resp = await self._client.post("/chat/completions", json=payload)
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
            model=data.get("model"),
            finish_reason=choice.get("finish_reason"),
        )

    async def stream_complete(
        self, messages: list[dict[str, Any]], model: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        payload = {"model": model, "messages": messages, "stream": True, **kwargs}
        async with self._client.stream("POST", "/chat/completions", json=payload) as resp:
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
