"""Local SQLite vector store for document chunks (`ADR-0006`)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from src.retrieval.embeddings import cosine_similarity, pack_embedding, unpack_embedding

DEFAULT_VECTOR_PATH = Path("data/vectors/chunks.sqlite3")


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    text: str
    source_system: str
    source_record_id: str
    score: float


class SQLiteVectorStore:
    def __init__(self, path: Path = DEFAULT_VECTOR_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                document_name TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                source_system TEXT NOT NULL,
                source_record_id TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM chunks")
        self._conn.commit()

    def upsert_chunk(
        self,
        *,
        chunk_id: str,
        document_id: str,
        document_name: str,
        text: str,
        embedding: list[float],
        source_system: str,
        source_record_id: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO chunks (
                chunk_id, document_id, document_name, text, embedding,
                source_system, source_record_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                document_id=excluded.document_id,
                document_name=excluded.document_name,
                text=excluded.text,
                embedding=excluded.embedding,
                source_system=excluded.source_system,
                source_record_id=excluded.source_record_id
            """,
            (
                chunk_id,
                document_id,
                document_name,
                text,
                pack_embedding(embedding),
                source_system,
                source_record_id,
            ),
        )
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()
        return int(row["n"]) if row else 0

    def search(self, query_embedding: list[float], *, top_k: int = 5) -> list[RetrievedChunk]:
        rows = self._conn.execute("SELECT * FROM chunks").fetchall()
        scored: list[RetrievedChunk] = []
        for row in rows:
            emb = unpack_embedding(row["embedding"])
            score = cosine_similarity(query_embedding, emb)
            scored.append(
                RetrievedChunk(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    document_name=row["document_name"],
                    text=row["text"],
                    source_system=row["source_system"],
                    source_record_id=row["source_record_id"],
                    score=score,
                )
            )
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]

    def close(self) -> None:
        self._conn.close()
