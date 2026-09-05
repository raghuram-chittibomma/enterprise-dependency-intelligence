"""MVP2 Graph RAG configuration (`ADR-0005`). Env-only; never commit secrets.
"""

from __future__ import annotations

import os

from src.env_loader import load_project_env

load_project_env()

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def graph_rag_enabled() -> bool:
    return os.environ.get("GRAPH_RAG_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def openai_api_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return key or None


def openai_model() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
