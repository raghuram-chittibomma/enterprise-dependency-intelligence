"""Index architecture docs into the local SQLite vector store.

Run after datagen + ingestion:

    python -m src.retrieval.index_docs
"""

from __future__ import annotations

import os
from pathlib import Path

from src.env_loader import load_project_env
from src.ingestion.identity import make_id
from src.ingestion.parsers import architecture_docs as docs_parser
from src.nlquery.config import openai_api_key
from src.retrieval.chunking import chunk_markdown
from src.retrieval.embeddings import FakeEmbedder, OpenAIEmbedder
from src.retrieval.vector_store import DEFAULT_VECTOR_PATH, SQLiteVectorStore

DEFAULT_DOCS_DIR = Path("data/sample/docs")
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def embedding_model() -> str:
    return (
        os.environ.get("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip()
        or DEFAULT_EMBEDDING_MODEL
    )


def vector_store_path() -> Path:
    raw = os.environ.get("VECTOR_STORE_PATH", "").strip()
    return Path(raw) if raw else DEFAULT_VECTOR_PATH


def build_embedder(*, allow_fake: bool = False):
    key = openai_api_key()
    if key:
        return OpenAIEmbedder(api_key=key, model=embedding_model())
    if allow_fake:
        return FakeEmbedder()
    raise RuntimeError(
        "OPENAI_API_KEY is required to index documents (or pass allow_fake=True for tests)."
    )


def index_docs(
    docs_dir: Path = DEFAULT_DOCS_DIR,
    store_path: Path | None = None,
    *,
    embedder=None,
    allow_fake: bool = False,
) -> int:
    """Chunk + embed all docs under `docs_dir`. Returns number of chunks upserted."""
    load_project_env()
    store = SQLiteVectorStore(store_path or vector_store_path())
    client = embedder or build_embedder(allow_fake=allow_fake)
    rows = docs_parser.read(docs_dir)
    store.clear()
    total = 0
    for row in rows:
        document_id = make_id("Document", docs_parser.SOURCE_SYSTEM, row["slug"])
        # Body already includes the markdown title heading from datagen.
        markdown = row["body"]
        chunks = chunk_markdown(document_id, markdown)
        if not chunks:
            continue
        embeddings = client.embed([c.text for c in chunks])
        for chunk, emb in zip(chunks, embeddings, strict=True):
            store.upsert_chunk(
                chunk_id=chunk.chunk_id,
                document_id=document_id,
                document_name=row["title"],
                text=chunk.text,
                embedding=emb,
                source_system=docs_parser.SOURCE_SYSTEM,
                source_record_id=row["slug"],
            )
            total += 1
    store.close()
    return total


def main() -> None:
    load_project_env()
    n = index_docs()
    print(f"indexed {n} chunks into {vector_store_path()}")


if __name__ == "__main__":
    main()
