"""Parser for Source 4: Team Ownership (`data/sample/team_ownership.json`).
Originates Team nodes; the sole source of OWNED_BY edges (ADR-0003 --
ownership is never inferred or duplicated across sources).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.ingestion.identity import make_id
from src.ingestion.parsers.base import TYPE_TO_LABEL, ParsedRelationship
from src.ingestion.resolution import EntityResolver
from src.ontology.entities import Team
from src.ontology.relationships import OwnedBy

SOURCE_SYSTEM = "team-ownership"


def read(path: Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_nodes(rows: list[dict[str, Any]], resolver: EntityResolver) -> list[Team]:
    nodes: list[Team] = []
    for row in rows:
        node = Team(
            id=make_id("Team", SOURCE_SYSTEM, row["team_id"]),
            name=row["name"],
            description=row.get("description", ""),
            business_area=row["business_area"],
            source_system=SOURCE_SYSTEM,
            source_record_id=row["team_id"],
        )
        resolver.register("team", row["name"], node.id)
        nodes.append(node)
    return nodes


def build_relationships(
    rows: list[dict[str, Any]], resolver: EntityResolver
) -> list[ParsedRelationship]:
    relationships: list[ParsedRelationship] = []
    for row in rows:
        team_id = make_id("Team", SOURCE_SYSTEM, row["team_id"])

        for system in row.get("systems_owned", []):
            system_id = resolver.resolve(
                system["type"],
                system["name"],
                referenced_by_source=SOURCE_SYSTEM,
                referenced_by_record_id=row["team_id"],
            )
            if system_id is None:
                continue
            rel = OwnedBy(
                source_id=system_id,
                target_id=team_id,
                source_system=SOURCE_SYSTEM,
                source_record_id=row["team_id"],
            )
            relationships.append(
                ParsedRelationship(rel, "OWNED_BY", TYPE_TO_LABEL[system["type"]], "Team")
            )

    return relationships
