"""Loads a policy pack from YAML into a validated `Policy` model."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from ai_privacy_gateway.policy.models import Policy


class PolicyLoadError(ValueError):
    pass


def load_policy(path: str | Path) -> Policy:
    file_path = Path(path)
    if not file_path.exists():
        raise PolicyLoadError(f"Policy file not found: {file_path}")

    try:
        raw = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PolicyLoadError(f"Invalid YAML in {file_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise PolicyLoadError(f"Policy file {file_path} must contain a YAML mapping at the top level.")

    try:
        return Policy.model_validate(raw)
    except ValidationError as exc:
        raise PolicyLoadError(f"Policy file {file_path} failed validation:\n{exc}") from exc
