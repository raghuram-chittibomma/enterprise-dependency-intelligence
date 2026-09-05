"""MVP3 Hybrid Graph + Document RAG evals — fake embedder/LLM (no network)."""

from __future__ import annotations

import json

from src.nlquery.graphrag import retrieve_open_ended
from src.nlquery.llm import LLMAnswerGenerator
from src.retrieval.vector_store import RetrievedChunk


class _FakeClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.last_user = ""

    def complete(self, *, system: str, user: str) -> str:
        self.last_user = user
        return json.dumps(self.payload)


def _chunk(
    *,
    document_id: str = "doc:arch-docs:storefront-architecture",
    chunk_id: str = "doc:arch-docs:storefront-architecture#c0-abc",
    text: str = "Storefront uses a blue-green deploy window every Tuesday at 02:00 UTC.",
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        document_name="Storefront Architecture Notes",
        text=text,
        source_system="arch-docs",
        source_record_id="storefront-architecture",
        score=0.9,
    )


def test_doc_only_citation_accepted(store) -> None:
    retrieval = retrieve_open_ended(
        store,
        "When is the Storefront blue-green deploy window?",
        include_docs=True,
        doc_chunks=[_chunk()],
    )
    assert retrieval.status == "ok"
    assert retrieval.doc_chunks
    chunk = retrieval.doc_chunks[0]
    answer = LLMAnswerGenerator(
        client=_FakeClient(
            {
                "status": "answered",
                "text": "Tuesday at 02:00 UTC.",
                "citations": [],
                "doc_citations": [
                    {"document_id": chunk.document_id, "chunk_id": chunk.chunk_id}
                ],
            }
        )
    ).generate(retrieval)
    assert answer.status == "answered"
    assert answer.doc_evidence
    assert answer.doc_evidence[0].chunk_id == chunk.chunk_id


def test_graph_plus_doc_fusion_citations(store) -> None:
    retrieval = retrieve_open_ended(
        store,
        "What does Storefront depend on, and when is its deploy window?",
        include_docs=True,
        doc_chunks=[_chunk()],
    )
    assert retrieval.open_subgraph_edges
    edge = retrieval.open_subgraph_edges[0]
    chunk = retrieval.doc_chunks[0]
    answer = LLMAnswerGenerator(
        client=_FakeClient(
            {
                "status": "answered",
                "text": "Storefront depends on graph neighbors and deploys Tuesday 02:00 UTC.",
                "citations": [
                    {
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "rel_type": edge.rel_type,
                    }
                ],
                "doc_citations": [
                    {"document_id": chunk.document_id, "chunk_id": chunk.chunk_id}
                ],
            }
        )
    ).generate(retrieval)
    assert answer.status == "answered"
    assert answer.evidence
    assert answer.doc_evidence


def test_refusal_when_doc_citation_fabricated(store) -> None:
    retrieval = retrieve_open_ended(
        store,
        "When is the Storefront blue-green deploy window?",
        include_docs=True,
        doc_chunks=[_chunk()],
    )
    answer = LLMAnswerGenerator(
        client=_FakeClient(
            {
                "status": "answered",
                "text": "Invented fact.",
                "citations": [],
                "doc_citations": [
                    {"document_id": "doc:arch-docs:nope", "chunk_id": "missing#c0"}
                ],
            }
        )
    ).generate(retrieval)
    assert answer.status == "insufficient_evidence"
    assert answer.doc_evidence == []


def test_refusal_when_docs_irrelevant_and_model_guesses(store) -> None:
    """Irrelevant chunks + no valid cites → refuse (FR19)."""
    retrieval = retrieve_open_ended(
        store,
        "What is the secret launch code for Storefront?",
        include_docs=True,
        doc_chunks=[
            _chunk(
                text="Audience sync runs hourly; opportunity sync runs every 15 minutes."
            )
        ],
    )
    answer = LLMAnswerGenerator(
        client=_FakeClient(
            {
                "status": "answered",
                "text": "The launch code is 42.",
                "citations": [],
                "doc_citations": [],
            }
        )
    ).generate(retrieval)
    assert answer.status == "insufficient_evidence"
