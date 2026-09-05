"""Orchestrates the source parsers into a single idempotent ingestion run
(increment-4 / MVP3 docs / ADR-0009 recon). Two global upsert phases -- all
nodes, then all relationships -- then a dry-run membership reconciliation
report (never deletes).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.graph.store import GraphStore
from src.ingestion.parsers import (
    api_catalog,
    architecture_docs,
    cmdb,
    db_metadata,
    integration_catalog,
    team_ownership,
)
from src.ingestion.reconcile import ReconciliationReport, reconcile
from src.ingestion.resolution import EntityResolver, UnresolvedReference

DEFAULT_DATA_DIR = Path("data/sample")
DEFAULT_UNRESOLVED_PATH = Path("data/unresolved/unresolved.json")


@dataclass
class IngestionResult:
    nodes_upserted: int
    relationships_upserted: int
    unresolved: list[UnresolvedReference]
    reconciliation: ReconciliationReport | None = None


def _read_all(data_dir: Path) -> dict[str, list]:
    return {
        "cmdb": cmdb.read(data_dir / "cmdb.csv"),
        "api_catalog": api_catalog.read(data_dir / "api_catalog.json"),
        "db_metadata": db_metadata.read(data_dir / "db_metadata.json"),
        "team_ownership": team_ownership.read(data_dir / "team_ownership.json"),
        "integration_catalog": integration_catalog.read(data_dir / "integration_catalog.csv"),
        "architecture_docs": architecture_docs.read(data_dir / "docs"),
    }


def run_ingestion(
    store: GraphStore,
    data_dir: Path = DEFAULT_DATA_DIR,
    unresolved_path: Path | None = DEFAULT_UNRESOLVED_PATH,
) -> IngestionResult:
    resolver = EntityResolver()
    rows = _read_all(data_dir)

    all_nodes = [
        *cmdb.build_nodes(rows["cmdb"], resolver),
        *api_catalog.build_nodes(rows["api_catalog"], resolver),
        *db_metadata.build_nodes(rows["db_metadata"], resolver),
        *team_ownership.build_nodes(rows["team_ownership"], resolver),
        *integration_catalog.build_nodes(rows["integration_catalog"], resolver),
        *architecture_docs.build_nodes(rows["architecture_docs"], resolver),
    ]
    for node in all_nodes:
        store.upsert_node(type(node).label(), node)

    all_relationships = [
        *cmdb.build_relationships(rows["cmdb"], resolver),
        *api_catalog.build_relationships(rows["api_catalog"], resolver),
        *db_metadata.build_relationships(rows["db_metadata"], resolver),
        *team_ownership.build_relationships(rows["team_ownership"], resolver),
        *integration_catalog.build_relationships(rows["integration_catalog"], resolver),
        *architecture_docs.build_relationships(rows["architecture_docs"], resolver),
    ]
    for parsed in all_relationships:
        store.upsert_relationship(
            parsed.rel_type, parsed.relationship, parsed.source_label, parsed.target_label
        )

    if resolver.unresolved and unresolved_path is not None:
        _write_unresolved_queue(resolver.unresolved, unresolved_path)

    recon = reconcile(store, all_nodes, all_relationships)

    return IngestionResult(
        nodes_upserted=len(all_nodes),
        relationships_upserted=len(all_relationships),
        unresolved=resolver.unresolved,
        reconciliation=recon,
    )


def _write_unresolved_queue(unresolved: list[UnresolvedReference], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(u) for u in unresolved], indent=2), encoding="utf-8")
