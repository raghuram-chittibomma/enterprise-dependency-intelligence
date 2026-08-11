"""Unit tests for FR1 (entity search), FR2 (entity detail), and FR3 (direct
dependencies) in `src/graph/queries.py`, against the fallback store seeded
with a handful of hand-written nodes -- small, synthetic, scoped to the
unit under test, per `docs/02_testing/TEST_STRATEGY.md`.
"""

from __future__ import annotations

from src.graph.fallback_store import FallbackGraphStore
from src.graph.queries import (
    get_dependency_traversal,
    get_direct_dependencies,
    get_entity_detail,
    search_entities,
)
from src.ontology.entities import API, Application, Database, Service, Team
from src.ontology.relationships import Consumes, OwnedBy, ReadsFrom


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
    store.upsert_node(
        "Team",
        Team(
            id="team:team-ownership:1",
            name="Commerce Platform Team",
            source_system="team-ownership",
            source_record_id="1",
            business_area="Commerce",
        ),
    )
    store.upsert_relationship(
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
    store.upsert_relationship(
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
    store.upsert_relationship(
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


class TestGetEntityDetail:
    def test_returns_none_for_unknown_id(self) -> None:
        store = _seed_store()
        assert get_entity_detail(store, "does-not-exist") is None

    def test_returns_common_metadata_fields(self) -> None:
        store = _seed_store()
        detail = get_entity_detail(store, "app:cmdb:1")
        assert detail is not None
        assert detail.label == "Application"
        assert detail.name == "Storefront"
        assert detail.description == "Customer-facing e-commerce storefront."
        assert detail.criticality == "critical"
        assert detail.lifecycle_status == "active"

    def test_returns_owner_when_owned_by_relationship_exists(self) -> None:
        store = _seed_store()
        detail = get_entity_detail(store, "app:cmdb:1")
        assert detail is not None
        assert detail.owner is not None
        assert detail.owner.id == "team:team-ownership:1"
        assert detail.owner.name == "Commerce Platform Team"

    def test_owner_is_none_when_no_owned_by_relationship(self) -> None:
        store = _seed_store()
        detail = get_entity_detail(store, "app:cmdb:2")
        assert detail is not None
        assert detail.owner is None

    def test_type_specific_properties_are_surfaced(self) -> None:
        store = _seed_store()
        detail = get_entity_detail(store, "app:cmdb:1")
        assert detail is not None
        assert detail.properties["technology"] == "React"
        assert detail.properties["environment"] == "prod"
        # Common fields (already promoted to top-level attributes) shouldn't
        # be duplicated in the type-specific properties bag.
        assert "name" not in detail.properties
        assert "criticality" not in detail.properties

    def test_provenance_fields_are_included(self) -> None:
        store = _seed_store()
        detail = get_entity_detail(store, "app:cmdb:1")
        assert detail is not None
        assert detail.source_system == "cmdb"
        assert detail.source_record_id == "1"
        assert detail.ingested_at


class TestGetDirectDependencies:
    def test_returns_none_for_unknown_id(self) -> None:
        store = _seed_store()
        assert get_direct_dependencies(store, "does-not-exist") is None

    def test_upstream_is_what_the_entity_depends_on(self) -> None:
        store = _seed_store()
        deps = get_direct_dependencies(store, "app:cmdb:1")
        assert deps is not None
        assert len(deps.upstream) == 1
        assert deps.upstream[0].entity.id == "api:api-catalog:1"
        assert deps.upstream[0].rel_type == "CONSUMES"

    def test_downstream_is_what_depends_on_the_entity(self) -> None:
        store = _seed_store()
        deps = get_direct_dependencies(store, "api:api-catalog:1")
        assert deps is not None
        assert len(deps.downstream) == 1
        assert deps.downstream[0].entity.id == "app:cmdb:1"
        assert deps.downstream[0].rel_type == "CONSUMES"

    def test_an_entity_can_have_both_upstream_and_downstream(self) -> None:
        store = _seed_store()
        deps = get_direct_dependencies(store, "api:api-catalog:1")
        assert deps is not None
        assert {e.entity.id for e in deps.upstream} == {"db:db-metadata:1"}
        assert {e.entity.id for e in deps.downstream} == {"app:cmdb:1"}

    def test_is_direct_only_not_transitive(self) -> None:
        # Storefront -CONSUMES-> Customer API v1 -READS_FROM-> OrdersDB:
        # Storefront's direct upstream is only the API, not the database
        # two hops away.
        store = _seed_store()
        deps = get_direct_dependencies(store, "app:cmdb:1")
        assert deps is not None
        assert "db:db-metadata:1" not in {e.entity.id for e in deps.upstream}

    def test_ownership_and_other_non_dependency_edges_are_excluded(self) -> None:
        # Storefront is OWNED_BY the Commerce Platform Team -- that's not a
        # dependency edge (DATA_MODEL.md), so the team must not appear here.
        store = _seed_store()
        deps = get_direct_dependencies(store, "app:cmdb:1")
        assert deps is not None
        all_ids = {e.entity.id for e in deps.upstream} | {e.entity.id for e in deps.downstream}
        assert "team:team-ownership:1" not in all_ids

    def test_entity_with_no_dependency_edges_returns_empty_lists(self) -> None:
        store = _seed_store()
        deps = get_direct_dependencies(store, "app:cmdb:3")  # Customer Portal
        assert deps is not None
        assert deps.upstream == []
        assert deps.downstream == []


class TestGetDependencyTraversal:
    """`_seed_store`'s chain: Storefront -CONSUMES-> Customer API v1
    -READS_FROM-> OrdersDB.
    """

    def test_returns_none_for_unknown_id(self) -> None:
        store = _seed_store()
        assert get_dependency_traversal(store, "does-not-exist", "upstream") is None

    def test_rejects_an_invalid_direction(self) -> None:
        store = _seed_store()
        try:
            get_dependency_traversal(store, "app:cmdb:1", "sideways")
        except ValueError as exc:
            assert "direction" in str(exc)
        else:
            raise AssertionError("expected ValueError for an invalid direction")

    def test_depth_1_reaches_only_the_direct_neighbor(self) -> None:
        store = _seed_store()
        result = get_dependency_traversal(store, "app:cmdb:1", "upstream", max_depth=1)
        assert result is not None
        assert {n.entity.id: n.depth for n in result.nodes} == {
            "app:cmdb:1": 0,
            "api:api-catalog:1": 1,
        }
        assert len(result.edges) == 1
        assert result.edges[0].rel_type == "CONSUMES"

    def test_depth_2_reaches_the_second_hop(self) -> None:
        store = _seed_store()
        result = get_dependency_traversal(store, "app:cmdb:1", "upstream", max_depth=2)
        assert result is not None
        depths = {n.entity.id: n.depth for n in result.nodes}
        assert depths == {"app:cmdb:1": 0, "api:api-catalog:1": 1, "db:db-metadata:1": 2}
        assert {(e.source_id, e.target_id, e.rel_type) for e in result.edges} == {
            ("app:cmdb:1", "api:api-catalog:1", "CONSUMES"),
            ("api:api-catalog:1", "db:db-metadata:1", "READS_FROM"),
        }

    def test_downstream_is_the_mirror_of_upstream(self) -> None:
        store = _seed_store()
        result = get_dependency_traversal(store, "db:db-metadata:1", "downstream", max_depth=2)
        assert result is not None
        depths = {n.entity.id: n.depth for n in result.nodes}
        assert depths == {"db:db-metadata:1": 0, "api:api-catalog:1": 1, "app:cmdb:1": 2}

    def test_requested_depth_beyond_available_hops_does_not_error(self) -> None:
        store = _seed_store()
        result = get_dependency_traversal(store, "app:cmdb:1", "upstream", max_depth=5)
        assert result is not None
        assert len(result.nodes) == 3  # stops once the frontier is empty, no phantom hops

    def test_depth_is_clamped_to_the_configured_maximum(self) -> None:
        from src.graph.queries import MAX_TRAVERSAL_DEPTH

        store = _seed_store()
        result = get_dependency_traversal(store, "app:cmdb:1", "upstream", max_depth=999)
        assert result is not None
        assert result.max_depth == MAX_TRAVERSAL_DEPTH

    def test_depth_is_clamped_to_at_least_one(self) -> None:
        store = _seed_store()
        result = get_dependency_traversal(store, "app:cmdb:1", "upstream", max_depth=0)
        assert result is not None
        assert result.max_depth == 1

    def test_a_cycle_does_not_hang_and_its_edges_are_still_reported(self) -> None:
        store = FallbackGraphStore()
        store.upsert_node(
            "Service",
            Service(
                id="svc:cmdb:1",
                name="Service A",
                source_system="cmdb",
                source_record_id="1",
                technology="Java",
                environment="prod",
            ),
        )
        store.upsert_node(
            "Service",
            Service(
                id="svc:cmdb:2",
                name="Service B",
                source_system="cmdb",
                source_record_id="2",
                technology="Java",
                environment="prod",
            ),
        )
        store.upsert_relationship(
            "CONSUMES",
            Consumes(
                source_id="svc:cmdb:1",
                target_id="svc:cmdb:2",
                source_system="cmdb",
                source_record_id="1",
            ),
            "Service",
            "Service",
        )
        store.upsert_relationship(
            "CONSUMES",
            Consumes(
                source_id="svc:cmdb:2",
                target_id="svc:cmdb:1",
                source_system="cmdb",
                source_record_id="2",
            ),
            "Service",
            "Service",
        )

        result = get_dependency_traversal(store, "svc:cmdb:1", "upstream", max_depth=5)
        assert result is not None
        # Only 2 nodes -- the cycle back to an already-visited node adds no
        # new node, but its edge is still surfaced for the subgraph (FR5).
        assert {n.entity.id for n in result.nodes} == {"svc:cmdb:1", "svc:cmdb:2"}
        assert {(e.source_id, e.target_id) for e in result.edges} == {
            ("svc:cmdb:1", "svc:cmdb:2"),
            ("svc:cmdb:2", "svc:cmdb:1"),
        }
