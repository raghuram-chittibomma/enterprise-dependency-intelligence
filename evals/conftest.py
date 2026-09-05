"""Pytest fixture: a FallbackGraphStore seeded by ingesting the real
Meridian sample dataset (`data/sample/`). Shared by every golden scenario
so the evals exercise the same graph the app does at runtime.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph.fallback_store import FallbackGraphStore
from src.ingestion.pipeline import run_ingestion

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"


@pytest.fixture(autouse=True)
def _mvp1_golden_disables_graph_rag(monkeypatch: pytest.MonkeyPatch) -> None:
    """MVP1 closed-question scenarios must stay deterministic even if a
    developer has GRAPH_RAG_ENABLED set in their shell.
    """
    monkeypatch.delenv("GRAPH_RAG_ENABLED", raising=False)
    monkeypatch.delenv("HYBRID_DOC_RAG_ENABLED", raising=False)
    monkeypatch.delenv("AGENTIC_INVESTIGATION_ENABLED", raising=False)
    monkeypatch.delenv("INTELLIGENCE_NARRATIVE_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture(scope="module")
def store():
    graph = FallbackGraphStore()
    result = run_ingestion(graph, data_dir=SAMPLE_DIR, unresolved_path=None)
    assert result.unresolved == [], f"golden graph has unresolved refs: {result.unresolved}"
    assert graph.count_nodes() == 55
    assert graph.count_relationships() == 131
    yield graph
    graph.close()
