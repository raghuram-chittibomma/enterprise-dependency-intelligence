"""Unit tests for MVP2 open-ended Graph RAG retrieval and LLM grounding.
"""

from __future__ import annotations

import json

import pytest

from src.graph.fallback_store import FallbackGraphStore
from src.nlquery.ask import ask
from src.nlquery.graphrag import retrieve_open_ended
from src.nlquery.llm import MISSING_API_KEY_TEXT, LLMAnswerGenerator
from src.ontology.entities import API, Application, Database, Service, Team
from src.ontology.relationships import Consumes, OwnedBy, ReadsFrom


def _seed() -> FallbackGraphStore:
    store = FallbackGraphStore()
    store.upsert_node(
        "Team",
        Team(
            id="team:1",
            name="Commerce Platform Team",
            source_system="team-ownership",
            source_record_id="1",
            business_area="Commerce",
        ),
    )
    store.upsert_node(
        "Application",
        Application(
            id="app:storefront",
            name="Storefront",
            source_system="cmdb",
            source_record_id="1",
            technology="React",
            environment="prod",
        ),
    )
    store.upsert_node(
        "API",
        API(
            id="api:customer",
            name="Customer API v1",
            source_system="api-catalog",
            source_record_id="1",
            version="v1",
            protocol="REST",
        ),
    )
    store.upsert_node(
        "Service",
        Service(
            id="svc:customer",
            name="Customer Service",
            source_system="cmdb",
            source_record_id="2",
            technology="Java",
            environment="prod",
        ),
    )
    store.upsert_node(
        "Database",
        Database(
            id="db:customer",
            name="Customer Database",
            source_system="db-metadata",
            source_record_id="1",
            engine="PostgreSQL",
        ),
    )
    store.upsert_relationship(
        "OWNED_BY",
        OwnedBy(
            source_id="app:storefront",
            target_id="team:1",
            source_system="team-ownership",
            source_record_id="1",
        ),
        "Application",
        "Team",
    )
    store.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="app:storefront",
            target_id="api:customer",
            source_system="api-catalog",
            source_record_id="1",
        ),
        "Application",
        "API",
    )
    store.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="api:customer",
            target_id="svc:customer",
            source_system="api-catalog",
            source_record_id="2",
        ),
        "API",
        "Service",
    )
    store.upsert_relationship(
        "READS_FROM",
        ReadsFrom(
            source_id="svc:customer",
            target_id="db:customer",
            source_system="db-metadata",
            source_record_id="1",
        ),
        "Service",
        "Database",
    )
    return store


class TestRetrieveOpenEnded:
    def test_resolves_mentioned_entity_and_builds_subgraph(self) -> None:
        store = _seed()
        result = retrieve_open_ended(
            store, "What would break if we retired Customer API v1?"
        )
        assert result.status == "ok"
        assert result.open_ended
        assert result.open_subgraph_nodes is not None
        names = {n.name for n in result.open_subgraph_nodes}
        assert "Customer API v1" in names
        assert "Storefront" in names
        assert result.open_subgraph_edges
        assert any(e.rel_type == "CONSUMES" for e in result.open_subgraph_edges)

    def test_no_mention_is_not_found(self) -> None:
        store = _seed()
        result = retrieve_open_ended(store, "What is the weather in Austin?")
        assert result.status == "not_found"
        assert result.open_ended


class _FakeClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls = 0

    def complete(self, *, system: str, user: str) -> str:
        self.calls += 1
        return json.dumps(self.payload)


class TestLLMAnswerGenerator:
    def test_filters_citations_to_retrieved_edges(self) -> None:
        store = _seed()
        retrieval = retrieve_open_ended(
            store, "What depends on Customer API v1 in our landscape?"
        )
        assert retrieval.status == "ok"
        edge = next(e for e in retrieval.open_subgraph_edges if e.rel_type == "CONSUMES")
        client = _FakeClient(
            {
                "status": "answered",
                "text": f"{edge.source_name} consumes {edge.target_name}.",
                "citations": [
                    {
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "rel_type": edge.rel_type,
                    },
                    {
                        "source_id": "fake",
                        "target_id": "fake",
                        "rel_type": "CONSUMES",
                    },
                ],
            }
        )
        answer = LLMAnswerGenerator(client=client).generate(retrieval)
        assert answer.status == "answered"
        assert answer.question_type == "open_ended"
        assert len(answer.evidence) == 1
        assert answer.evidence[0].source_id == edge.source_id
        assert answer.evidence[0].source_system == edge.source_system

    def test_answered_without_valid_citations_becomes_insufficient(self) -> None:
        store = _seed()
        retrieval = retrieve_open_ended(store, "Impact of retiring Customer API v1?")
        client = _FakeClient(
            {
                "status": "answered",
                "text": "Everything explodes.",
                "citations": [
                    {"source_id": "x", "target_id": "y", "rel_type": "CONSUMES"},
                ],
            }
        )
        answer = LLMAnswerGenerator(client=client).generate(retrieval)
        assert answer.status == "insufficient_evidence"
        assert answer.evidence == []

    def test_missing_api_key_message_when_no_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        store = _seed()
        retrieval = retrieve_open_ended(store, "Impact of retiring Customer API v1?")
        answer = LLMAnswerGenerator(client=None).generate(retrieval)
        assert answer.status == "unsupported"
        assert MISSING_API_KEY_TEXT in answer.text


class TestAskRouting:
    def test_closed_template_still_deterministic_with_rag_on(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRAPH_RAG_ENABLED", "true")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        store = _seed()
        answer = ask(store, "What does Storefront depend on?")
        assert answer.status == "answered"
        assert answer.question_type == "depends_on"
        assert "Customer API v1" in answer.text

    def test_unsupported_when_rag_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GRAPH_RAG_ENABLED", raising=False)
        store = _seed()
        answer = ask(store, "What would break if we retired Customer API v1?")
        assert answer.status == "unsupported"
        assert "fixed set" in answer.text.lower() or "only answer" in answer.text.lower()

    def test_open_ended_uses_llm_when_rag_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GRAPH_RAG_ENABLED", "true")
        store = _seed()
        retrieval = retrieve_open_ended(
            store, "What would break if we retired Customer API v1?"
        )
        edge = next(e for e in retrieval.open_subgraph_edges if e.source_id == "app:storefront")

        class Injected(LLMAnswerGenerator):
            def __init__(self) -> None:
                super().__init__(
                    client=_FakeClient(
                        {
                            "status": "answered",
                            "text": "Storefront would be impacted.",
                            "citations": [
                                {
                                    "source_id": edge.source_id,
                                    "target_id": edge.target_id,
                                    "rel_type": edge.rel_type,
                                }
                            ],
                        }
                    )
                )

        # `src.nlquery.ask` is shadowed by the `ask` function re-export in
        # `src.nlquery.__init__`; load the real module via importlib.
        import importlib

        ask_module = importlib.import_module("src.nlquery.ask")
        monkeypatch.setattr(ask_module, "LLMAnswerGenerator", Injected)
        answer = ask(store, "What would break if we retired Customer API v1?")
        assert answer.status == "answered"
        assert answer.question_type == "open_ended"
        assert "Storefront" in answer.text
        assert answer.evidence
