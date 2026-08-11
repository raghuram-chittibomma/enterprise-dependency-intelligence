"""Parser for Source 5: Integration Catalog (`data/sample/integration_catalog.csv`).
Originates ExternalSystem nodes (derived from the target system columns, on
first sight); contributes INTEGRATES_WITH edges.
"""

from __future__ import annotations

import csv
from pathlib import Path

from src.ingestion.derived import get_or_create
from src.ingestion.parsers.base import TYPE_TO_LABEL, ParsedRelationship
from src.ingestion.resolution import EntityResolver
from src.ontology.entities import ExternalSystem
from src.ontology.relationships import IntegratesWith

SOURCE_SYSTEM = "integration-catalog"


def read(path: Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_nodes(rows: list[dict[str, str]], resolver: EntityResolver) -> list[ExternalSystem]:
    nodes: list[ExternalSystem] = []
    for row in rows:
        name = row["target_system_name"]
        _, node = get_or_create(
            resolver,
            "external_system",
            "ExternalSystem",
            name,
            SOURCE_SYSTEM,
            build=lambda id_, _row=row: ExternalSystem(
                id=id_,
                name=_row["target_system_name"],
                vendor=_row["target_system_vendor"],
                category=_row["target_system_category"],
                source_system=SOURCE_SYSTEM,
                source_record_id=_row["target_system_name"],
            ),
        )
        if node is not None:
            nodes.append(node)
    return nodes


def build_relationships(
    rows: list[dict[str, str]], resolver: EntityResolver
) -> list[ParsedRelationship]:
    relationships: list[ParsedRelationship] = []
    for i, row in enumerate(rows):
        source_id = resolver.resolve(
            row["source_system_type"],
            row["source_system_name"],
            referenced_by_source=SOURCE_SYSTEM,
            referenced_by_record_id=str(i),
        )
        if source_id is None:
            continue
        target_id = resolver.lookup_exact("external_system", row["target_system_name"])
        if target_id is None:
            continue
        rel = IntegratesWith(
            source_id=source_id,
            target_id=target_id,
            source_system=SOURCE_SYSTEM,
            source_record_id=str(i),
            integration_type=row.get("integration_type"),
            protocol=row.get("protocol"),
            frequency=row.get("frequency"),
        )
        relationships.append(
            ParsedRelationship(
                rel, "INTEGRATES_WITH", TYPE_TO_LABEL[row["source_system_type"]], "ExternalSystem"
            )
        )
    return relationships
