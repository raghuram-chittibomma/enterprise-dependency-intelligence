"""Unit tests for MVP3 chunk/embed/vector index (fake embedder, no network)."""

from __future__ import annotations

from pathlib import Path

from src.datagen import generate
from src.retrieval.chunking import chunk_markdown
from src.retrieval.embeddings import FakeEmbedder, cosine_similarity
from src.retrieval.index_docs import index_docs
from src.retrieval.vector_store import SQLiteVectorStore


def test_chunk_markdown_produces_stable_ids() -> None:
    md = "# Title\n\nFirst paragraph.\n\nSecond paragraph with more text."
    first = chunk_markdown("doc:arch-docs:demo", md)
    second = chunk_markdown("doc:arch-docs:demo", md)
    assert first
    assert [c.chunk_id for c in first] == [c.chunk_id for c in second]


def test_fake_embedder_is_deterministic() -> None:
    emb = FakeEmbedder(dim=32)
    a = emb.embed(["Order Database backup RPO"])[0]
    b = emb.embed(["Order Database backup RPO"])[0]
    assert a == b
    assert cosine_similarity(a, b) > 0.99


def test_index_docs_and_search_with_fake_embedder(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path / "sample")
    monkeypatch.setattr(generate, "DOCS_DIR", tmp_path / "sample" / "docs")
    generate.generate_all()
    store_path = tmp_path / "vectors.sqlite3"
    n = index_docs(
        docs_dir=tmp_path / "sample" / "docs",
        store_path=store_path,
        embedder=FakeEmbedder(),
        allow_fake=True,
    )
    assert n > 0
    store = SQLiteVectorStore(store_path)
    assert store.count() == n
    query = FakeEmbedder().embed(["What is the Order Database backup RPO?"])[0]
    hits = store.search(query, top_k=3)
    store.close()
    assert hits
    joined = " ".join(h.text for h in hits)
    assert "RPO" in joined or "Order Database" in joined
