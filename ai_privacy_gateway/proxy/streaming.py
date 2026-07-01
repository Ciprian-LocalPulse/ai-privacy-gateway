"""Streaming-safe re-identification.

SSE responses arrive in arbitrary-sized chunks that have no relationship
to our placeholder token boundaries — a `⟦PII:EMAIL:a1b2c3d4⟧` marker can
easily be split across two `data:` events. This buffer holds back just
enough trailing text on every `feed()` call to guarantee a full token (or
a full synthetic value) is visible before it gets processed and released
downstream.
"""

from __future__ import annotations

from ai_privacy_gateway.anonymizer.engine import AppliedAnonymization
from ai_privacy_gateway.anonymizer.reidentifier import ReIdentifier
from ai_privacy_gateway.anonymizer.vault import EncryptedVault


class StreamingReIdentifier:
    TOKEN_START = "\u27e6"
    TOKEN_END = "\u27e7"
    # Generous upper bound on how long a partial token or synthetic value
    # tail could be: longest entity-type name (~20 chars) + fixed marker
    # overhead, rounded well up for safety margin.
    MAX_HOLDBACK = 64

    def __init__(self, vault: EncryptedVault, session_id: str, applied: list[AppliedAnonymization]) -> None:
        self._reidentifier = ReIdentifier(vault)
        self._session_id = session_id
        self._applied = applied
        self._buffer = ""

    def _compute_safe_length(self, buf: str) -> int:
        idx = buf.rfind(self.TOKEN_START)
        if idx != -1 and self.TOKEN_END not in buf[idx:]:
            # An unterminated placeholder begins at idx — hold everything
            # from there onward until its terminator arrives in a later chunk.
            return idx
        # No pending partial placeholder: still keep a conservative tail
        # so a synthetic replacement value can't be split across chunks.
        return max(0, len(buf) - self.MAX_HOLDBACK)

    def feed(self, chunk: str) -> str:
        """Feed a new chunk of raw streamed text. Returns the portion that
        is now safe to emit downstream, already re-identified."""
        self._buffer += chunk
        safe_len = self._compute_safe_length(self._buffer)
        to_emit, self._buffer = self._buffer[:safe_len], self._buffer[safe_len:]
        if not to_emit:
            return ""
        return self._reidentifier.reidentify(to_emit, self._session_id, self._applied)

    def flush(self) -> str:
        """Call once the upstream stream has ended to emit any remaining
        buffered (and now necessarily complete) text."""
        remainder, self._buffer = self._buffer, ""
        if not remainder:
            return ""
        return self._reidentifier.reidentify(remainder, self._session_id, self._applied)
