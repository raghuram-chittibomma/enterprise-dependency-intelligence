"""Writes the 5 MVP1 synthetic source files to `data/sample/` from the
hand-authored scenario in `src/datagen/scenario.py`.

Run: `python -m src.datagen.generate`

Safe to re-run at any time — this always overwrites the output files with
the same deterministic content (no randomness, no timestamps in the data
itself), which is exactly what makes downstream ingestion idempotent.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from src.datagen import scenario

OUTPUT_DIR = Path("data/sample")

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


def generate_all() -> list[Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return [
        write_cmdb(),
        write_api_catalog(),
        write_db_metadata(),
        write_team_ownership(),
        write_integration_catalog(),
    ]


def main() -> None:
    paths = generate_all()
    for path in paths:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
