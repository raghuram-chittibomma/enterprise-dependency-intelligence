"""MVP2 open-ended Graph RAG eval scenarios — faithfulness, citation, refusal.

Uses fake LLM responses (no network). Live OpenAI checks stay optional and
are not required for the commit gate (`EVAL_STRATEGY.md`).
"""

from __future__ import annotations

import json

import pytest

from src.nlquery.graphrag import retrieve_open_ended
from src.nlquery.llm import LLMAnswerGenerator


class _FakeClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def complete(self, *, system: str, user: str) -> str:
        return json.dumps(self.payload)


def test_open_ended_retrieval_finds_customer_api(store) -> None:
    result = retrieve_open_ended(
        store, "What would be impacted if we retired Customer API v1?"
    )
    assert result.status == "ok"
    assert result.open_ended
    names = {n.name for n in (result.open_subgraph_nodes or [])}
    assert "Customer API v1" in names
    assert result.open_subgraph_edges


def test_faithfulness_rejects_fabricated_citations(store) -> None:
    retrieval = retrieve_open_ended(
        store, "What would be impacted if we retired Customer API v1?"
    )
    answer = LLMAnswerGenerator(
        client=_FakeClient(
            {
                "status": "answered",
                "text": "Everything depends on a fictional edge.",
                "citations": [
                    {
                        "source_id": "nope",
                        "target_id": "nope",
                        "rel_type": "CONSUMES",
                    }
                ],
            }
        )
    ).generate(retrieval)
    assert answer.status == "insufficient_evidence"
    assert answer.evidence == []


def test_faithfulness_accepts_in_subgraph_citations(store) -> None:
    retrieval = retrieve_open_ended(
        store, "What would be impacted if we retired Customer API v1?"
    )
    assert retrieval.open_subgraph_edges
    edge = retrieval.open_subgraph_edges[0]
    answer = LLMAnswerGenerator(
        client=_FakeClient(
            {
                "status": "answered",
                "text": f"{edge.source_name} is linked via {edge.rel_type}.",
                "citations": [
                    {
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "rel_type": edge.rel_type,
                    }
                ],
            }
        )
    ).generate(retrieval)
    assert answer.status == "answered"
    assert len(answer.evidence) == 1
    assert answer.evidence[0].source_id == edge.source_id


def test_refusal_when_model_says_insufficient(store) -> None:
    retrieval = retrieve_open_ended(
        store, "What would be impacted if we retired Customer API v1?"
    )
    answer = LLMAnswerGenerator(
        client=_FakeClient(
            {
                "status": "insufficient_evidence",
                "text": "Not enough in the subgraph.",
                "citations": [],
            }
        )
    ).generate(retrieval)
    assert answer.status == "insufficient_evidence"


def test_open_ended_not_found_for_unknown_topic(store) -> None:
    retrieval = retrieve_open_ended(store, "Explain quantum entanglement for toddlers")
    assert retrieval.status == "not_found"


@pytest.mark.integration
def test_live_openai_open_ended_optional(store, monkeypatch: pytest.MonkeyPatch) -> None:
    """Skipped unless OPENAI_API_KEY is present in the environment."""
    import os

    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    monkeypatch.setenv("GRAPH_RAG_ENABLED", "true")
    from src.nlquery.ask import ask

    answer = ask(store, "What would be impacted if we retired Customer API v1?")
    assert answer.status in {"answered", "insufficient_evidence"}
    if answer.status == "answered":
        assert answer.evidence
        retrieved = retrieve_open_ended(
            store, "What would be impacted if we retired Customer API v1?"
        )
        allowed = {
            (e.source_id, e.target_id, e.rel_type) for e in (retrieved.open_subgraph_edges or [])
        }
        for edge in answer.evidence:
            assert (edge.source_id, edge.target_id, edge.rel_type) in allowed
