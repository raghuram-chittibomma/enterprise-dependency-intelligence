"""Run: `python -m src.graph.healthcheck`

Connects to the configured graph store, runs its health check and schema
bootstrap, prints the result, and exits non-zero on failure -- suitable for
a pre-ingestion sanity check or a CI/manual smoke test.
"""

from __future__ import annotations

import sys

from src.graph.config import get_graph_store


def main() -> int:
    store = get_graph_store()
    try:
        result = store.health_check()
        print(result)
        if not result.ok:
            return 1
        store.bootstrap_schema()
        print("schema bootstrap OK")
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
