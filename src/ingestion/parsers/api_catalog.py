"""Parser for Source 2: API Catalog (`data/sample/api_catalog.json`).
Originates API nodes; contributes CONSUMES (consumer -> API, and API ->
backend service facade) and SUPPORTS (API -> BusinessCapability) edges.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.ingestion.derived import get_or_create
from src.ingestion.identity import make_id
from src.ingestion.parsers.base import ParsedRelationship
from src.ingestion.resolution import EntityResolver
from src.ontology.entities import API, BusinessCapability
from src.ontology.relationships import Consumes, Supports
from src.ontology.types import Criticality

SOURCE_SYSTEM = "api-catalog"


def read(path: Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_nodes(rows: list[dict[str, Any]], resolver: EntityResolver) -> list[Any]:
    nodes: list[Any] = []
    for row in rows:
        node = API(
            id=make_id("API", SOURCE_SYSTEM, row["record_id"]),
            name=row["name"],
            version=row["version"],
            protocol=row["protocol"],
            criticality=Criticality(row["criticality"]) if row.get("criticality") else None,
            lifecycle_status=row["lifecycle_status"],
            implementing_application=row.get("implementing_application"),
            source_system=SOURCE_SYSTEM,
            source_record_id=row["record_id"],
        )
        resolver.register("api", row["name"], node.id)
        nodes.append(node)

        capability_name = row.get("business_capability")
        if capability_name:
            from src.ingestion.capability_taxonomy import area_for

            _, capability_node = get_or_create(
                resolver,
                "business_capability",
                "BusinessCapability",
                capability_name,
                SOURCE_SYSTEM,
                build=lambda id_, _name=capability_name: BusinessCapability(
                    id=id_,
                    name=_name,
                    source_system=SOURCE_SYSTEM,
                    source_record_id=_name,
                    capability_area=area_for(_name),
                ),
            )
            if capability_node is not None:
                nodes.append(capability_node)

    return nodes


def build_relationships(
    rows: list[dict[str, Any]], resolver: EntityResolver
) -> list[ParsedRelationship]:
    relationships: list[ParsedRelationship] = []
    for row in rows:
        api_id = make_id("API", SOURCE_SYSTEM, row["record_id"])

        for consumer in row.get("consuming_applications", []):
            consumer_id = resolver.resolve(
                consumer["type"],
                consumer["name"],
                referenced_by_source=SOURCE_SYSTEM,
                referenced_by_record_id=row["record_id"],
            )
            if consumer_id is None:
                continue
            consumer_label = {"application": "Application", "service": "Service"}[consumer["type"]]
            rel = Consumes(
                source_id=consumer_id,
                target_id=api_id,
                source_system=SOURCE_SYSTEM,
                source_record_id=row["record_id"],
            )
            relationships.append(ParsedRelationship(rel, "CONSUMES", consumer_label, "API"))

        backend_service = row.get("backend_service")
        if backend_service:
            backend_id = resolver.resolve(
                "service",
                backend_service,
                referenced_by_source=SOURCE_SYSTEM,
                referenced_by_record_id=row["record_id"],
            )
            if backend_id is not None:
                rel = Consumes(
                    source_id=api_id,
                    target_id=backend_id,
                    source_system=SOURCE_SYSTEM,
                    source_record_id=row["record_id"],
                )
                relationships.append(ParsedRelationship(rel, "CONSUMES", "API", "Service"))

        capability_name = row.get("business_capability")
        if capability_name:
            capability_id = resolver.lookup_exact("business_capability", capability_name)
            if capability_id is not None:
                rel = Supports(
                    source_id=api_id,
                    target_id=capability_id,
                    source_system=SOURCE_SYSTEM,
                    source_record_id=row["record_id"],
                )
                relationships.append(
                    ParsedRelationship(rel, "SUPPORTS", "API", "BusinessCapability")
                )

    return relationships
