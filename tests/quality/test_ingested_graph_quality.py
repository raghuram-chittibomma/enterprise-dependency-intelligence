"""Runs every data-quality check (increment-5) against the real generator
output ingested end to end -- the "after every ingestion run" check from
`docs/02_testing/TEST_STRATEGY.md`, applied to the actual golden dataset
rather than hand-crafted fixtures (those live in `test_checks.py`). Uses the
fallback store so this runs fast on every commit, no Docker required.
"""

from __future__ import annotations

from src.datagen import generate
from src.graph.fallback_store import FallbackGraphStore
from src.ingestion.pipeline import run_ingestion
from src.quality.checks import run_all_checks


def test_freshly_ingested_golden_dataset_has_zero_quality_issues(tmp_path) -> None:
    data_dir = tmp_path / "sample"
    import src.datagen.generate as gen_module

    original_output_dir = gen_module.OUTPUT_DIR
    gen_module.OUTPUT_DIR = data_dir
    try:
        generate.generate_all()
    finally:
        gen_module.OUTPUT_DIR = original_output_dir

    store = FallbackGraphStore()
    result = run_ingestion(store, data_dir=data_dir, unresolved_path=tmp_path / "unresolved.json")
    assert result.unresolved == []

    report = run_all_checks(store.get_all_nodes(), store.get_all_relationships())

    assert report.ok, "\n".join(f"{i.severity}: {i.message}" for i in report.errors())
    assert report.warnings() == []
