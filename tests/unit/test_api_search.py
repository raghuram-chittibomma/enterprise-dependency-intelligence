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
from src.ontology.entities import API, Application, BusinessCapability, Database, Team
from src.ontology.relationships import Consumes, OwnedBy, ReadsFrom, Supports


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
    seeded.upsert_node(
        "BusinessCapability",
        BusinessCapability(
            id="cap:cap-catalog:1",
            name="Order Management",
            source_system="cap-catalog",
            source_record_id="1",
            capability_area="Commerce",
        ),
    )
    seeded.upsert_relationship(
        "SUPPORTS",
        Supports(
            source_id="app:cmdb:1",
            target_id="cap:cap-catalog:1",
            source_system="cap-catalog",
            source_record_id="1",
        ),
        "Application",
        "BusinessCapability",
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

    def test_index_page_renders_ask_form(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert 'hx-post="/ask"' in response.text
        assert 'id="ask-answer"' in response.text
        assert 'id="ask-loading"' in response.text
        assert "hx-indicator" in response.text
        assert "hx-disabled-elt" in response.text

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


class TestPathsRoutes:
    def test_search_excludes_the_entity_itself(self, client: TestClient) -> None:
        response = client.get(
            "/entities/app:cmdb:1/paths/search", params={"q": "Storefront"}
        )
        assert response.status_code == 200
        assert "app:cmdb:1" not in response.text

    def test_search_finds_a_candidate_target(self, client: TestClient) -> None:
        response = client.get("/entities/app:cmdb:1/paths/search", params={"q": "OrdersDB"})
        assert response.status_code == 200
        assert "OrdersDB" in response.text
        assert 'hx-get="/entities/app:cmdb:1/paths/result?target=db:db-metadata:1"' in (
            response.text
        )

    def test_result_renders_the_shortest_path_chain(self, client: TestClient) -> None:
        response = client.get(
            "/entities/app:cmdb:1/paths/result", params={"target": "db:db-metadata:1"}
        )
        assert response.status_code == 200
        assert "Shortest path to OrdersDB" in response.text
        assert "2 hops" in response.text
        assert "Customer API v1" in response.text
        assert "CONSUMES" in response.text
        assert "READS_FROM" in response.text

    def test_result_reports_no_path_when_none_exists(self, client: TestClient) -> None:
        # The owning team is only reachable via OWNED_BY, which isn't a
        # dependency edge, so no dependency path connects them.
        response = client.get(
            "/entities/app:cmdb:1/paths/result",
            params={"target": "team:team-ownership:1"},
        )
        assert response.status_code == 200
        assert "No dependency path found" in response.text

    def test_result_handles_an_unknown_target_gracefully(self, client: TestClient) -> None:
        response = client.get(
            "/entities/app:cmdb:1/paths/result", params={"target": "does-not-exist"}
        )
        assert response.status_code == 200
        assert "Could not compute a path" in response.text

    def test_detail_page_includes_the_path_explorer_section(self, client: TestClient) -> None:
        response = client.get("/entities/app:cmdb:1")
        assert response.status_code == 200
        assert 'hx-get="/entities/app:cmdb:1/paths/search"' in response.text
        assert 'id="path-result"' in response.text


class TestOwnershipRollupRoute:
    def test_unknown_entity_id_returns_404(self, client: TestClient) -> None:
        response = client.get("/entities/does-not-exist/ownership")
        assert response.status_code == 404

    def test_upstream_rollup_includes_the_roots_own_team(self, client: TestClient) -> None:
        response = client.get(
            "/entities/app:cmdb:1/ownership", params={"direction": "upstream", "depth": 2}
        )
        assert response.status_code == 200
        assert "Commerce Platform Team" in response.text
        assert "Storefront" in response.text

    def test_upstream_rollup_groups_unowned_entities_together(self, client: TestClient) -> None:
        response = client.get(
            "/entities/app:cmdb:1/ownership", params={"direction": "upstream", "depth": 2}
        )
        assert response.status_code == 200
        assert "No owning team recorded" in response.text
        assert "Customer API v1" in response.text
        assert "OrdersDB" in response.text

    def test_downstream_rollup_reaches_the_owning_dependent(self, client: TestClient) -> None:
        response = client.get(
            "/entities/api:api-catalog:1/ownership",
            params={"direction": "downstream", "depth": 1},
        )
        assert response.status_code == 200
        assert "Commerce Platform Team" in response.text
        assert "Storefront" in response.text

    def test_detail_page_includes_the_stakeholder_rollup_section(
        self, client: TestClient
    ) -> None:
        response = client.get("/entities/app:cmdb:1")
        assert response.status_code == 200
        assert 'hx-get="/entities/app:cmdb:1/ownership"' in response.text
        assert 'id="ownership-rollup"' in response.text


class TestBusinessCapabilitiesOnDetailPage:
    def test_shows_capabilities_directly_supported_by_the_entity(
        self, client: TestClient
    ) -> None:
        response = client.get("/entities/app:cmdb:1")
        assert response.status_code == 200
        assert "Order Management" in response.text

    def test_shows_empty_state_when_entity_supports_nothing_directly(
        self, client: TestClient
    ) -> None:
        response = client.get("/entities/db:db-metadata:1")
        assert response.status_code == 200
        assert "does not directly support any capability" in response.text

    def test_detail_page_includes_the_capability_rollup_controls(
        self, client: TestClient
    ) -> None:
        response = client.get("/entities/app:cmdb:1")
        assert response.status_code == 200
        assert 'hx-get="/entities/app:cmdb:1/capabilities"' in response.text
        assert 'id="capability-rollup"' in response.text


class TestCapabilityRollupRoute:
    def test_unknown_entity_id_returns_404(self, client: TestClient) -> None:
        response = client.get("/entities/does-not-exist/capabilities")
        assert response.status_code == 404

    def test_rolls_up_a_capability_supported_two_hops_downstream(
        self, client: TestClient
    ) -> None:
        # OrdersDB has no capability of its own, but Storefront (2 hops
        # downstream via the API) supports Order Management.
        response = client.get(
            "/entities/db:db-metadata:1/capabilities",
            params={"direction": "downstream", "depth": 2},
        )
        assert response.status_code == 200
        assert "Order Management" in response.text
        assert "Storefront" in response.text

    def test_depth_1_does_not_yet_reach_the_capability(self, client: TestClient) -> None:
        response = client.get(
            "/entities/db:db-metadata:1/capabilities",
            params={"direction": "downstream", "depth": 1},
        )
        assert response.status_code == 200
        assert "No business capabilities found in that direction." in response.text


class TestAskRoute:
    def test_answered_question_renders_answer_and_evidence(self, client: TestClient) -> None:
        response = client.post(
            "/ask",
            data={"q": "What does Storefront depend on?"},
        )
        assert response.status_code == 200
        assert "ask-answer-ok" in response.text
        assert "Customer API v1" in response.text
        assert "Evidence" in response.text
        assert "CONSUMES" in response.text

    def test_unsupported_question_renders_explicit_non_answer(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GRAPH_RAG_ENABLED", raising=False)
        monkeypatch.delenv("HYBRID_DOC_RAG_ENABLED", raising=False)
        response = client.post("/ask", data={"q": "Why is the sky blue?"})
        assert response.status_code == 200
        assert "ask-answer-unsupported" in response.text
        assert "fixed set" in response.text.lower() or "only answer" in response.text.lower()

    def test_unknown_entity_renders_not_found(self, client: TestClient) -> None:
        response = client.post(
            "/ask",
            data={"q": "What does Totally Fake System depend on?"},
        )
        assert response.status_code == 200
        assert "ask-answer-not_found" in response.text
        assert "Totally Fake System" in response.text


class TestEvidencePanel:
    def test_detail_page_renders_evidence_section(self, client: TestClient) -> None:
        response = client.get("/entities/app:cmdb:1")
        assert response.status_code == 200
        assert "Evidence" in response.text
        assert "api-catalog" in response.text
        assert "documented" in response.text
        assert "CONSUMES" in response.text

    def test_dependency_list_shows_source_system_and_evidence_type(
        self, client: TestClient
    ) -> None:
        response = client.get("/entities/app:cmdb:1")
        assert response.status_code == 200
        assert "evidence-badge" in response.text
        assert "api-catalog" in response.text
