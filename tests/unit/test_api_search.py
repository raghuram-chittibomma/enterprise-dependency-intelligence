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
from src.ontology.entities import API, Application


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
