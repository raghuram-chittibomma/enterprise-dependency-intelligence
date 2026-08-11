"""Tests for the synthetic data generator (increment-2): every source file
gets written in the expected shape, and regenerating is byte-for-byte
idempotent (no timestamps/randomness leaking into the output).
"""

from __future__ import annotations

import csv
import json

from src.datagen import generate


def test_generate_all_writes_5_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)
    paths = generate.generate_all()
    assert {p.name for p in paths} == {
        "cmdb.csv",
        "api_catalog.json",
        "db_metadata.json",
        "team_ownership.json",
        "integration_catalog.csv",
    }
    for path in paths:
        assert path.exists()
        assert path.stat().st_size > 0


def test_regenerating_is_byte_for_byte_idempotent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)
    first_run = {p.name: p.read_bytes() for p in generate.generate_all()}
    second_run = {p.name: p.read_bytes() for p in generate.generate_all()}
    assert first_run == second_run


def test_cmdb_csv_is_parseable_and_covers_all_4_types(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)
    path = generate.write_cmdb()
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert set(row["type"] for row in rows) == {"application", "service", "data_pipeline", "report"}
    assert len(rows) == 8 + 5 + 3 + 2


def test_api_catalog_json_is_valid_and_has_6_entries(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)
    path = generate.write_api_catalog()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 6
    assert {api["name"] for api in data} >= {"Customer API v1", "Order API v1"}


def test_db_metadata_json_is_valid_and_has_6_entries(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)
    path = generate.write_db_metadata()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 6


def test_team_ownership_json_is_valid_and_has_5_teams(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)
    path = generate.write_team_ownership()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 5


def test_integration_catalog_csv_is_parseable(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(generate, "OUTPUT_DIR", tmp_path)
    path = generate.write_integration_catalog()
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 5
    assert {row["target_system_vendor"] for row in rows} == {
        "Stripe",
        "FedEx",
        "Mailchimp",
        "Salesforce",
    }
