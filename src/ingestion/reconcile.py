"""Source–graph membership reconciliation (`ADR-0009`, FR28).

Dry-run only: report stale nodes/relationships. Hard-delete apply is not
wired (no CLI/env flag) until deliberately re-enabled later.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.graph.store import GraphStore
from src.ingestion.parsers.base import ParsedRelationship
from src.ontology.entities import NodeBase

RelKey = tuple[str, str, str]


@dataclass(frozen=True)
class StaleNode:
    id: str
    label: str
    name: str


@dataclass(frozen=True)
class StaleRelationship:
    source_id: str
    target_id: str
    rel_type: str


@dataclass
class ReconciliationReport:
    would_delete_nodes: list[StaleNode] = field(default_factory=list)
    would_delete_rels: list[StaleRelationship] = field(default_factory=list)


def expected_sets(
    nodes: list[NodeBase],
    relationships: list[ParsedRelationship],
) -> tuple[set[str], set[RelKey]]:
    node_ids = {n.id for n in nodes}
    rel_keys = {
        (p.relationship.source_id, p.relationship.target_id, p.rel_type)
        for p in relationships
    }
    return node_ids, rel_keys


def diff_stale(
    store: GraphStore,
    expected_node_ids: set[str],
    expected_rel_keys: set[RelKey],
) -> tuple[list[StaleNode], list[StaleRelationship]]:
    stale_nodes = [
        StaleNode(
            id=n["id"],
            label=str(n.get("label") or ""),
            name=str(n.get("name") or n["id"]),
        )
        for n in store.get_all_nodes()
        if n.get("id") not in expected_node_ids
    ]
    stale_nodes.sort(key=lambda s: (s.label, s.name))

    stale_rels = [
        StaleRelationship(
            source_id=r["source_id"],
            target_id=r["target_id"],
            rel_type=r["rel_type"],
        )
        for r in store.get_all_relationships()
        if (r["source_id"], r["target_id"], r["rel_type"]) not in expected_rel_keys
    ]
    stale_rels.sort(key=lambda s: (s.rel_type, s.source_id, s.target_id))
    return stale_nodes, stale_rels


def reconcile(
    store: GraphStore,
    nodes: list[NodeBase],
    relationships: list[ParsedRelationship],
) -> ReconciliationReport:
    """Diff graph vs expected parse set; never mutates the graph."""
    expected_node_ids, expected_rel_keys = expected_sets(nodes, relationships)
    stale_nodes, stale_rels = diff_stale(store, expected_node_ids, expected_rel_keys)
    return ReconciliationReport(
        would_delete_nodes=stale_nodes,
        would_delete_rels=stale_rels,
    )
