"""MVP5 Advanced Intelligence configuration (`ADR-0008`)."""

from __future__ import annotations

import os

from src.env_loader import load_project_env
from src.nlquery.config import openai_api_key, openai_model

load_project_env()


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def intelligence_narrative_enabled() -> bool:
    return _truthy("INTELLIGENCE_NARRATIVE_ENABLED")


__all__ = [
    "intelligence_narrative_enabled",
    "openai_api_key",
    "openai_model",
]
