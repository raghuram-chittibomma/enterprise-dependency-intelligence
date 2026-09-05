"""Parser for MVP3 architecture docs (`data/sample/docs/*.md`).

Creates `Document` nodes and `DOCUMENTED_BY` edges (Document → entity) with
ADR-0003 provenance. Natural keys: `doc:arch-docs:<slug>`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.ingestion.identity import make_id
from src.ingestion.parsers.base import TYPE_TO_LABEL, ParsedRelationship
from src.ingestion.resolution import EntityResolver
from src.ontology.entities import Document
from src.ontology.relationships import DocumentedBy

SOURCE_SYSTEM = "arch-docs"


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Minimal YAML-ish frontmatter parser (no PyYAML dependency)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    header = text[3:end].strip("\n")
    body = text[end + 4 :].lstrip("\n")

    meta: dict[str, Any] = {"related_entities": []}
    current_rel: dict[str, str] | None = None
    in_related = False
    for raw_line in header.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith("related_entities:"):
            in_related = True
            continue
        if in_related and re.match(r"^\s+-\s+type:\s+", line):
            if current_rel:
                meta["related_entities"].append(current_rel)
            current_rel = {"type": line.split(":", 1)[1].strip()}
            continue
        if in_related and current_rel is not None and re.match(r"^\s+name:\s+", line):
            current_rel["name"] = line.split(":", 1)[1].strip()
            continue
        if ":" in line and not line.startswith(" "):
            if current_rel:
                meta["related_entities"].append(current_rel)
                current_rel = None
            in_related = False
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    if current_rel:
        meta["related_entities"].append(current_rel)
    return meta, body


def read(docs_dir: Path) -> list[dict[str, Any]]:
    if not docs_dir.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(docs_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        slug = str(meta.get("slug") or path.stem)
        title = str(meta.get("title") or slug)
        related = meta.get("related_entities") or []
        rows.append(
            {
                "slug": slug,
                "title": title,
                "path": f"docs/{path.name}",
                "body": body,
                "related_entities": related,
            }
        )
    return rows


def build_nodes(rows: list[dict[str, Any]], resolver: EntityResolver) -> list[Document]:
    nodes: list[Document] = []
    for row in rows:
        node = Document(
            id=make_id("Document", SOURCE_SYSTEM, row["slug"]),
            name=row["title"],
            description=row.get("body", "")[:240],
            path=row["path"],
            doc_type="architecture_note",
            source_system=SOURCE_SYSTEM,
            source_record_id=row["slug"],
        )
        resolver.register("document", row["title"], node.id)
        nodes.append(node)
    return nodes


def build_relationships(
    rows: list[dict[str, Any]], resolver: EntityResolver
) -> list[ParsedRelationship]:
    relationships: list[ParsedRelationship] = []
    for row in rows:
        doc_id = make_id("Document", SOURCE_SYSTEM, row["slug"])
        for related in row.get("related_entities") or []:
            entity_type = related["type"]
            entity_name = related["name"]
            target_id = resolver.resolve(
                entity_type,
                entity_name,
                referenced_by_source=SOURCE_SYSTEM,
                referenced_by_record_id=row["slug"],
            )
            if target_id is None:
                continue
            rel = DocumentedBy(
                source_id=doc_id,
                target_id=target_id,
                source_system=SOURCE_SYSTEM,
                source_record_id=row["slug"],
            )
            DocumentedBy.validate_endpoints("Document", TYPE_TO_LABEL[entity_type])
            relationships.append(
                ParsedRelationship(rel, "DOCUMENTED_BY", "Document", TYPE_TO_LABEL[entity_type])
            )
    return relationships
