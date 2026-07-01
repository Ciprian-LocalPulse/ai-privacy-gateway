"""Turns a `Policy` into per-entity decisions at request time."""

from __future__ import annotations

from ai_privacy_gateway.anonymizer.strategies import AnonymizationAction
from ai_privacy_gateway.detectors.base import Entity
from ai_privacy_gateway.policy.models import Policy


class PolicyEvaluator:
    def __init__(self, policy: Policy) -> None:
        self.policy = policy

    def decide_action(self, entity: Entity) -> AnonymizationAction:
        entity_policy = self.policy.action_for(entity.entity_type.value)
        if entity_policy is None:
            return self.policy.default_action
        if entity.confidence < entity_policy.min_confidence:
            # Not confident enough to act — leaving it alone beats a
            # false-positive redaction mangling ordinary prose.
            return AnonymizationAction.ALLOW
        return entity_policy.action

    def should_block_request(self, entities: list[Entity]) -> bool:
        if not self.policy.block_on_types:
            return False
        blocked = set(self.policy.block_on_types)
        return any(e.entity_type.value in blocked for e in entities)

    def blocking_entity_types(self, entities: list[Entity]) -> list[str]:
        blocked = set(self.policy.block_on_types)
        return sorted({e.entity_type.value for e in entities if e.entity_type.value in blocked})
