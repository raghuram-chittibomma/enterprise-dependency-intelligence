"""MVP4 Agentic Investigate evals — fake LLM, no network (`ADR-0007`)."""

from __future__ import annotations

import json

from src.investigate.agent import ScriptedClient, run_investigation
from src.investigate.tools import run_skeleton
from src.nlquery.resolution import resolve_entity


def _report(*, edge, status: str = "answered", extra_findings: list | None = None) -> str:
    return json.dumps(
        {
            "status": status,
            "summary": f"Impact centers on {edge.source_name} / {edge.target_name}.",
            "findings": extra_findings
            or [f"{edge.source_name} -[{edge.rel_type}]-> {edge.target_name}"],
            "citations": [
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "rel_type": edge.rel_type,
                }
            ],
            "doc_citations": [],
        }
    )


def test_skeleton_runs_before_adaptive_and_report(store, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_INVESTIGATION_ENABLED", "true")
    monkeypatch.delenv("HYBRID_DOC_RAG_ENABLED", raising=False)
    seed = resolve_entity(store, "Customer API v1").entity
    assert seed is not None
    bundle, _ = run_skeleton(store, seed, "retire Customer API v1")
    assert bundle.edges
    edge = bundle.edges[0]

    client = ScriptedClient(
        replies=[
            json.dumps({"tool": None, "args": {}, "done": True}),
            _report(edge=edge),
        ]
    )
    result = run_investigation(
        store,
        "What would be impacted if we retired Customer API v1?",
        client=client,
        max_tool_calls=3,
    )
    assert result.status == "answered"
    assert result.seed_entity is not None
    assert result.seed_entity.name == "Customer API v1"
    phases = [s.phase for s in result.steps]
    assert phases.count("skeleton") >= 5
    assert "report" in phases
    assert result.evidence


def test_tool_budget_enforced(store, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_INVESTIGATION_ENABLED", "true")
    monkeypatch.delenv("HYBRID_DOC_RAG_ENABLED", raising=False)
    seed = resolve_entity(store, "Customer API v1").entity
    assert seed is not None
    bundle, _ = run_skeleton(store, seed, "retire Customer API v1")
    edge = bundle.edges[0]

    client = ScriptedClient(
        replies=[
            json.dumps(
                {
                    "tool": "traverse",
                    "args": {"direction": "downstream", "max_depth": 2},
                    "done": False,
                }
            ),
            # With max_tool_calls=1 the loop stops after one adaptive call;
            # the next complete() is report synthesis.
            _report(edge=edge),
        ]
    )
    result = run_investigation(
        store,
        "What would be impacted if we retired Customer API v1?",
        client=client,
        max_tool_calls=1,
    )
    adaptive = [s for s in result.steps if s.phase == "adaptive" and s.tool == "traverse"]
    assert len(adaptive) == 1
    assert result.status == "answered"


def test_fabricated_citations_refuse(store, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_INVESTIGATION_ENABLED", "true")
    monkeypatch.delenv("HYBRID_DOC_RAG_ENABLED", raising=False)
    client = ScriptedClient(
        replies=[
            json.dumps({"tool": None, "args": {}, "done": True}),
            json.dumps(
                {
                    "status": "answered",
                    "summary": "Invented.",
                    "findings": ["Nope"],
                    "citations": [
                        {
                            "source_id": "nope",
                            "target_id": "nope",
                            "rel_type": "CONSUMES",
                        }
                    ],
                    "doc_citations": [],
                }
            ),
        ]
    )
    result = run_investigation(
        store,
        "What would be impacted if we retired Customer API v1?",
        client=client,
        max_tool_calls=0,
    )
    assert result.status == "insufficient_evidence"
    assert result.evidence == []


def test_not_found_seed(store, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_INVESTIGATION_ENABLED", "true")
    result = run_investigation(
        store,
        "What happens if we retire Completely Fake System XYZ?",
        client=ScriptedClient(replies=[]),
        max_tool_calls=0,
    )
    assert result.status == "not_found"
