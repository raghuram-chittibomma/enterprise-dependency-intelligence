"""Unit tests for FR1 (entity search), FR2 (entity detail), and FR3 (direct
dependencies) in `src/graph/queries.py`, against the fallback store seeded
with a handful of hand-written nodes -- small, synthetic, scoped to the
unit under test, per `docs/02_testing/TEST_STRATEGY.md`.
"""

from __future__ import annotations

from src.graph.fallback_store import FallbackGraphStore
from src.graph.queries import (
    MAX_ALTERNATE_PATHS,
    get_dependency_paths,
    get_dependency_traversal,
    get_direct_dependencies,
    get_entity_detail,
    get_ownership_rollup,
    get_owning_team,
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


def _seed_path_scenario() -> FallbackGraphStore:
    """A "diamond-plus-direct" topology for FR6/FR7:

    - App -READS_FROM-> DB directly (1 hop -- the shortest path).
    - App -CONSUMES-> {API A, API B, API C, API D} -READS_FROM-> DB
      (2 hops each -- four equal-length alternates, one more than
      `MAX_ALTERNATE_PATHS`, to exercise the alternates cap).
    - Orphan Application has no relationships at all, for the
      no-path-exists case.
    """
    store = FallbackGraphStore()
    store.upsert_node(
        "Application",
        Application(
            id="app:1",
            name="App",
            source_system="cmdb",
            source_record_id="1",
            technology="Java",
            environment="prod",
        ),
    )
    store.upsert_node(
        "Database",
        Database(
            id="db:1",
            name="DB",
            source_system="db-metadata",
            source_record_id="1",
            engine="PostgreSQL",
        ),
    )
    store.upsert_relationship(
        "READS_FROM",
        ReadsFrom(
            source_id="app:1",
            target_id="db:1",
            source_system="db-metadata",
            source_record_id="1",
        ),
        "Application",
        "Database",
    )
    for letter in "ABCD":
        api_id = f"api:{letter}"
        store.upsert_node(
            "API",
            API(
                id=api_id,
                name=f"API {letter}",
                source_system="api-catalog",
                source_record_id=letter,
                version="v1",
                protocol="REST",
            ),
        )
        store.upsert_relationship(
            "CONSUMES",
            Consumes(
                source_id="app:1",
                target_id=api_id,
                source_system="api-catalog",
                source_record_id=letter,
            ),
            "Application",
            "API",
        )
        store.upsert_relationship(
            "READS_FROM",
            ReadsFrom(
                source_id=api_id,
                target_id="db:1",
                source_system="db-metadata",
                source_record_id=letter,
            ),
            "API",
            "Database",
        )
    store.upsert_node(
        "Application",
        Application(
            id="app:orphan",
            name="Orphan App",
            source_system="cmdb",
            source_record_id="orphan",
            technology="Java",
            environment="prod",
        ),
    )
    return store


class TestGetDependencyPaths:
    def test_returns_none_for_unknown_source_id(self) -> None:
        store = _seed_path_scenario()
        assert get_dependency_paths(store, "does-not-exist", "db:1") is None

    def test_returns_none_for_unknown_target_id(self) -> None:
        store = _seed_path_scenario()
        assert get_dependency_paths(store, "app:1", "does-not-exist") is None

    def test_source_equal_to_target_is_a_trivial_single_node_path(self) -> None:
        store = _seed_path_scenario()
        result = get_dependency_paths(store, "app:1", "app:1")
        assert result is not None
        assert result.shortest is not None
        assert [n.id for n in result.shortest.nodes] == ["app:1"]
        assert result.shortest.edges == []
        assert result.alternates == []

    def test_no_dependency_path_connects_disconnected_entities(self) -> None:
        store = _seed_path_scenario()
        result = get_dependency_paths(store, "app:1", "app:orphan")
        assert result is not None
        assert result.shortest is None
        assert result.alternates == []

    def test_shortest_path_is_the_minimum_hop_walk(self) -> None:
        store = _seed_path_scenario()
        result = get_dependency_paths(store, "app:1", "db:1")
        assert result is not None
        assert result.shortest is not None
        assert result.shortest.hops == 1
        assert [n.id for n in result.shortest.nodes] == ["app:1", "db:1"]

    def test_path_edges_preserve_the_original_relationship_direction(self) -> None:
        store = _seed_path_scenario()
        result = get_dependency_paths(store, "app:1", "db:1")
        assert result is not None
        assert result.shortest is not None
        edge = result.shortest.edges[0]
        assert edge.source_id == "app:1"
        assert edge.target_id == "db:1"
        assert edge.rel_type == "READS_FROM"

    def test_walking_a_dependency_edge_against_its_direction_is_allowed(self) -> None:
        # Reverse the query: DB doesn't depend on anything, but the
        # connection is still findable walking the READS_FROM edge
        # backwards -- direction only matters for FR3's upstream/downstream
        # labeling, not for "are these two systems connected" (FR6/FR7).
        store = _seed_path_scenario()
        result = get_dependency_paths(store, "db:1", "app:1")
        assert result is not None
        assert result.shortest is not None
        assert [n.id for n in result.shortest.nodes] == ["db:1", "app:1"]
        edge = result.shortest.edges[0]
        assert (edge.source_id, edge.target_id) == ("app:1", "db:1")

    def test_alternate_paths_are_found_when_they_exist(self) -> None:
        store = _seed_path_scenario()
        result = get_dependency_paths(store, "app:1", "db:1")
        assert result is not None
        assert len(result.alternates) > 0
        for alternate in result.alternates:
            assert alternate.hops == 2  # the App-API-DB detours

    def test_alternate_paths_are_capped_at_the_configured_maximum(self) -> None:
        store = _seed_path_scenario()
        result = get_dependency_paths(store, "app:1", "db:1")
        assert result is not None
        assert len(result.alternates) == MAX_ALTERNATE_PATHS

    def test_alternates_are_distinct_from_each_other_and_the_shortest(self) -> None:
        store = _seed_path_scenario()
        result = get_dependency_paths(store, "app:1", "db:1")
        assert result is not None
        assert result.shortest is not None
        node_sequences = [tuple(n.id for n in result.shortest.nodes)]
        for alternate in result.alternates:
            node_sequences.append(tuple(n.id for n in alternate.nodes))
        assert len(node_sequences) == len(set(node_sequences))


def _seed_ownership_scenario() -> FallbackGraphStore:
    """App1 (Team A) -CONSUMES-> {Api1 (Team B), Api2 (unowned)};
    Api1 -READS_FROM-> Db1 (Team B) -- exercises the "root itself
    included", "grouped by team", and "unowned bucket" cases together.
    """
    store = FallbackGraphStore()
    store.upsert_node(
        "Team",
        Team(
            id="team:a",
            name="Team A",
            source_system="team-ownership",
            source_record_id="a",
            business_area="Commerce",
        ),
    )
    store.upsert_node(
        "Team",
        Team(
            id="team:b",
            name="Team B",
            source_system="team-ownership",
            source_record_id="b",
            business_area="Platform",
        ),
    )
    store.upsert_node(
        "Application",
        Application(
            id="app:1",
            name="App1",
            source_system="cmdb",
            source_record_id="1",
            technology="Java",
            environment="prod",
        ),
    )
    store.upsert_relationship(
        "OWNED_BY",
        OwnedBy(
            source_id="app:1",
            target_id="team:a",
            source_system="team-ownership",
            source_record_id="1",
        ),
        "Application",
        "Team",
    )
    store.upsert_node(
        "API",
        API(
            id="api:1",
            name="Api1",
            source_system="api-catalog",
            source_record_id="1",
            version="v1",
            protocol="REST",
        ),
    )
    store.upsert_relationship(
        "OWNED_BY",
        OwnedBy(
            source_id="api:1",
            target_id="team:b",
            source_system="team-ownership",
            source_record_id="2",
        ),
        "API",
        "Team",
    )
    store.upsert_node(
        "API",
        API(
            id="api:2",
            name="Api2",
            source_system="api-catalog",
            source_record_id="2",
            version="v1",
            protocol="REST",
        ),
    )
    store.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="app:1", target_id="api:1", source_system="api-catalog", source_record_id="1"
        ),
        "Application",
        "API",
    )
    store.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="app:1", target_id="api:2", source_system="api-catalog", source_record_id="2"
        ),
        "Application",
        "API",
    )
    store.upsert_node(
        "Database",
        Database(
            id="db:1",
            name="Db1",
            source_system="db-metadata",
            source_record_id="1",
            engine="PostgreSQL",
        ),
    )
    store.upsert_relationship(
        "OWNED_BY",
        OwnedBy(
            source_id="db:1",
            target_id="team:b",
            source_system="team-ownership",
            source_record_id="3",
        ),
        "Database",
        "Team",
    )
    store.upsert_relationship(
        "READS_FROM",
        ReadsFrom(
            source_id="api:1", target_id="db:1", source_system="db-metadata", source_record_id="1"
        ),
        "API",
        "Database",
    )
    return store


