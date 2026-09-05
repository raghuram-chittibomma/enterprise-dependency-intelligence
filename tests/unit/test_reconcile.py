"""Tests for source–graph reconciliation dry-run (`ADR-0009`, FR28)."""

from __future__ import annotations

from src.datagen import generate
from src.graph.fallback_store import FallbackGraphStore
from src.ingestion.pipeline import run_ingestion
from src.ingestion.reconcile import reconcile
from src.ontology.entities import API, Application
from src.ontology.relationships import Consumes


def test_diff_reports_stale_without_mutating() -> None:
    store = FallbackGraphStore()
    live_app = Application(
        id="app:live",
        name="Live App",
        source_system="cmdb",
        source_record_id="live",
        technology="Java",
        environment="prod",
    )
    stale_api = API(
        id="api:stale",
        name="Stale API",
        source_system="api-catalog",
        source_record_id="stale",
        version="v0",
        protocol="REST",
    )
    store.upsert_node("Application", live_app)
    store.upsert_node("API", stale_api)
    store.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="app:live",
            target_id="api:stale",
            source_system="api-catalog",
            source_record_id="c1",
        ),
        "Application",
        "API",
    )

    report = reconcile(store, [live_app], [])
    assert {n.id for n in report.would_delete_nodes} == {"api:stale"}
    assert len(report.would_delete_rels) == 1
    assert store.count_nodes() == 2
    assert store.count_relationships() == 1
    store.close()


def test_pipeline_reports_extra_but_keeps_it(tmp_path) -> None:
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
    unresolved = tmp_path / "unresolved.json"
    run_ingestion(store, data_dir=data_dir, unresolved_path=unresolved)
    base_nodes = store.count_nodes()

    store.upsert_node(
        "API",
        API(
            id="api:ghost",
            name="Ghost API",
            source_system="api-catalog",
            source_record_id="ghost",
            version="v9",
            protocol="REST",
        ),
    )
    result = run_ingestion(store, data_dir=data_dir, unresolved_path=unresolved)
    assert result.reconciliation is not None
    assert any(n.id == "api:ghost" for n in result.reconciliation.would_delete_nodes)
    assert store.count_nodes() == base_nodes + 1
    store.close()


def test_no_reconcile_apply_flag_on_cli() -> None:
    from src.ingestion import run as run_mod
    import inspect

    source = inspect.getsource(run_mod)
    assert "reconcile-apply" not in source
    assert "RECONCILE_APPLY" not in source
