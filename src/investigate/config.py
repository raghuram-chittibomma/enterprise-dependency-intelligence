"""MVP4 Agentic Investigation configuration (`ADR-0007`)."""

from __future__ import annotations

import os

from src.env_loader import load_project_env
from src.nlquery.config import openai_api_key, openai_model

load_project_env()

DEFAULT_MAX_TOOL_CALLS = 3
DEFAULT_MAX_TRAVERSAL_DEPTH = 4


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def agentic_investigation_enabled() -> bool:
    return _truthy("AGENTIC_INVESTIGATION_ENABLED")


def agentic_max_tool_calls() -> int:
    raw = os.environ.get("AGENTIC_MAX_TOOL_CALLS", "").strip()
    if not raw:
        return DEFAULT_MAX_TOOL_CALLS
    try:
        return max(0, min(int(raw), 10))
    except ValueError:
        return DEFAULT_MAX_TOOL_CALLS


def agentic_max_traversal_depth() -> int:
    return DEFAULT_MAX_TRAVERSAL_DEPTH


__all__ = [
    "agentic_investigation_enabled",
    "agentic_max_tool_calls",
    "agentic_max_traversal_depth",
    "openai_api_key",
    "openai_model",
]
