"""Integration tests against a real Neo4j instance (increment-3). Skips the
whole module if the configured Neo4j isn't reachable -- these are meant to
run against the Docker container from `docker-compose.yml` (see
`docs/03_operations/RUNBOOK.md`), not to block local dev when it's down.
"""

from __future__ import annotations

import pytest

from src.graph.config import get_graph_store
from src.graph.neo4j_store import Neo4jGraphStore
from src.ontology.entities import Application, Team
from src.ontology.relationships import OwnedBy

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
    # Isolate this test run's writes so it doesn't collide with real data.
    yield candidate
    with candidate._driver.session() as session:  # noqa: SLF001 - test-only cleanup
        session.run(
            "MATCH (n) WHERE n.source_system STARTS WITH 'integration-test' DETACH DELETE n"
        )
    candidate.close()


class TestNeo4jGraphStore:
    def test_health_check_reports_ok(self, store: Neo4jGraphStore) -> None:
        result = store.health_check()
        assert result.ok
        assert result.backend == "neo4j"

    def test_bootstrap_schema_is_idempotent(self, store: Neo4jGraphStore) -> None:
        store.bootstrap_schema()
        store.bootstrap_schema()  # must not raise on the second call

    def test_upsert_node_and_relationship_round_trip(self, store: Neo4jGraphStore) -> None:
        app = Application(
            id="app:integration-test:1",
            name="Integration Test App",
            source_system="integration-test",
            source_record_id="1",
            technology="Test",
            environment="test",
        )
        team = Team(
            id="team:integration-test:1",
            name="Integration Test Team",
            source_system="integration-test",
            source_record_id="1",
            business_area="Test",
        )
        store.upsert_node("Application", app)
        store.upsert_node("Team", team)
        rel = OwnedBy(
            source_id=app.id,
            target_id=team.id,
            source_system="integration-test",
            source_record_id="1",
        )
        store.upsert_relationship("OWNED_BY", rel, "Application", "Team")
        # Idempotency: re-running must not create a duplicate.
        store.upsert_node("Application", app)
        store.upsert_relationship("OWNED_BY", rel, "Application", "Team")

        with store._driver.session() as session:  # noqa: SLF001 - test-only assertion
            record = session.run(
                "MATCH (a:Application {id: $id})-[r:OWNED_BY]->(t:Team) RETURN a, r, t",
                id=app.id,
            ).single()
        assert record is not None
        assert record["a"]["name"] == "Integration Test App"
