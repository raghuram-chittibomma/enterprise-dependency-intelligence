"""Unit tests for GraphStore delete APIs (`ADR-0009`)."""

from __future__ import annotations

from src.graph.fallback_store import FallbackGraphStore
from src.ontology.entities import API, Application
from src.ontology.relationships import Consumes


def test_delete_relationship_and_node() -> None:
    store = FallbackGraphStore()
    store.upsert_node(
        "Application",
        Application(
            id="app:1",
            name="Storefront",
            source_system="cmdb",
            source_record_id="1",
            technology="React",
            environment="prod",
        ),
    )
    store.upsert_node(
        "API",
        API(
            id="api:1",
            name="Customer API",
            source_system="api-catalog",
            source_record_id="1",
            version="v1",
            protocol="REST",
        ),
    )
    store.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="app:1",
            target_id="api:1",
            source_system="api-catalog",
            source_record_id="c1",
        ),
        "Application",
        "API",
    )
    assert store.count_relationships() == 1
    assert store.delete_relationship("app:1", "api:1", "CONSUMES") is True
    assert store.count_relationships() == 0
    assert store.delete_relationship("app:1", "api:1", "CONSUMES") is False

    # Re-add edge then delete node (detaches)
    store.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="app:1",
            target_id="api:1",
            source_system="api-catalog",
            source_record_id="c1",
        ),
        "Application",
        "API",
    )
    assert store.delete_node("api:1") is True
    assert store.count_nodes() == 1
    assert store.count_relationships() == 0
    assert store.delete_node("api:1") is False
    store.close()
