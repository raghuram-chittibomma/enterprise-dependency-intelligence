"""Run: `python -m src.ingestion.run`

Ingests the 5 source files under `data/sample/` into the configured graph
store (see `src/graph/config.py`). Safe to re-run at any time -- idempotent
by construction (ADR-0002/ADR-0003).
"""

from __future__ import annotations

import sys

from src.graph.config import get_graph_store
from src.ingestion.pipeline import run_ingestion


def main() -> int:
    store = get_graph_store()
    try:
        store.bootstrap_schema()
        result = run_ingestion(store)
        print(f"Ingested {result.nodes_upserted} nodes, {result.relationships_upserted} rels")
        print(f"Graph now has {store.count_nodes()} nodes, {store.count_relationships()} rels")
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
