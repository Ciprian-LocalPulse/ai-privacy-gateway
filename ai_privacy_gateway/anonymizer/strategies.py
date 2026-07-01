"""Anonymization strategies.

Four strategies, each trading off reversibility against how much the
replacement disturbs the LLM's ability to reason about the text:

| Strategy  | Reversible | LLM-friendly | Typical use |
|-----------|-----------|--------------|--------------|
| mask      | no        | low          | Data that must never leave the building in any form (secrets) |
| tokenize  | yes       | low-medium   | Data the caller needs echoed back exactly (a ticket number, a CNP the user asked to be reasoned about) |
| hash      | no*       | low          | Data useful for correlation across requests but never needed in plaintext again |
| synthetic | partial   | high         | Free text where the model needs *a* plausible name/email/IBAN to keep the response coherent, but not the real one |

`hash` is one-way by design but is *deterministic* per (secret key,
value) pair — the same input always hashes to the same token — which is
what makes cross-request correlation possible without ever storing the
plaintext.

`synthetic` is "partial" because we do store a reverse mapping
(synthetic value -> original) in the vault so that if the LLM echoes the
synthetic value back verbatim, we can restore the original. If the model
*transforms* the synthetic value in its output (e.g., abbreviates a name),
we cannot recover the original from that transformed text — see
docs/threat-model.md for the full discussion of this tradeoff.
"""

from __future__ import annotations

import hashlib
import hmac
import random
import secrets
import string
from calendar import monthrange
from dataclasses import dataclass
from enum import Enum

from ai_privacy_gateway.detectors.base import Entity, EntityType
from ai_privacy_gateway.detectors.regex_detectors import _CNP_WEIGHTS  # reuse the exact checksum weights


class AnonymizationAction(str, Enum):
    MASK = "mask"
    TOKENIZE = "tokenize"
    HASH = "hash"
    SYNTHETIC = "synthetic"
    ALLOW = "allow"  # policy says: leave this entity alone


@dataclass(frozen=True, slots=True)
class StrategyOutput:
    replacement: str
    action: AnonymizationAction
    reversible: bool
    # For TOKENIZE and SYNTHETIC, the (token_or_synthetic_value, original_value) pair
    # that the caller (AnonymizationEngine) should persist in the vault.
    vault_entry: tuple[str, str] | None = None


def mask(entity: Entity) -> StrategyOutput:
    return StrategyOutput(
        replacement=f"[REDACTED_{entity.entity_type.value}]",
        action=AnonymizationAction.MASK,
        reversible=False,
    )


def tokenize(entity: Entity) -> StrategyOutput:
    token = secrets.token_hex(4)
    placeholder = f"\u27e6PII:{entity.entity_type.value}:{token}\u27e7"
    return StrategyOutput(
        replacement=placeholder,
        action=AnonymizationAction.TOKENIZE,
        reversible=True,
        vault_entry=(placeholder, entity.text),
    )


def hash_value(entity: Entity, secret_key: bytes) -> StrategyOutput:
    digest = hmac.new(secret_key, entity.text.encode("utf-8"), hashlib.sha256).hexdigest()[:12]
    return StrategyOutput(
        replacement=f"[HASH_{entity.entity_type.value}:{digest}]",
        action=AnonymizationAction.HASH,
        reversible=False,
    )


# ---------------------------------------------------------------------------
# Synthetic value generation
# ---------------------------------------------------------------------------

_SAMPLE_PERSON_NAMES = [
    "Alex Popescu", "Maria Ionescu", "Jordan Reyes", "Sam Whitfield",
    "Elena Marinescu", "Chris Okafor", "Taylor Nakamura", "Andrei Dumitrescu",
]
_SAMPLE_ORG_NAMES = [
    "Contoso Ltd", "Fabrikam Inc", "Northwind Traders", "Tailspin Toys",
    "Woodgrove Bank", "Adventure Works SRL",
]
_SAMPLE_ADDRESS = "123 Sample Street, Example City"


def _digits(n: int, width: int) -> list[int]:
    s = str(n).zfill(width)
    return [int(c) for c in s]


