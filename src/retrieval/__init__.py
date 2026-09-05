"""MVP3 document retrieval: chunking, embeddings, local SQLite vectors (`ADR-0006`)."""

from __future__ import annotations

from src.retrieval.chunking import chunk_markdown
from src.retrieval.embeddings import Embedder, FakeEmbedder, OpenAIEmbedder
from src.retrieval.vector_store import RetrievedChunk, SQLiteVectorStore

__all__ = [
    "Embedder",
    "FakeEmbedder",
    "OpenAIEmbedder",
    "RetrievedChunk",
    "SQLiteVectorStore",
    "chunk_markdown",
]