class TestGetOwningTeam:
    def test_returns_the_owning_team(self) -> None:
        store = _seed_ownership_scenario()
        owner = get_owning_team(store, "app:1")
        assert owner is not None
        assert owner.id == "team:a"
        assert owner.name == "Team A"

    def test_returns_none_for_an_unowned_entity(self) -> None:
        store = _seed_ownership_scenario()
        assert get_owning_team(store, "api:2") is None

    def test_returns_none_for_an_unknown_entity(self) -> None:
        store = _seed_ownership_scenario()
        assert get_owning_team(store, "does-not-exist") is None


class TestGetOwnershipRollup:
    def test_returns_none_for_unknown_id(self) -> None:
        store = _seed_ownership_scenario()
        assert get_ownership_rollup(store, "does-not-exist", "upstream") is None

    def test_includes_the_root_entitys_own_team(self) -> None:
        store = _seed_ownership_scenario()
        rollup = get_ownership_rollup(store, "app:1", "upstream", max_depth=2)
        assert rollup is not None
        team_a_group = next(g for g in rollup.groups if g.team and g.team.id == "team:a")
        assert {e.id for e in team_a_group.entities} == {"app:1"}

    def test_groups_entities_by_owning_team(self) -> None:
        store = _seed_ownership_scenario()
        rollup = get_ownership_rollup(store, "app:1", "upstream", max_depth=2)
        assert rollup is not None
        team_b_group = next(g for g in rollup.groups if g.team and g.team.id == "team:b")
        assert {e.id for e in team_b_group.entities} == {"api:1", "db:1"}

    def test_unowned_entities_are_grouped_under_a_none_team(self) -> None:
        store = _seed_ownership_scenario()
        rollup = get_ownership_rollup(store, "app:1", "upstream", max_depth=2)
        assert rollup is not None
        unowned_group = next(g for g in rollup.groups if g.team is None)
        assert {e.id for e in unowned_group.entities} == {"api:2"}

    def test_depth_1_excludes_the_second_hop_owner(self) -> None:
        store = _seed_ownership_scenario()
        rollup = get_ownership_rollup(store, "app:1", "upstream", max_depth=1)
        assert rollup is not None
        all_entity_ids = {e.id for g in rollup.groups for e in g.entities}
        assert "db:1" not in all_entity_ids

    def test_downstream_direction_rolls_up_dependents_instead(self) -> None:
        store = _seed_ownership_scenario()
        rollup = get_ownership_rollup(store, "api:1", "downstream", max_depth=2)
        assert rollup is not None
        all_entity_ids = {e.id for g in rollup.groups for e in g.entities}
        assert all_entity_ids == {"api:1", "app:1"}

    def test_groups_are_sorted_by_team_name_with_unowned_last(self) -> None:
        store = _seed_ownership_scenario()
        rollup = get_ownership_rollup(store, "app:1", "upstream", max_depth=2)
        assert rollup is not None
        team_names = [g.team.name if g.team else None for g in rollup.groups]
        assert team_names == ["Team A", "Team B", None]
