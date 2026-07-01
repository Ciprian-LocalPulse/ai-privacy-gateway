"""Anonymization engine.

Given the original text, the entities detected in it, and a per-entity
action decided by the policy layer, this module produces the redacted
text that is safe to forward to an external LLM — plus a structured
record of what was done, which the audit log and the re-identifier both
need.

Replacement is done right-to-left (highest `start` offset first) so that
earlier character offsets in the original text remain valid as later
(higher-offset) spans are replaced with strings of a different length.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ai_privacy_gateway.anonymizer.strategies import (
    AnonymizationAction,
    StrategyOutput,
    allow,
    hash_value,
    mask,
    synthetic,
    tokenize,
)
from ai_privacy_gateway.anonymizer.vault import EncryptedVault
from ai_privacy_gateway.detectors.base import Entity

DecisionFn = Callable[[Entity], AnonymizationAction]


@dataclass(frozen=True, slots=True)
class AppliedAnonymization:
    entity: Entity
    action: AnonymizationAction
    reversible: bool
    replacement: str


@dataclass(frozen=True, slots=True)
class AnonymizationOutcome:
    anonymized_text: str
    session_id: str
    applied: list[AppliedAnonymization] = field(default_factory=list)

    def entity_type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.applied:
            key = item.entity.entity_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts


class AnonymizationEngine:
    def __init__(self, vault: EncryptedVault, hash_secret_key: bytes) -> None:
        self.vault = vault
        self.hash_secret_key = hash_secret_key

    def _apply_strategy(self, entity: Entity, action: AnonymizationAction) -> StrategyOutput:
        if action == AnonymizationAction.MASK:
            return mask(entity)
        if action == AnonymizationAction.TOKENIZE:
            return tokenize(entity)
        if action == AnonymizationAction.HASH:
            return hash_value(entity, self.hash_secret_key)
        if action == AnonymizationAction.SYNTHETIC:
            return synthetic(entity)
        return allow(entity)

    def anonymize(
        self,
        text: str,
        entities: list[Entity],
        session_id: str,
        decide_action: DecisionFn,
        vault_ttl_seconds: int | None = None,
    ) -> AnonymizationOutcome:
        # Right-to-left so earlier offsets stay valid as we mutate the string.
        entities_desc = sorted(entities, key=lambda e: e.start, reverse=True)

        result_text = text
        applied: list[AppliedAnonymization] = []

        for entity in entities_desc:
            action = decide_action(entity)
            output = self._apply_strategy(entity, action)

            result_text = result_text[: entity.start] + output.replacement + result_text[entity.end :]

            if output.vault_entry is not None:
                key, original_value = output.vault_entry
                self.vault.store(session_id, key, original_value, ttl_seconds=vault_ttl_seconds)

            applied.append(
                AppliedAnonymization(
                    entity=entity,
                    action=output.action,
                    reversible=output.reversible,
                    replacement=output.replacement,
                )
            )

        applied.reverse()  # restore left-to-right order for readable audit/billing records
        return AnonymizationOutcome(anonymized_text=result_text, session_id=session_id, applied=applied)
