"""Helpers to attach document chunks to open-ended retrieval (MVP3)."""

from __future__ import annotations

from pathlib import Path

from src.nlquery.config import hybrid_doc_top_k, openai_api_key
from src.retrieval.embeddings import FakeEmbedder, OpenAIEmbedder
from src.retrieval.index_docs import embedding_model, vector_store_path
from src.retrieval.vector_store import RetrievedChunk, SQLiteVectorStore


def retrieve_doc_chunks(
    question: str,
    *,
    top_k: int | None = None,
    store_path: Path | None = None,
    embedder=None,
) -> list[RetrievedChunk]:
    """Return top-k chunks for `question`. Empty list if the store is missing."""
    path = store_path or vector_store_path()
    if not path.exists():
        return []
    client = embedder
    if client is None:
        key = openai_api_key()
        client = OpenAIEmbedder(api_key=key, model=embedding_model()) if key else FakeEmbedder()
    store = SQLiteVectorStore(path)
    try:
        if store.count() == 0:
            return []
        query_vec = client.embed([question])[0]
        return store.search(query_vec, top_k=top_k or hybrid_doc_top_k())
    finally:
        store.close()
