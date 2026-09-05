"""Run: `python -m src.ingestion.run`

Ingests sources under `data/sample/` into the configured graph store.
Always reports stale membership as a dry-run (`ADR-0009`); never deletes.
"""

from __future__ import annotations

import sys

from src.env_loader import load_project_env
from src.graph.config import get_graph_store
from src.ingestion.pipeline import run_ingestion

load_project_env()


def _print_reconciliation(result) -> None:
    recon = result.reconciliation
    if recon is None:
        return
    n_nodes = len(recon.would_delete_nodes)
    n_rels = len(recon.would_delete_rels)
    print(f"Reconciliation (dry-run): {n_nodes} stale node(s), {n_rels} stale relationship(s)")
    for node in recon.would_delete_nodes[:20]:
        print(f"  would-delete node [{node.label}] {node.name} ({node.id})")
    if n_nodes > 20:
        print(f"  ... and {n_nodes - 20} more node(s)")
    for rel in recon.would_delete_rels[:20]:
        print(
            f"  would-delete rel {rel.rel_type} "
            f"{rel.source_id} -> {rel.target_id}"
        )
    if n_rels > 20:
        print(f"  ... and {n_rels - 20} more relationship(s)")
    if n_nodes or n_rels:
        print("Report only — ingestion does not delete stale membership.")


def main() -> int:
    store = get_graph_store()
    try:
        store.bootstrap_schema()
        result = run_ingestion(store)
        print(f"Ingested {result.nodes_upserted} nodes, {result.relationships_upserted} rels")
        print(f"Graph now has {store.count_nodes()} nodes, {store.count_relationships()} rels")
        _print_reconciliation(result)
        if result.unresolved:
            print(
                f"WARNING: {len(result.unresolved)} unresolved reference(s) -- "
                "see data/unresolved/unresolved.json"
            )
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