def _generate_synthetic_cnp() -> str:
    s = random.choice([1, 2, 5, 6])
    yy = random.randint(0, 99)
    mm = random.randint(1, 12)
    year = (1900 if s in (1, 2) else 2000) + yy
    day_max = monthrange(year, mm)[1]
    dd = random.randint(1, day_max)
    county = random.choice([1, 10, 22, 40, 51])
    nnn = random.randint(1, 999)

    digits = _digits(s, 1) + _digits(yy, 2) + _digits(mm, 2) + _digits(dd, 2) + _digits(county, 2) + _digits(nnn, 3)
    total = sum(d * w for d, w in zip(digits, _CNP_WEIGHTS))
    remainder = total % 11
    control = 1 if remainder == 10 else remainder
    return "".join(str(d) for d in digits) + str(control)


def _generate_synthetic_iban(original: str) -> str:
    compact = original.replace(" ", "")
    country = compact[:2] if compact[:2].isalpha() else "RO"
    bban_length = max(len(compact) - 4, 16)
    bban = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(bban_length))
    provisional = f"{country}00{bban}"
    rearranged = provisional[4:] + provisional[:4]
    numeric_str = "".join(ch if ch.isdigit() else str(int(ch, 36)) for ch in rearranged)
    check = 98 - (int(numeric_str) % 97)
    return f"{country}{check:02d}{bban}"


def _generate_synthetic_credit_card(length: int = 16) -> str:
    payload = [secrets.randbelow(10) for _ in range(length - 1)]
    payload[0] = 4  # cosmetic Visa-like prefix; not a real issuer BIN range
    total = 0
    for i, d in enumerate(reversed(payload)):
        if i % 2 == 0:
            d2 = d * 2
            total += d2 - 9 if d2 > 9 else d2
        else:
            total += d
    check_digit = (10 - total % 10) % 10
    return "".join(map(str, payload)) + str(check_digit)


def _generate_synthetic_ssn() -> str:
    # Area codes 900-999 are guaranteed never issued to a real person by the SSA.
    area = random.randint(900, 999)
    group = random.randint(1, 99)
    serial = random.randint(1, 9999)
    return f"{area:03d}-{group:02d}-{serial:04d}"


def _generate_synthetic_email() -> str:
    return f"user.{secrets.token_hex(3)}@example.com"


def _generate_synthetic_phone(original: str) -> str:
    if original.lstrip("+").startswith("40") or original.startswith("07"):
        return "07" + "".join(str(secrets.randbelow(10)) for _ in range(8))
    digit_count = sum(1 for c in original if c.isdigit())
    return "+" + "".join(str(secrets.randbelow(10)) for _ in range(max(digit_count, 8)))


def _generate_synthetic_vat(original: str) -> str:
    country = original[:2] if original[:2].isalpha() else "RO"
    return country + "".join(str(secrets.randbelow(10)) for _ in range(9))


_SYNTHETIC_GENERATORS = {
    EntityType.PERSON_NAME: lambda e: secrets.choice(_SAMPLE_PERSON_NAMES),
    EntityType.ORGANIZATION: lambda e: secrets.choice(_SAMPLE_ORG_NAMES),
    EntityType.ADDRESS: lambda e: _SAMPLE_ADDRESS,
    EntityType.RO_CNP: lambda e: _generate_synthetic_cnp(),
    EntityType.IBAN: lambda e: _generate_synthetic_iban(e.text),
    EntityType.CREDIT_CARD: lambda e: _generate_synthetic_credit_card(len(e.text.replace(" ", "").replace("-", ""))),
    EntityType.US_SSN: lambda e: _generate_synthetic_ssn(),
    EntityType.EMAIL: lambda e: _generate_synthetic_email(),
    EntityType.PHONE_NUMBER: lambda e: _generate_synthetic_phone(e.text),
    EntityType.EU_VAT_NUMBER: lambda e: _generate_synthetic_vat(e.text),
}


def synthetic(entity: Entity) -> StrategyOutput:
    generator = _SYNTHETIC_GENERATORS.get(entity.entity_type)
    if generator is None:
        # No tasteful synthetic generator for this type (e.g. API keys, medical
        # context keywords) — fall back to a plain mask instead of guessing.
        return mask(entity)
    replacement = generator(entity)
    return StrategyOutput(
        replacement=replacement,
        action=AnonymizationAction.SYNTHETIC,
        reversible=True,
        vault_entry=(replacement, entity.text),
    )


def allow(entity: Entity) -> StrategyOutput:
    return StrategyOutput(replacement=entity.text, action=AnonymizationAction.ALLOW, reversible=False)
