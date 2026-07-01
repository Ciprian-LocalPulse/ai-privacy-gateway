"""Policy data model.

A policy pack is a YAML file mapping entity types to the anonymization
action that should be taken when they're detected, plus a couple of
pack-wide settings (default action for unlisted types, and which entity
types are severe enough to reject the request outright instead of
anonymizing it). See `policies/*.yaml` for the shipped starter packs and
`docs/policy-configuration.md` for the authoring guide.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from ai_privacy_gateway.anonymizer.strategies import AnonymizationAction


class EntityPolicy(BaseModel):
    action: AnonymizationAction
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class Policy(BaseModel):
    name: str
    description: str = ""
    jurisdiction: str | None = None
    default_action: AnonymizationAction = AnonymizationAction.MASK
    entity_policies: dict[str, EntityPolicy] = Field(default_factory=dict)
    block_on_types: list[str] = Field(default_factory=list)

    @field_validator("entity_policies", mode="before")
    @classmethod
    def _normalize_entity_policy_dicts(cls, v: dict) -> dict:
        """Allow the YAML to write a bare string for the action
        (`RO_CNP: tokenize`) instead of requiring `RO_CNP: {action: tokenize}`
        — much friendlier for a policy pack that's mostly a big list."""
        if not isinstance(v, dict):
            return v
        normalized = {}
        for key, value in v.items():
            if isinstance(value, str):
                normalized[key] = {"action": value}
            else:
                normalized[key] = value
        return normalized

    def action_for(self, entity_type: str) -> EntityPolicy | None:
        return self.entity_policies.get(entity_type)
