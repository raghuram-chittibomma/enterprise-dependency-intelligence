"""Orchestrates the 5 parsers into a single idempotent ingestion run
(increment-4). Two global phases -- all nodes, then all relationships --
which is what actually guarantees no forward-reference ever fails to
resolve, regardless of row order within (or even between) source files: by
the time phase 2 starts, every node from every source already exists.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.graph.store import GraphStore
from src.ingestion.parsers import (
    api_catalog,
    cmdb,
    db_metadata,
    integration_catalog,
    team_ownership,
)
from src.ingestion.resolution import EntityResolver, UnresolvedReference

DEFAULT_DATA_DIR = Path("data/sample")
DEFAULT_UNRESOLVED_PATH = Path("data/unresolved/unresolved.json")


@dataclass
class IngestionResult:
    nodes_upserted: int
    relationships_upserted: int
    unresolved: list[UnresolvedReference]


def _read_all(data_dir: Path) -> dict[str, list]:
    return {
        "cmdb": cmdb.read(data_dir / "cmdb.csv"),
        "api_catalog": api_catalog.read(data_dir / "api_catalog.json"),
        "db_metadata": db_metadata.read(data_dir / "db_metadata.json"),
        "team_ownership": team_ownership.read(data_dir / "team_ownership.json"),
        "integration_catalog": integration_catalog.read(data_dir / "integration_catalog.csv"),
    }


def run_ingestion(
    store: GraphStore,
    data_dir: Path = DEFAULT_DATA_DIR,
    unresolved_path: Path | None = DEFAULT_UNRESOLVED_PATH,
) -> IngestionResult:
    resolver = EntityResolver()
    rows = _read_all(data_dir)

    # Phase 1: nodes.
    all_nodes = [
        *cmdb.build_nodes(rows["cmdb"], resolver),
        *api_catalog.build_nodes(rows["api_catalog"], resolver),
        *db_metadata.build_nodes(rows["db_metadata"], resolver),
        *team_ownership.build_nodes(rows["team_ownership"], resolver),
        *integration_catalog.build_nodes(rows["integration_catalog"], resolver),
    ]
    for node in all_nodes:
        store.upsert_node(type(node).label(), node)

    # Phase 2: relationships -- every endpoint from phase 1 is already
    # registered with the resolver, so no reference can be a forward
    # reference here.
    all_relationships = [
        *cmdb.build_relationships(rows["cmdb"], resolver),
        *api_catalog.build_relationships(rows["api_catalog"], resolver),
        *db_metadata.build_relationships(rows["db_metadata"], resolver),
        *team_ownership.build_relationships(rows["team_ownership"], resolver),
        *integration_catalog.build_relationships(rows["integration_catalog"], resolver),
    ]
    for parsed in all_relationships:
        store.upsert_relationship(
            parsed.rel_type, parsed.relationship, parsed.source_label, parsed.target_label
        )

    if resolver.unresolved and unresolved_path is not None:
        _write_unresolved_queue(resolver.unresolved, unresolved_path)

    return IngestionResult(
        nodes_upserted=len(all_nodes),
        relationships_upserted=len(all_relationships),
        unresolved=resolver.unresolved,
    )


def _write_unresolved_queue(unresolved: list[UnresolvedReference], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(u) for u in unresolved], indent=2), encoding="utf-8")
