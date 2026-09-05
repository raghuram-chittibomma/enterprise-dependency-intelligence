"""Markdown chunking for architecture docs (MVP3)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    text: str
    ordinal: int


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end < 0:
        return text
    return text[end + 4 :].lstrip("\n")


def chunk_markdown(document_id: str, markdown: str, *, max_chars: int = 800) -> list[TextChunk]:
    """Split markdown into roughly paragraph-sized chunks with stable ids."""
    body = _strip_frontmatter(markdown).strip()
    if not body:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    chunks: list[TextChunk] = []
    buffer = ""
    ordinal = 0

    def flush() -> None:
        nonlocal buffer, ordinal
        text = buffer.strip()
        if not text:
            buffer = ""
            return
        digest = hashlib.sha1(f"{document_id}:{ordinal}:{text}".encode()).hexdigest()[:12]
        chunks.append(TextChunk(chunk_id=f"{document_id}#c{ordinal}-{digest}", text=text, ordinal=ordinal))
        ordinal += 1
        buffer = ""

    for para in paragraphs:
        candidate = f"{buffer}\n\n{para}".strip() if buffer else para
        if len(candidate) <= max_chars:
            buffer = candidate
            continue
        flush()
        if len(para) <= max_chars:
            buffer = para
            continue
        # Hard-split long paragraphs.
        for i in range(0, len(para), max_chars):
            buffer = para[i : i + max_chars]
            flush()

    flush()
    return chunks
