"""MVP2 Graph RAG + MVP3 Hybrid Doc RAG configuration (`ADR-0005`, `ADR-0006`).

Env-only; never commit secrets.
"""

from __future__ import annotations

import os

from src.env_loader import load_project_env

load_project_env()

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_HYBRID_DOC_TOP_K = 5


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def graph_rag_enabled() -> bool:
    return _truthy("GRAPH_RAG_ENABLED")


def hybrid_doc_rag_enabled() -> bool:
    """Hybrid requires Graph RAG; the doc flag alone is not enough."""
    return graph_rag_enabled() and _truthy("HYBRID_DOC_RAG_ENABLED")


def openai_api_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return key or None


def openai_model() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL


def hybrid_doc_top_k() -> int:
    raw = os.environ.get("HYBRID_DOC_TOP_K", "").strip()
    if not raw:
        return DEFAULT_HYBRID_DOC_TOP_K
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_HYBRID_DOC_TOP_K
