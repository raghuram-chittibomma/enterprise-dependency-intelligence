"""End-to-end ingestion against the real Neo4j instance (increment-4). Skips
if unreachable. Deliberately wipes the graph before ingesting -- this
project's dev Neo4j is single-tenant, single-dataset, so "the golden dataset
freshly ingested" is the intended steady state for local dev, not a
side effect to avoid.
"""

from __future__ import annotations

import pytest

from src.graph.config import get_graph_store
from src.graph.neo4j_store import Neo4jGraphStore
from src.ingestion.pipeline import run_ingestion
from tests.unit.test_pipeline import EXPECTED_NODE_COUNT, EXPECTED_RELATIONSHIP_COUNT

pytestmark = pytest.mark.integration


@pytest.fixture
def store():
    import os

    os.environ.setdefault("GRAPH_STORE_BACKEND", "neo4j")
    candidate = get_graph_store()
    assert isinstance(candidate, Neo4jGraphStore)
    result = candidate.health_check()
    if not result.ok:
        candidate.close()
        pytest.skip(f"Neo4j not reachable: {result.detail}")
    candidate.bootstrap_schema()
    with candidate._driver.session() as session:  # noqa: SLF001 - test-only reset
        session.run("MATCH (n) DETACH DELETE n")
    yield candidate
    candidate.close()


class TestIngestionAgainstNeo4j:
    def test_ingests_expected_counts_and_is_idempotent(
        self, store: Neo4jGraphStore, tmp_path
    ) -> None:
        first = run_ingestion(store, unresolved_path=tmp_path / "unresolved.json")
        assert first.nodes_upserted == EXPECTED_NODE_COUNT
        assert first.relationships_upserted == EXPECTED_RELATIONSHIP_COUNT
        assert store.count_nodes() == EXPECTED_NODE_COUNT
        assert store.count_relationships() == EXPECTED_RELATIONSHIP_COUNT
        assert first.unresolved == []

        second = run_ingestion(store, unresolved_path=tmp_path / "unresolved2.json")
        assert store.count_nodes() == EXPECTED_NODE_COUNT
        assert store.count_relationships() == EXPECTED_RELATIONSHIP_COUNT
        assert second.nodes_upserted == first.nodes_upserted
        assert second.relationships_upserted == first.relationships_upserted

    def test_a_sample_relationship_carries_provenance(self, store: Neo4jGraphStore) -> None:
        run_ingestion(store)
        with store._driver.session() as session:  # noqa: SLF001 - test-only assertion
            record = session.run(
                "MATCH (a:Application {name: 'Storefront'})"
                "-[r:CONSUMES]->(api:API {name: 'Customer API v1'}) "
                "RETURN r.source_system AS source_system, r.evidence_type AS evidence_type"
            ).single()
        assert record is not None
        assert record["source_system"] == "api-catalog"
        assert record["evidence_type"] == "documented"
