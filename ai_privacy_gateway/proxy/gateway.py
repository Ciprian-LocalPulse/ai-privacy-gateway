from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol

from ai_privacy_gateway.anonymizer.engine import AnonymizationEngine, AnonymizationOutcome
from ai_privacy_gateway.detectors.base import Entity
from ai_privacy_gateway.policy.evaluator import PolicyEvaluator
from ai_privacy_gateway.providers.base import LLMProvider, ProviderResponse
from ai_privacy_gateway.proxy.reidentifier import Reidentifier
from ai_privacy_gateway.proxy.streaming import StreamingInterpolator


class DetectorProtocol(Protocol):
    """Interfață abstractă pentru detectorul de entități (ex: Presidio sau un model NER local)."""
    async def detect(self, text: str) -> list[Entity]:
        ...


@dataclass(slots=True)
class GatewayResult:
    """Rezultatul final returnat de gateway pentru cererile non-streaming."""
    original_text: str
    anonymized_text: str
    response_text: str
    raw_provider_response: dict[str, Any]
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None


class RequestBlockedError(Exception):
    """Excepție ridicată atunci când cererea încalcă politicile critice de securitate."""
    def __init__(self, blocked_types: list[str]) -> None:
        self.blocked_types = blocked_types
        super().__init__(
            f"Cererea a fost blocată deoarece conține tipuri de date restricționate: {', '.join(blocked_types)}"
        )


class PrivacyGateway:
    """Orchestratorul principal care implementează pipeline-ul de anonimizare și securitate."""

    def __init__(
        self,
        engine: AnonymizationEngine,
        evaluator: PolicyEvaluator,
        provider: LLMProvider,
        reidentifier: Reidentifier,
        detector: DetectorProtocol,
    ) -> None:
        self.engine = engine
        self.evaluator = evaluator
        self.provider = provider
        self.reidentifier = reidentifier
        self.detector = detector

    async def _process_and_anonymize_messages(
        self, messages: list[dict[str, Any]], session_id: str
    ) -> list[dict[str, Any]]:
        """Scanează și anonimizează fiecare mesaj din istoric, aplicând politicile stabilite."""
        anonymized_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Anonimizăm doar mesajele venite de la utilizator sau sistem
            if role in ("user", "system") and isinstance(content, str) and content:
                # 1. Detectăm entitățile sensibile (PII/PHI)
                entities = await self.detector.detect(content)

                # 2. Verificăm dacă politica cere blocarea completă a cererii
                if self.evaluator.should_block_request(entities):
                    blocked_types = self.evaluator.blocking_entity_types(entities)
                    raise RequestBlockedError(blocked_types)

                # 3. Aplicăm transformările de anonimizare (mask, tokenize, synthetic)
                outcome: AnonymizationOutcome = self.engine.anonymize(
                    text=content,
                    entities=entities,
                    session_id=session_id,
                    decide_action=self.evaluator.decide_action,
                )
                
                anonymized_messages.append({"role": role, "content": outcome.anonymized_text})
            else:
                anonymized_messages.append(msg)

        return anonymized_messages

    async def complete(
        self, messages: list[dict[str, Any]], model: str, session_id: str, **kwargs: Any
    ) -> GatewayResult:
        """Procesează o cerere standard (non-streaming) end-to-end."""
        # Anonimizare payload de intrare
        safe_messages = await self._process_and_anonymize_messages(messages, session_id)

        # Transmitere către LLM Provider (OpenAI, Anthropic, Azure)
        provider_resp: ProviderResponse = await self.provider.complete(
            messages=safe_messages, model=model, **kwargs
        )

        # Re-identificare răspuns (repunem datele reale din seif înapoi în text)
        final_text = self.reidentifier.reidentify(provider_resp.text, session_id)

        return GatewayResult(
            original_text=messages[-1].get("content", ""),
            anonymized_text=safe_messages[-1].get("content", ""),
            response_text=final_text,
            raw_provider_response=provider_resp.raw,
            input_tokens=provider_resp.input_tokens,
            output_tokens=provider_resp.output_tokens,
            model=provider_resp.model,
        )

    async def stream_complete(
        self, messages: list[dict[str, Any]], model: str, session_id: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        """Procesează o cerere de tip streaming, interpolând tokenii în timp real."""
        # Anonimizare payload de intrare
        safe_messages = await self._process_and_anonymize_messages(messages, session_id)

        # Pornim stream-ul asincron de la provider
        raw_stream = self.provider.stream_complete(messages=safe_messages, model=model, **kwargs)

        # Folosim utilitarul de streaming pentru a de-anonimiza chunk-urile din mers
        interpolator = StreamingInterpolator(self.reidentifier, session_id)

        async for chunk in raw_stream:
            async for clear_text in interpolator.process_chunk(chunk):
                yield clear_text

        # Returnăm eventualele resturi rămase în buffer-ul interpolatorului
        async for clear_text in interpolator.flush():
            yield clear_text