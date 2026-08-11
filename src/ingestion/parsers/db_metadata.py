"""Parser for Source 3: Database Metadata (`data/sample/db_metadata.json`).
Originates Database nodes; contributes READS_FROM and WRITES_TO edges from
each listed reader/writer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.ingestion.identity import make_id
from src.ingestion.parsers.base import TYPE_TO_LABEL, ParsedRelationship
from src.ingestion.resolution import EntityResolver
from src.ontology.entities import Database
from src.ontology.relationships import ReadsFrom, WritesTo
from src.ontology.types import Criticality

SOURCE_SYSTEM = "db-metadata"


def read(path: Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_nodes(rows: list[dict[str, Any]], resolver: EntityResolver) -> list[Database]:
    nodes: list[Database] = []
    for row in rows:
        node = Database(
            id=make_id("Database", SOURCE_SYSTEM, row["record_id"]),
            name=row["name"],
            engine=row["engine"],
            key_tables=row.get("key_tables", []),
            criticality=Criticality(row["criticality"]) if row.get("criticality") else None,
            lifecycle_status=row["lifecycle_status"],
            source_system=SOURCE_SYSTEM,
            source_record_id=row["record_id"],
        )
        resolver.register("database", row["name"], node.id)
        nodes.append(node)
    return nodes


def build_relationships(
    rows: list[dict[str, Any]], resolver: EntityResolver
) -> list[ParsedRelationship]:
    relationships: list[ParsedRelationship] = []
    for row in rows:
        db_id = make_id("Database", SOURCE_SYSTEM, row["record_id"])

        for reader in row.get("readers", []):
            reader_id = resolver.resolve(
                reader["type"],
                reader["name"],
                referenced_by_source=SOURCE_SYSTEM,
                referenced_by_record_id=row["record_id"],
            )
            if reader_id is None:
                continue
            rel = ReadsFrom(
                source_id=reader_id,
                target_id=db_id,
                source_system=SOURCE_SYSTEM,
                source_record_id=row["record_id"],
            )
            relationships.append(
                ParsedRelationship(rel, "READS_FROM", TYPE_TO_LABEL[reader["type"]], "Database")
            )

        for writer in row.get("writers", []):
            writer_id = resolver.resolve(
                writer["type"],
                writer["name"],
                referenced_by_source=SOURCE_SYSTEM,
                referenced_by_record_id=row["record_id"],
            )
            if writer_id is None:
                continue
            rel = WritesTo(
                source_id=writer_id,
                target_id=db_id,
                source_system=SOURCE_SYSTEM,
                source_record_id=row["record_id"],
            )
            relationships.append(
                ParsedRelationship(rel, "WRITES_TO", TYPE_TO_LABEL[writer["type"]], "Database")
            )

    return relationships
