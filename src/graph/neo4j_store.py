"""Primary `GraphStore` implementation: Neo4j Community Edition (ADR-0001),
reached over Bolt via the official driver.
"""

from __future__ import annotations

from neo4j import Driver, GraphDatabase

from src.graph.types import HealthCheckResult
from src.ontology.entities import NodeBase
from src.ontology.registry import NODE_TYPES, RELATIONSHIP_TYPES
from src.ontology.relationships import RelationshipBase


class Neo4jGraphStore:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def health_check(self) -> HealthCheckResult:
        try:
            self._driver.verify_connectivity()
            with self._driver.session() as session:
                node_count = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            return HealthCheckResult(
                ok=True, backend="neo4j", detail=f"reachable, {node_count} node(s) in graph"
            )
        except Exception as exc:  # noqa: BLE001 - health check must never raise
            return HealthCheckResult(ok=False, backend="neo4j", detail=str(exc))

    def bootstrap_schema(self) -> None:
        with self._driver.session() as session:
            for label in NODE_TYPES:
                session.run(
                    f"CREATE CONSTRAINT unique_{label.lower()}_id IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                )

    def upsert_node(self, label: str, node: NodeBase) -> None:
        if label not in NODE_TYPES:
            raise ValueError(f"Unknown node label {label!r}; expected one of {sorted(NODE_TYPES)}")
        props = node.model_dump(mode="json")
        with self._driver.session() as session:
            session.run(f"MERGE (n:{label} {{id: $id}}) SET n = $props", id=node.id, props=props)

    def upsert_relationship(
        self, rel_type: str, rel: RelationshipBase, source_label: str, target_label: str
    ) -> None:
        if rel_type not in RELATIONSHIP_TYPES:
            raise ValueError(
                f"Unknown relationship type {rel_type!r}; "
                f"expected one of {sorted(RELATIONSHIP_TYPES)}"
            )
        props = rel.model_dump(mode="json", exclude={"source_id", "target_id"})
        with self._driver.session() as session:
            session.run(
                f"MATCH (s:{source_label} {{id: $source_id}}), "
                f"(t:{target_label} {{id: $target_id}}) "
                f"MERGE (s)-[r:{rel_type}]->(t) SET r = $props",
                source_id=rel.source_id,
                target_id=rel.target_id,
                props=props,
            )

    def delete_relationship(self, source_id: str, target_id: str, rel_type: str) -> bool:
        if rel_type not in RELATIONSHIP_TYPES:
            raise ValueError(
                f"Unknown relationship type {rel_type!r}; "
                f"expected one of {sorted(RELATIONSHIP_TYPES)}"
            )
        with self._driver.session() as session:
            result = session.run(
                f"MATCH (s {{id: $source_id}})-[r:{rel_type}]->(t {{id: $target_id}}) "
                "DELETE r RETURN count(r) AS c",
                source_id=source_id,
                target_id=target_id,
            )
            record = result.single()
            return bool(record and record["c"] > 0)

    def delete_node(self, entity_id: str) -> bool:
        with self._driver.session() as session:
            result = session.run(
                "MATCH (n {id: $id}) DETACH DELETE n RETURN count(n) AS c",
                id=entity_id,
            )
            record = result.single()
            return bool(record and record["c"] > 0)

    def count_nodes(self, label: str | None = None) -> int:
        query = f"MATCH (n{':' + label if label else ''}) RETURN count(n) AS c"
        with self._driver.session() as session:
            return session.run(query).single()["c"]

    def count_relationships(self, rel_type: str | None = None) -> int:
        query = f"MATCH ()-[r{':' + rel_type if rel_type else ''}]->() RETURN count(r) AS c"
        with self._driver.session() as session:
            return session.run(query).single()["c"]

    def get_all_nodes(self) -> list[dict]:
        with self._driver.session() as session:
            result = session.run("MATCH (n) RETURN labels(n) AS labels, properties(n) AS props")
            return [{"label": record["labels"][0], **record["props"]} for record in result]

    def get_all_relationships(self) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(
                "MATCH (s)-[r]->(t) RETURN type(r) AS rel_type, s.id AS source_id, "
                "t.id AS target_id, properties(r) AS props"
            )
            return [
                {
                    "rel_type": record["rel_type"],
                    "source_id": record["source_id"],
                    "target_id": record["target_id"],
                    **record["props"],
                }
                for record in result
            ]

    def close(self) -> None:
        self._driver.close()
