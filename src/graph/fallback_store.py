"""Fallback `GraphStore` implementation (ADR-0001): NetworkX for in-memory
traversal + SQLite for persistence, used only when the remote Docker host
running Neo4j is unreachable. Supports the same query *surface*, not full
Cypher parity -- see ADR-0001's Consequences.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import networkx as nx

from src.graph.types import HealthCheckResult
from src.ontology.entities import NodeBase
from src.ontology.registry import NODE_TYPES, RELATIONSHIP_TYPES
from src.ontology.relationships import RelationshipBase

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    properties TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS relationships (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    rel_type TEXT NOT NULL,
    properties TEXT NOT NULL,
    PRIMARY KEY (source_id, target_id, rel_type)
);
"""


class FallbackGraphStore:
    """`sqlite_path=":memory:"` is convenient for tests; a real path persists
    across process restarts, matching Neo4j's durability.
    """

    def __init__(self, sqlite_path: str | Path = ":memory:") -> None:
        if sqlite_path != ":memory:":
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(sqlite_path))
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self._load_into_memory()

    def _load_into_memory(self) -> None:
        node_rows = self._conn.execute("SELECT id, label, properties FROM nodes")
        for node_id, label, properties in node_rows:
            self.graph.add_node(node_id, label=label, **json.loads(properties))
        rel_rows = self._conn.execute(
            "SELECT source_id, target_id, rel_type, properties FROM relationships"
        )
        for source_id, target_id, rel_type, properties in rel_rows:
            self.graph.add_edge(
                source_id, target_id, key=rel_type, rel_type=rel_type, **json.loads(properties)
            )

    def health_check(self) -> HealthCheckResult:
        try:
            node_count = self.count_nodes()
            return HealthCheckResult(
                ok=True, backend="fallback", detail=f"reachable, {node_count} node(s) in graph"
            )
        except Exception as exc:  # noqa: BLE001 - health check must never raise
            return HealthCheckResult(ok=False, backend="fallback", detail=str(exc))

    def bootstrap_schema(self) -> None:
        pass  # tables already created in __init__; uniqueness enforced by PRIMARY KEY

    def upsert_node(self, label: str, node: NodeBase) -> None:
        if label not in NODE_TYPES:
            raise ValueError(f"Unknown node label {label!r}; expected one of {sorted(NODE_TYPES)}")
        props = node.model_dump(mode="json")
        self._conn.execute(
            "INSERT INTO nodes (id, label, properties) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "label = excluded.label, properties = excluded.properties",
            (node.id, label, json.dumps(props)),
        )
        self._conn.commit()
        self.graph.add_node(node.id, label=label, **props)

    def upsert_relationship(
        self, rel_type: str, rel: RelationshipBase, source_label: str, target_label: str
    ) -> None:
        if rel_type not in RELATIONSHIP_TYPES:
            raise ValueError(
                f"Unknown relationship type {rel_type!r}; "
                f"expected one of {sorted(RELATIONSHIP_TYPES)}"
            )
        props = rel.model_dump(mode="json", exclude={"source_id", "target_id"})
        self._conn.execute(
            "INSERT INTO relationships (source_id, target_id, rel_type, properties) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(source_id, target_id, rel_type) "
            "DO UPDATE SET properties = excluded.properties",
            (rel.source_id, rel.target_id, rel_type, json.dumps(props)),
        )
        self._conn.commit()
        self.graph.add_edge(rel.source_id, rel.target_id, key=rel_type, rel_type=rel_type, **props)

    def count_nodes(self, label: str | None = None) -> int:
        if label:
            return self._conn.execute(
                "SELECT COUNT(*) FROM nodes WHERE label = ?", (label,)
            ).fetchone()[0]
        return self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]

    def count_relationships(self, rel_type: str | None = None) -> int:
        if rel_type:
            return self._conn.execute(
                "SELECT COUNT(*) FROM relationships WHERE rel_type = ?", (rel_type,)
            ).fetchone()[0]
        return self._conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]

    def close(self) -> None:
        self._conn.close()
