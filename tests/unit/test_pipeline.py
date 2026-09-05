"""End-to-end ingestion tests (increment-4) against the in-memory fallback
store -- fast enough to run every commit, unlike the Neo4j-backed version in
`tests/integration/test_pipeline_neo4j.py`. Exercises the real generator
output (`src/datagen/generate.py`) end to end, not hand-crafted fixtures, so
a mismatch between the scenario and the parsers/pipeline shows up here.

Expected counts are computed from `src/datagen/scenario.py` (see that
file's module docstring) -- a change to the scenario data should come with
a deliberate update to these numbers, not a silent drift.
"""

from __future__ import annotations

from src.datagen import generate
from src.graph.fallback_store import FallbackGraphStore
from src.ingestion.pipeline import run_ingestion

# 8 apps + 5 services + 6 APIs + 6 DBs + 3 pipelines + 2 reports + 5 teams
# + 4 external systems + 6 capabilities + 10 architecture documents
EXPECTED_NODE_COUNT = 55
# 21 CONSUMES + 16 READS_FROM + 9 WRITES_TO + 5 INTEGRATES_WITH + 19 SUPPORTS
# + 30 OWNED_BY + 1 REPLACED_BY + 30 DOCUMENTED_BY
EXPECTED_RELATIONSHIP_COUNT = 131


def _ingest_into_fresh_fallback_store(tmp_path):
    data_dir = tmp_path / "sample"
    import src.datagen.generate as gen_module

    original_output_dir = gen_module.OUTPUT_DIR
    original_docs_dir = gen_module.DOCS_DIR
    gen_module.OUTPUT_DIR = data_dir
    gen_module.DOCS_DIR = data_dir / "docs"
    try:
        generate.generate_all()
    finally:
        gen_module.OUTPUT_DIR = original_output_dir
        gen_module.DOCS_DIR = original_docs_dir

    store = FallbackGraphStore()
    result = run_ingestion(
        store, data_dir=data_dir, unresolved_path=tmp_path / "unresolved.json"
    )
    return store, result


class TestIngestionPipeline:
    def test_ingests_expected_node_and_relationship_counts(self, tmp_path) -> None:
        store, result = _ingest_into_fresh_fallback_store(tmp_path)
        assert result.nodes_upserted == EXPECTED_NODE_COUNT
        assert result.relationships_upserted == EXPECTED_RELATIONSHIP_COUNT
        assert store.count_nodes() == EXPECTED_NODE_COUNT
        assert store.count_relationships() == EXPECTED_RELATIONSHIP_COUNT

    def test_zero_unresolved_references(self, tmp_path) -> None:
        _store, result = _ingest_into_fresh_fallback_store(tmp_path)
        assert result.unresolved == []

    def test_per_label_and_per_rel_type_counts(self, tmp_path) -> None:
        store, _result = _ingest_into_fresh_fallback_store(tmp_path)
        assert store.count_nodes(label="Application") == 8
        assert store.count_nodes(label="Service") == 5
        assert store.count_nodes(label="API") == 6
        assert store.count_nodes(label="Database") == 6
        assert store.count_nodes(label="DataPipeline") == 3
        assert store.count_nodes(label="Report") == 2
        assert store.count_nodes(label="Team") == 5
        assert store.count_nodes(label="ExternalSystem") == 4
        assert store.count_nodes(label="BusinessCapability") == 6
        assert store.count_nodes(label="Document") == 10

        assert store.count_relationships(rel_type="CONSUMES") == 21
        assert store.count_relationships(rel_type="READS_FROM") == 16
        assert store.count_relationships(rel_type="WRITES_TO") == 9
        assert store.count_relationships(rel_type="INTEGRATES_WITH") == 5
        assert store.count_relationships(rel_type="SUPPORTS") == 19
        assert store.count_relationships(rel_type="OWNED_BY") == 30
        assert store.count_relationships(rel_type="REPLACED_BY") == 1
        assert store.count_relationships(rel_type="DOCUMENTED_BY") == 30

    def test_reingesting_is_idempotent(self, tmp_path) -> None:
        store, first = _ingest_into_fresh_fallback_store(tmp_path)
        from src.ingestion.pipeline import run_ingestion as run_again

        second = run_again(
            store, data_dir=tmp_path / "sample", unresolved_path=tmp_path / "u2.json"
        )
        assert store.count_nodes() == EXPECTED_NODE_COUNT
        assert store.count_relationships() == EXPECTED_RELATIONSHIP_COUNT
        assert first.nodes_upserted == second.nodes_upserted
        assert first.relationships_upserted == second.relationships_upserted

    def test_key_edges_for_planned_golden_questions_exist(self, tmp_path) -> None:
        """Spot-checks the specific edges the 7 planned NL golden questions
        (docs/00_project/PRODUCT_BRIEF.md) will depend on -- catching a
        wiring bug here is much cheaper than in increment-13.
        """
        store, _result = _ingest_into_fresh_fallback_store(tmp_path)
        graph = store.graph

        def node_id(label_prefix: str, name: str) -> str:
            matches = [
                n
                for n, data in graph.nodes(data=True)
                if data.get("name") == name and n.startswith(label_prefix)
            ]
            assert len(matches) == 1, f"expected exactly 1 match for {name!r}, got {matches}"
            return matches[0]

        storefront = node_id("app:", "Storefront")
        customer_api = node_id("api:", "Customer API v1")
        customer_portal = node_id("app:", "Customer Portal")
        order_service = node_id("svc:", "Order Service")
        customer_service = node_id("svc:", "Customer Service")
        customer_db = node_id("db:", "Customer Database")
        order_management = node_id("app:", "Order Management")
        order_db = node_id("db:", "Order Database")

        # Q1: consumers of Customer API v1.
        assert graph.has_edge(storefront, customer_api, key="CONSUMES")
        assert graph.has_edge(customer_portal, customer_api, key="CONSUMES")
        assert graph.has_edge(order_service, customer_api, key="CONSUMES")

        # Q5: Storefront -> Customer API v1 -> Customer Service -> Customer Database.
        assert graph.has_edge(customer_api, customer_service, key="CONSUMES")
        assert graph.has_edge(customer_service, customer_db, key="WRITES_TO") or graph.has_edge(
            customer_service, customer_db, key="READS_FROM"
        )

        # Q4/alternate-path case: Order Management both reads Order Database
        # directly AND reaches it transitively via Order API v1 -> Order Service.
        assert graph.has_edge(order_management, order_db, key="READS_FROM")
        order_api = node_id("api:", "Order API v1")
        assert graph.has_edge(order_management, order_api, key="CONSUMES")
        assert graph.has_edge(order_api, order_service, key="CONSUMES")
        assert graph.has_edge(order_service, order_db, key="WRITES_TO")
