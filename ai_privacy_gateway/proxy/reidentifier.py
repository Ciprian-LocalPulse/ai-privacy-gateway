"""Re-identification.

The last leg of the round trip: the external LLM's response comes back
containing our placeholder tokens (for TOKENIZE) and/or our synthetic
stand-in values (for SYNTHETIC) instead of the user's real data. This
module puts the real data back before the response reaches the end user.

Two mechanisms, matching the two reversible strategies:

1. **Token placeholders** (`⟦PII:TYPE:hex⟧`) are found by regex and looked
   up directly in the vault — this is fully reliable because the
   placeholder is an opaque, unmistakable marker the LLM has no reason to
   alter (and if it does alter it, the vault lookup simply misses, which
   fails safe: the placeholder is left as-is rather than guessing).
2. **Synthetic values** are looked up by exact string match against the
   list of synthetic values generated for this session. This only
   succeeds if the model echoed the synthetic value verbatim — if the
   model paraphrased or transformed it, the original cannot be recovered
   from that output. This is a known, documented tradeoff (see
   docs/threat-model.md), not a bug.
"""

from __future__ import annotations

import re

from ai_privacy_gateway.anonymizer.engine import AppliedAnonymization
from ai_privacy_gateway.anonymizer.strategies import AnonymizationAction
from ai_privacy_gateway.anonymizer.vault import EncryptedVault

_TOKEN_PATTERN = re.compile(r"\u27e6PII:[A-Z0-9_]+:[0-9a-f]{8}\u27e7")


class ReIdentifier:
    def __init__(self, vault: EncryptedVault) -> None:
        self.vault = vault

    def reidentify(
        self,
        response_text: str,
        session_id: str,
        applied: list[AppliedAnonymization] | None = None,
    ) -> str:
        result = self._reidentify_tokens(response_text, session_id)
        if applied:
            result = self._reidentify_synthetic(result, session_id, applied)
        return result

    def _reidentify_tokens(self, text: str, session_id: str) -> str:
        def _sub(match: re.Match) -> str:
            placeholder = match.group(0)
            original = self.vault.retrieve(session_id, placeholder)
            return original if original is not None else placeholder

        return _TOKEN_PATTERN.sub(_sub, text)

    def _reidentify_synthetic(
        self, text: str, session_id: str, applied: list[AppliedAnonymization]
    ) -> str:
        result = text
        for item in applied:
            if item.action != AnonymizationAction.SYNTHETIC or not item.reversible:
                continue
            if item.replacement not in result:
                continue
            original = self.vault.retrieve(session_id, item.replacement)
            if original is not None:
                result = result.replace(item.replacement, original)
        return result
