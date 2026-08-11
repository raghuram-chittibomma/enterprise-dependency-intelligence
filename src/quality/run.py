"""CLI entry point: run every data-quality check (increment-5) against
whichever graph store is currently configured (see `src/graph/config.py`),
and exit non-zero if any `error`-severity issue is found -- intended to run
after every ingestion (`docs/03_operations/RUNBOOK.md`).
"""

from __future__ import annotations

import sys

from src.graph.config import get_graph_store
from src.quality.checks import run_all_checks


def main() -> int:
    store = get_graph_store()
    try:
        nodes = store.get_all_nodes()
        relationships = store.get_all_relationships()
        report = run_all_checks(nodes, relationships)

        for issue in report.issues:
            print(f"[{issue.severity.upper()}] {issue.check}: {issue.message}")

        print(
            f"\n{len(nodes)} nodes, {len(relationships)} relationships checked -- "
            f"{len(report.errors())} error(s), {len(report.warnings())} warning(s)"
        )
        return 0 if report.ok else 1
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
