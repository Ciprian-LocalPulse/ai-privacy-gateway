from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ai_privacy_gateway.providers.base import LLMProvider, ProviderError, ProviderResponse

_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    """Adapter for Anthropic's `/v1/messages` API."""

    name = "anthropic"

    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com", timeout: float = 60.0) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "x-api-key": api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            timeout=timeout,
        )

    @staticmethod
    def _extract_text(content_blocks: list[dict[str, Any]]) -> str:
        return "".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")

    async def complete(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> ProviderResponse:
        max_tokens = kwargs.pop("max_tokens", 1024)
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens, **kwargs}
        resp = await self._client.post("/v1/messages", json=payload)
        if resp.status_code >= 400:
            raise ProviderError(self.name, resp.status_code, resp.text)
        data = resp.json()
        usage = data.get("usage", {})
        return ProviderResponse(
            text=self._extract_text(data.get("content", [])),
            raw=data,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            model=data.get("model"),
            finish_reason=data.get("stop_reason"),
        )

    async def stream_complete(
        self, messages: list[dict[str, Any]], model: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        max_tokens = kwargs.pop("max_tokens", 1024)
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": True, **kwargs}
        async with self._client.stream("POST", "/v1/messages", json=payload) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                raise ProviderError(self.name, resp.status_code, body.decode(errors="replace"))
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = line[len("data:") :].strip()
                if not chunk:
                    continue
                try:
                    event = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    text = delta.get("text")
                    if text:
                        yield text

    async def aclose(self) -> None:
        await self._client.aclose()
