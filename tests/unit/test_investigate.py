"""Unit tests for MVP4 investigation skeleton + allowlisted tools (no LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph.fallback_store import FallbackGraphStore
from src.ingestion.pipeline import run_ingestion
from src.investigate.agent import _resolve_seed
from src.investigate.tools import TOOL_NAMES, EvidenceBundle, run_skeleton, run_tool
from src.nlquery.resolution import resolve_entity

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample"


@pytest.fixture(scope="module")
def store():
    graph = FallbackGraphStore()
    result = run_ingestion(graph, data_dir=SAMPLE_DIR, unresolved_path=None)
    assert result.unresolved == []
    yield graph
    graph.close()


def test_skeleton_always_records_required_steps(store, monkeypatch) -> None:
    monkeypatch.delenv("HYBRID_DOC_RAG_ENABLED", raising=False)
    seed = resolve_entity(store, "Customer API v1").entity
    assert seed is not None
    bundle, steps = run_skeleton(store, seed, "Impact of retiring Customer API v1?")
    tools = [s.tool for s in steps if s.phase == "skeleton"]
    assert "entity_detail" in tools
    assert "direct_dependencies" in tools
    assert tools.count("traverse") == 2
    assert "owners_rollup" in tools
    assert "capabilities_rollup" in tools
    assert "doc_search" in tools
    assert bundle.edges


def test_unknown_tool_rejected(store) -> None:
    seed = resolve_entity(store, "Storefront").entity
    assert seed is not None
    bundle = EvidenceBundle()
    with pytest.raises(ValueError, match="not allowlisted"):
        run_tool(store, bundle, "run_cypher", {}, seed=seed)


def test_allowlisted_tool_names() -> None:
    assert "traverse" in TOOL_NAMES
    assert "find_paths" in TOOL_NAMES
    assert "run_cypher" not in TOOL_NAMES


def test_resolve_seed_fuzzy_partial_name(store) -> None:
    """Informal names like 'customer api' should resolve to Customer API v1."""
    seed, matched, ambiguous = _resolve_seed(
        store, "what impact we will have if retire customer api"
    )
    assert not ambiguous
    assert seed is not None
    assert seed.name == "Customer API v1"
    assert "customer" in matched.lower()


def test_traverse_tool_adds_edges(store) -> None:
    seed = resolve_entity(store, "Customer API v1").entity
    assert seed is not None
    bundle = EvidenceBundle()
    bundle.remember_entity(seed.id, seed.name)
    summary = run_tool(
        store,
        bundle,
        "traverse",
        {"direction": "downstream", "max_depth": 2},
        seed=seed,
    )
    assert "nodes=" in summary
    assert bundle.edges
