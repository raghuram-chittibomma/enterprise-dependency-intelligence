"""Parser for Source 1: CMDB / Technology Inventory (`data/sample/cmdb.csv`).
Originates Application, Service, DataPipeline, and Report nodes, and (via
`business_capability`) BusinessCapability nodes on first sight.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.ingestion.derived import get_or_create
from src.ingestion.identity import make_id
from src.ingestion.parsers.base import ParsedRelationship
from src.ingestion.resolution import EntityResolver
from src.ontology.entities import Application, BusinessCapability, DataPipeline, Report, Service
from src.ontology.relationships import ReplacedBy, Supports
from src.ontology.types import Criticality

SOURCE_SYSTEM = "cmdb"

_TYPE_TO_CLASS = {
    "application": Application,
    "service": Service,
    "data_pipeline": DataPipeline,
    "report": Report,
}
_TYPE_TO_LABEL = {
    "application": "Application",
    "service": "Service",
    "data_pipeline": "DataPipeline",
    "report": "Report",
}


def read(path: Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _common_kwargs(row: dict[str, str], label: str) -> dict[str, Any]:
    return {
        "id": make_id(label, SOURCE_SYSTEM, row["record_id"]),
        "name": row["name"],
        "description": row.get("description", ""),
        "criticality": Criticality(row["criticality"]) if row.get("criticality") else None,
        "lifecycle_status": row["lifecycle_status"],
        "source_system": SOURCE_SYSTEM,
        "source_record_id": row["record_id"],
    }


def build_nodes(rows: list[dict[str, str]], resolver: EntityResolver) -> list[Any]:
    nodes: list[Any] = []
    for row in rows:
        type_ = row["type"]
        label = _TYPE_TO_LABEL[type_]
        kwargs = _common_kwargs(row, label)

        if type_ in ("application", "service"):
            kwargs["technology"] = row["technology"]
            kwargs["environment"] = row["environment"]
        elif type_ == "data_pipeline":
            kwargs["pipeline_type"] = row["pipeline_type"]
            kwargs["schedule"] = row.get("schedule") or None
        elif type_ == "report":
            kwargs["audience"] = row["audience"]
            kwargs["refresh_frequency"] = row["refresh_frequency"]

        node = _TYPE_TO_CLASS[type_](**kwargs)
        resolver.register(type_, row["name"], node.id)
        nodes.append(node)

        capability_name = row.get("business_capability")
        if capability_name:
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
                    capability_area=_area_for(_name),
                ),
            )
            if capability_node is not None:
                nodes.append(capability_node)

    return nodes


def _area_for(capability_name: str) -> str:
    from src.ingestion.capability_taxonomy import area_for

    return area_for(capability_name)


def build_relationships(
    rows: list[dict[str, str]], resolver: EntityResolver
) -> list[ParsedRelationship]:
    relationships: list[ParsedRelationship] = []
    for row in rows:
        type_ = row["type"]
        label = _TYPE_TO_LABEL[type_]
        source_id = make_id(label, SOURCE_SYSTEM, row["record_id"])

        capability_name = row.get("business_capability")
        if capability_name and type_ in ("application", "service"):
            capability_id = resolver.lookup_exact("business_capability", capability_name)
            if capability_id is not None:
                rel = Supports(
                    source_id=source_id,
                    target_id=capability_id,
                    source_system=SOURCE_SYSTEM,
                    source_record_id=row["record_id"],
                )
                relationships.append(
                    ParsedRelationship(rel, "SUPPORTS", label, "BusinessCapability")
                )

        successor_name = row.get("replaced_by")
        if successor_name:
            # REPLACED_BY's target can be an Application or an API -- CMDB
            # rows don't say which, so try both before giving up.
            resolved = resolver.resolve_any(
                ("application", "api"),
                successor_name,
                referenced_by_source=SOURCE_SYSTEM,
                referenced_by_record_id=row["record_id"],
            )
            if resolved is not None:
                successor_type, successor_id = resolved
                rel = ReplacedBy(
                    source_id=source_id,
                    target_id=successor_id,
                    source_system=SOURCE_SYSTEM,
                    source_record_id=row["record_id"],
                )
                successor_label = {"application": "Application", "api": "API"}[successor_type]
                relationships.append(
                    ParsedRelationship(rel, "REPLACED_BY", label, successor_label)
                )

    return relationships
