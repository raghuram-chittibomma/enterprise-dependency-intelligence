"""Unit tests for FR1 (entity search) in `src/graph/queries.py`, against the
fallback store seeded with a handful of hand-written nodes -- small,
synthetic, scoped to the unit under test, per
`docs/02_testing/TEST_STRATEGY.md`.
"""

from __future__ import annotations

from src.graph.fallback_store import FallbackGraphStore
from src.graph.queries import search_entities
from src.ontology.entities import API, Application, Database


def _seed_store() -> FallbackGraphStore:
    store = FallbackGraphStore()
    store.upsert_node(
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
    store.upsert_node(
        "Application",
        Application(
            id="app:cmdb:2",
            name="Storefront Admin",
            criticality="medium",
            source_system="cmdb",
            source_record_id="2",
            technology="React",
            environment="prod",
        ),
    )
    store.upsert_node(
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
    store.upsert_node(
        "Database",
        Database(
            id="db:db-metadata:1",
            name="OrdersDB",
            source_system="db-metadata",
            source_record_id="1",
            engine="PostgreSQL",
        ),
    )
    store.upsert_node(
        "Application",
        Application(
            id="app:cmdb:3",
            name="Customer Portal",
            source_system="cmdb",
            source_record_id="3",
            technology="React",
            environment="prod",
        ),
    )
    return store


class TestSearchEntities:
    def test_exact_name_match_ranks_first(self) -> None:
        store = _seed_store()
        results = search_entities(store, "Storefront")
        assert results[0].id == "app:cmdb:1"
        assert results[0].name == "Storefront"

    def test_substring_match_is_found(self) -> None:
        store = _seed_store()
        results = search_entities(store, "Store")
        result_ids = {r.id for r in results}
        assert {"app:cmdb:1", "app:cmdb:2"} <= result_ids

    def test_is_case_insensitive(self) -> None:
        store = _seed_store()
        results = search_entities(store, "storefront")
        assert any(r.id == "app:cmdb:1" for r in results)

    def test_tolerates_a_small_typo(self) -> None:
        store = _seed_store()
        results = search_entities(store, "Storfront")  # missing an 'e'
        assert any(r.id == "app:cmdb:1" for r in results)

    def test_matches_across_entity_types(self) -> None:
        store = _seed_store()
        assert search_entities(store, "Customer API v1")[0].label == "API"
        assert search_entities(store, "OrdersDB")[0].label == "Database"

    def test_unrelated_query_returns_no_results(self) -> None:
        store = _seed_store()
        assert search_entities(store, "xyznonexistent") == []

    def test_blank_query_returns_no_results(self) -> None:
        store = _seed_store()
        assert search_entities(store, "   ") == []

    def test_limit_caps_result_count(self) -> None:
        store = _seed_store()
        results = search_entities(store, "a", limit=2)
        assert len(results) <= 2

    def test_result_includes_metadata_fields(self) -> None:
        store = _seed_store()
        result = search_entities(store, "Storefront")[0]
        assert result.description == "Customer-facing e-commerce storefront."
        assert result.criticality == "critical"
        assert result.lifecycle_status == "active"

    def test_multiword_typo_does_not_false_positive_on_a_shared_word(self) -> None:
        """A single well-matching word shouldn't be enough to match an
        unrelated multi-word name -- "Custmer API" should find "Customer
        API v1" (both words align) but not "Customer Portal" (only
        "Custmer"/"Customer" aligns; "API" has nothing to match against).
        """
        store = _seed_store()
        results = search_entities(store, "Custmer API")
        assert results[0].id == "api:api-catalog:1"
        assert "app:cmdb:3" not in {r.id for r in results}

    def test_exact_match_outranks_a_substring_match(self) -> None:
        store = _seed_store()
        results = search_entities(store, "Storefront")
        assert results[0].id == "app:cmdb:1"
        assert results[0].score == 100.0

    def test_reordered_multiword_query_still_matches(self) -> None:
        store = _seed_store()
        results = search_entities(store, "API Customer v1")
        assert results[0].id == "api:api-catalog:1"
