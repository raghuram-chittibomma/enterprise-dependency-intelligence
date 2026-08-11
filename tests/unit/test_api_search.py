"""Integration-style tests for the FR1 search HTTP routes, using FastAPI's
`TestClient` against a seeded `FallbackGraphStore` (no live external
service, so this runs fast on every commit like `test_pipeline.py`). The
store is injected via `app.dependency_overrides`, never the real configured
backend.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.deps import get_store
from src.api.main import app
from src.graph.fallback_store import FallbackGraphStore
from src.ontology.entities import API, Application, Database, Team
from src.ontology.relationships import Consumes, OwnedBy, ReadsFrom


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GRAPH_STORE_BACKEND", "fallback")
    monkeypatch.setenv("GRAPH_FALLBACK_SQLITE_PATH", ":memory:")

    seeded = FallbackGraphStore()
    seeded.upsert_node(
        "Application",
        Application(
            id="app:cmdb:1",
            name="Storefront",
            description="Customer-facing e-commerce storefront.",
            criticality="critical",
            source_system="cmdb",
            source_record_id="1",
            technology="React",
            environment="prod",
        ),
    )
    seeded.upsert_node(
        "API",
        API(
            id="api:api-catalog:1",
            name="Customer API v1",
            source_system="api-catalog",
            source_record_id="1",
            version="v1",
            protocol="REST",
        ),
    )
    seeded.upsert_node(
        "Team",
        Team(
            id="team:team-ownership:1",
            name="Commerce Platform Team",
            source_system="team-ownership",
            source_record_id="1",
            business_area="Commerce",
        ),
    )
    seeded.upsert_relationship(
        "OWNED_BY",
        OwnedBy(
            source_id="app:cmdb:1",
            target_id="team:team-ownership:1",
            source_system="team-ownership",
            source_record_id="1",
        ),
        "Application",
        "Team",
    )
    seeded.upsert_node(
        "Database",
        Database(
            id="db:db-metadata:1",
            name="OrdersDB",
            source_system="db-metadata",
            source_record_id="1",
            engine="PostgreSQL",
        ),
    )
    seeded.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="app:cmdb:1",
            target_id="api:api-catalog:1",
            source_system="api-catalog",
            source_record_id="1",
        ),
        "Application",
        "API",
    )
    seeded.upsert_relationship(
        "READS_FROM",
        ReadsFrom(
            source_id="api:api-catalog:1",
            target_id="db:db-metadata:1",
            source_system="db-metadata",
            source_record_id="1",
        ),
        "API",
        "Database",
    )
    app.dependency_overrides[get_store] = lambda: seeded

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    seeded.close()


class TestSearchPage:
    def test_index_page_renders_search_box(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert 'hx-get="/search"' in response.text

    def test_static_css_is_served(self, client: TestClient) -> None:
        response = client.get("/static/css/style.css")
        assert response.status_code == 200


class TestSearchRoute:
    def test_matching_query_returns_result_card(self, client: TestClient) -> None:
        response = client.get("/search", params={"q": "Storefront"})
        assert response.status_code == 200
        assert "Storefront" in response.text
        assert "critical" in response.text

    def test_matching_query_by_type_across_labels(self, client: TestClient) -> None:
        response = client.get("/search", params={"q": "Customer API"})
        assert response.status_code == 200
        assert "Customer API v1" in response.text

    def test_unrelated_query_shows_no_matches_message(self, client: TestClient) -> None:
        response = client.get("/search", params={"q": "xyznonexistent"})
        assert response.status_code == 200
        assert "No matches" in response.text

    def test_empty_query_returns_empty_partial(self, client: TestClient) -> None:
        response = client.get("/search", params={"q": ""})
        assert response.status_code == 200
        assert "search-result-card" not in response.text
        assert "No matches" not in response.text

    def test_result_card_links_to_entity_detail_page(self, client: TestClient) -> None:
        response = client.get("/search", params={"q": "Storefront"})
        assert response.status_code == 200
        assert 'href="/entities/app:cmdb:1"' in response.text


class TestEntityDetailRoute:
    def test_renders_metadata_for_a_known_entity(self, client: TestClient) -> None:
        response = client.get("/entities/app:cmdb:1")
        assert response.status_code == 200
        assert "Storefront" in response.text
        assert "Customer-facing e-commerce storefront." in response.text
        assert "critical" in response.text
        assert "React" in response.text  # type-specific property

    def test_renders_owning_team_as_a_link(self, client: TestClient) -> None:
        response = client.get("/entities/app:cmdb:1")
        assert response.status_code == 200
        assert 'href="/entities/team:team-ownership:1"' in response.text
        assert "Commerce Platform Team" in response.text

    def test_renders_no_owner_message_when_unowned(self, client: TestClient) -> None:
        response = client.get("/entities/api:api-catalog:1")
        assert response.status_code == 200
        assert "No owning team recorded" in response.text

    def test_unknown_entity_id_returns_404(self, client: TestClient) -> None:
        response = client.get("/entities/does-not-exist")
        assert response.status_code == 404
        assert "No entity found" in response.text

    def test_renders_provenance_source_line(self, client: TestClient) -> None:
        response = client.get("/entities/app:cmdb:1")
        assert response.status_code == 200
        assert "cmdb" in response.text


class TestDirectDependenciesOnDetailPage:
    def test_shows_upstream_dependency_with_relationship_type(self, client: TestClient) -> None:
        response = client.get("/entities/app:cmdb:1")
        assert response.status_code == 200
        assert "Depends on (1)" in response.text
        assert 'href="/entities/api:api-catalog:1"' in response.text
        assert "CONSUMES" in response.text

    def test_shows_downstream_dependents(self, client: TestClient) -> None:
        response = client.get("/entities/api:api-catalog:1")
        assert response.status_code == 200
        assert "Depended on by (1)" in response.text
        assert 'href="/entities/app:cmdb:1"' in response.text

    def test_entity_with_no_dependencies_shows_empty_state(self, client: TestClient) -> None:
        response = client.get("/entities/db:db-metadata:1")
        assert response.status_code == 200
        assert "Nothing depends directly on this entity." not in response.text
        assert "No direct upstream dependencies." in response.text

    def test_detail_page_includes_the_dependency_graph_section(
        self, client: TestClient
    ) -> None:
        response = client.get("/entities/app:cmdb:1")
        assert response.status_code == 200
        assert 'data-entity-id="app:cmdb:1"' in response.text
        assert 'id="dependency-graph"' in response.text
        assert "cytoscape" in response.text


class TestDependencyGraphRoute:
    def test_unknown_entity_id_returns_404(self, client: TestClient) -> None:
        response = client.get("/entities/does-not-exist/graph")
        assert response.status_code == 404

    def test_default_upstream_traversal_reaches_the_two_hop_chain(
        self, client: TestClient
    ) -> None:
        response = client.get("/entities/app:cmdb:1/graph")
        assert response.status_code == 200
        body = response.json()
        assert body["root_id"] == "app:cmdb:1"
        assert body["direction"] == "upstream"
        assert {n["id"] for n in body["nodes"]} == {
            "app:cmdb:1",
            "api:api-catalog:1",
            "db:db-metadata:1",
        }
        assert {(e["source_id"], e["target_id"]) for e in body["edges"]} == {
            ("app:cmdb:1", "api:api-catalog:1"),
            ("api:api-catalog:1", "db:db-metadata:1"),
        }

    def test_depth_1_stops_at_the_direct_neighbor(self, client: TestClient) -> None:
        response = client.get("/entities/app:cmdb:1/graph", params={"depth": 1})
        assert response.status_code == 200
        body = response.json()
        assert {n["id"] for n in body["nodes"]} == {"app:cmdb:1", "api:api-catalog:1"}

    def test_downstream_direction_traces_dependents(self, client: TestClient) -> None:
        response = client.get(
            "/entities/db:db-metadata:1/graph", params={"direction": "downstream"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["direction"] == "downstream"
        assert {n["id"] for n in body["nodes"]} == {
            "db:db-metadata:1",
            "api:api-catalog:1",
            "app:cmdb:1",
        }

    def test_invalid_direction_is_rejected(self, client: TestClient) -> None:
        response = client.get(
            "/entities/app:cmdb:1/graph", params={"direction": "sideways"}
        )
        assert response.status_code == 422
