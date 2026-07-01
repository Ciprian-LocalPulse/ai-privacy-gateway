"""Provider adapter abstraction.

Every upstream LLM (OpenAI, Anthropic, Azure OpenAI, ...) speaks a
slightly different wire format. The gateway's core proxy logic
(`proxy/gateway.py`) should never need to know which one it's talking to
— it anonymizes text, calls `provider.complete(...)`, gets back a
provider-agnostic `ProviderResponse`, and re-identifies the text. All the
format-specific translation happens once, here, per adapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ProviderResponse:
    text: str
    raw: dict[str, Any]
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None
    finish_reason: str | None = None


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> ProviderResponse:
        """Send a non-streaming chat completion request upstream."""

    @abstractmethod
    async def stream_complete(
        self, messages: list[dict[str, Any]], model: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        """Yield text deltas for a streaming chat completion request."""

    @abstractmethod
    async def aclose(self) -> None:
        """Release any underlying HTTP client resources."""


class ProviderError(RuntimeError):
    """Raised when an upstream provider returns an error response or the
    request otherwise fails. Wraps enough context for the gateway to
    return a sensible error to the caller without leaking upstream
    internals verbatim."""

    def __init__(self, provider_name: str, status_code: int | None, message: str) -> None:
        self.provider_name = provider_name
        self.status_code = status_code
        super().__init__(f"[{provider_name}] {message}")
