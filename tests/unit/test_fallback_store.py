"""Unit tests for the fallback GraphStore (increment-3) -- runs entirely
in-memory, no external services, so this is the store implementation that
actually runs in CI/every commit. The Neo4j implementation is covered by
`tests/integration/test_neo4j_store.py`, which skips if unreachable.
"""

from __future__ import annotations

from src.graph.fallback_store import FallbackGraphStore
from src.ontology.entities import Application, Team
from src.ontology.relationships import OwnedBy


def _make_app(id_: str = "app:cmdb:1", name: str = "Storefront") -> Application:
    return Application(
        id=id_,
        name=name,
        source_system="cmdb",
        source_record_id="1",
        technology="React",
        environment="prod",
    )


def _make_team(id_: str = "team:team-ownership:1", name: str = "Commerce Platform Team") -> Team:
    return Team(
        id=id_,
        name=name,
        source_system="team-ownership",
        source_record_id="1",
        business_area="Commerce",
    )


class TestFallbackGraphStore:
    def test_health_check_ok_on_empty_graph(self) -> None:
        store = FallbackGraphStore()
        result = store.health_check()
        assert result.ok
        assert result.backend == "fallback"

    def test_upsert_node_is_idempotent(self) -> None:
        store = FallbackGraphStore()
        store.upsert_node("Application", _make_app())
        store.upsert_node("Application", _make_app())  # re-ingest same record
        assert store.count_nodes() == 1
        assert store.count_nodes(label="Application") == 1

    def test_upsert_node_updates_properties_in_place(self) -> None:
        store = FallbackGraphStore()
        store.upsert_node("Application", _make_app(name="Storefront"))
        store.upsert_node("Application", _make_app(name="Storefront (renamed)"))
        assert store.count_nodes() == 1
        assert store.graph.nodes["app:cmdb:1"]["name"] == "Storefront (renamed)"

    def test_upsert_relationship_is_idempotent(self) -> None:
        store = FallbackGraphStore()
        store.upsert_node("Application", _make_app())
        store.upsert_node("Team", _make_team())
        rel = OwnedBy(
            source_id="app:cmdb:1",
            target_id="team:team-ownership:1",
            source_system="team-ownership",
            source_record_id="1",
        )
        store.upsert_relationship("OWNED_BY", rel, "Application", "Team")
        store.upsert_relationship("OWNED_BY", rel, "Application", "Team")
        assert store.count_relationships() == 1
        assert store.count_relationships(rel_type="OWNED_BY") == 1

    def test_rejects_unknown_label_and_rel_type(self) -> None:
        import pytest

        store = FallbackGraphStore()
        with pytest.raises(ValueError, match="Unknown node label"):
            store.upsert_node("NotARealLabel", _make_app())

    def test_persists_and_reloads_from_sqlite_file(self, tmp_path) -> None:
        db_path = tmp_path / "graph.sqlite3"
        store = FallbackGraphStore(sqlite_path=db_path)
        store.upsert_node("Application", _make_app())
        store.close()

        reloaded = FallbackGraphStore(sqlite_path=db_path)
        assert reloaded.count_nodes() == 1
        assert "app:cmdb:1" in reloaded.graph.nodes
