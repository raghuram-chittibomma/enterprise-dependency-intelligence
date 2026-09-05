"""Writes the synthetic Meridian source files to `data/sample/` from the
hand-authored scenario in `src/datagen/scenario.py` (plus MVP3 architecture
docs under `data/sample/docs/`).

Run: `python -m src.datagen.generate`

Safe to re-run at any time — this always overwrites the output files with
the same deterministic content (no randomness, no timestamps in the data
itself), which is exactly what makes downstream ingestion idempotent.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from src.datagen import architecture_docs, scenario

OUTPUT_DIR = Path("data/sample")
DOCS_DIR = OUTPUT_DIR / "docs"

CMDB_FIELDNAMES = [
    "record_id",
    "type",
    "name",
    "description",
    "criticality",
    "lifecycle_status",
    "environment",
    "technology",
    "pipeline_type",
    "schedule",
    "audience",
    "refresh_frequency",
    "business_capability",
    "replaced_by",
]

INTEGRATION_FIELDNAMES = [
    "source_system_name",
    "source_system_type",
    "target_system_name",
    "target_system_vendor",
    "target_system_category",
    "integration_type",
    "protocol",
    "frequency",
]


def _cmdb_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for app in scenario.APPLICATIONS:
        rows.append({**dict.fromkeys(CMDB_FIELDNAMES, ""), **app, "type": "application"})
    for svc in scenario.SERVICES:
        rows.append({**dict.fromkeys(CMDB_FIELDNAMES, ""), **svc, "type": "service"})
    for pipe in scenario.DATA_PIPELINES:
        rows.append({**dict.fromkeys(CMDB_FIELDNAMES, ""), **pipe, "type": "data_pipeline"})
    for report in scenario.REPORTS:
        rows.append({**dict.fromkeys(CMDB_FIELDNAMES, ""), **report, "type": "report"})
    return rows


def write_cmdb() -> Path:
    path = OUTPUT_DIR / "cmdb.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CMDB_FIELDNAMES)
        writer.writeheader()
        writer.writerows(_cmdb_rows())
    return path


def write_api_catalog() -> Path:
    path = OUTPUT_DIR / "api_catalog.json"
    path.write_text(json.dumps(scenario.APIS, indent=2) + "\n", encoding="utf-8")
    return path


def write_db_metadata() -> Path:
    path = OUTPUT_DIR / "db_metadata.json"
    path.write_text(json.dumps(scenario.DATABASES, indent=2) + "\n", encoding="utf-8")
    return path


def write_team_ownership() -> Path:
    path = OUTPUT_DIR / "team_ownership.json"
    path.write_text(json.dumps(scenario.TEAM_OWNERSHIP, indent=2) + "\n", encoding="utf-8")
    return path


def write_integration_catalog() -> Path:
    path = OUTPUT_DIR / "integration_catalog.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INTEGRATION_FIELDNAMES)
        writer.writeheader()
        writer.writerows(scenario.INTEGRATIONS)
    return path


def _render_doc(doc: architecture_docs.ArchDoc) -> str:
    related_lines = []
    for rel in doc["related_entities"]:
        related_lines.append(f"  - type: {rel['type']}")
        related_lines.append(f"    name: {rel['name']}")
    related_block = "\n".join(related_lines)
    return (
        "---\n"
        f"slug: {doc['slug']}\n"
        f"title: {doc['title']}\n"
        "related_entities:\n"
        f"{related_block}\n"
        "---\n"
        f"{doc['body'].rstrip()}\n"
    )


def write_architecture_docs() -> list[Path]:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for doc in architecture_docs.ARCHITECTURE_DOCS:
        path = DOCS_DIR / f"{doc['slug']}.md"
        path.write_text(_render_doc(doc), encoding="utf-8")
        paths.append(path)
    return paths


def generate_all() -> list[Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return [
        write_cmdb(),
        write_api_catalog(),
        write_db_metadata(),
        write_team_ownership(),
        write_integration_catalog(),
        *write_architecture_docs(),
    ]


def main() -> None:
    paths = generate_all()
    for path in paths:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
