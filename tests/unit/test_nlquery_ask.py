"""Unit tests for FR11/FR13 entity resolution (`src/nlquery/resolution.py`)
and the end-to-end `ask()` pipeline against a seeded fallback store that
covers all 7 golden question shapes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.graph.fallback_store import FallbackGraphStore
from src.nlquery.ask import ask
from src.nlquery.resolution import resolve_entity
from src.ontology.entities import API, Application, BusinessCapability, Database, Service, Team
from src.ontology.relationships import Consumes, OwnedBy, ReadsFrom, Supports, WritesTo


def _seed_nl_scenario() -> FallbackGraphStore:
    """A compact Meridian-shaped graph covering every golden question:

    Storefront (Team Commerce) -CONSUMES-> Customer API v1 (Team Platform)
      Customer API v1 -READS_FROM-> Customer Database
    Order Management (Team Commerce) -CONSUMES-> Orders API (Team Orders)
      Order Management -READS_FROM-> Order Database
    Order Service (Team Orders) -CONSUMES-> Customer API v1
      Order Service -WRITES_TO-> Order Database
      Order Service -READS_FROM-> Customer Database
    Order Management -SUPPORTS-> Order Fulfillment
    Storefront -SUPPORTS-> Online Sales
    """
    store = FallbackGraphStore()

    store.upsert_node(
        "Team",
        Team(
            id="team:commerce",
            name="Commerce Platform Team",
            source_system="team-ownership",
            source_record_id="commerce",
            business_area="Commerce",
        ),
    )
    store.upsert_node(
        "Team",
        Team(
            id="team:platform",
            name="Platform Team",
            source_system="team-ownership",
            source_record_id="platform",
            business_area="Platform",
        ),
    )
    store.upsert_node(
        "Team",
        Team(
            id="team:orders",
            name="Orders Team",
            source_system="team-ownership",
            source_record_id="orders",
            business_area="Orders",
        ),
    )

    store.upsert_node(
        "Application",
        Application(
            id="app:storefront",
            name="Storefront",
            source_system="cmdb",
            source_record_id="storefront",
            technology="React",
            environment="prod",
        ),
    )
    store.upsert_node(
        "Application",
        Application(
            id="app:order-mgmt",
            name="Order Management",
            source_system="cmdb",
            source_record_id="order-mgmt",
            technology="Java",
            environment="prod",
        ),
    )
    store.upsert_node(
        "Application",
        Application(
            id="app:admin",
            name="Admin Console",
            source_system="cmdb",
            source_record_id="admin",
            technology="React",
            environment="prod",
        ),
    )
    store.upsert_node(
        "Service",
        Service(
            id="svc:order",
            name="Order Service",
            source_system="cmdb",
            source_record_id="order-svc",
            technology="Java",
            environment="prod",
        ),
    )
    store.upsert_node(
        "API",
        API(
            id="api:customer-v1",
            name="Customer API v1",
            source_system="api-catalog",
            source_record_id="customer-v1",
            version="v1",
            protocol="REST",
        ),
    )
    store.upsert_node(
        "API",
        API(
            id="api:orders",
            name="Orders API",
            source_system="api-catalog",
            source_record_id="orders",
            version="v1",
            protocol="REST",
        ),
    )
    store.upsert_node(
        "Database",
        Database(
            id="db:customer",
            name="Customer Database",
            source_system="db-metadata",
            source_record_id="customer",
            engine="PostgreSQL",
        ),
    )
    store.upsert_node(
        "Database",
        Database(
            id="db:order",
            name="Order Database",
            source_system="db-metadata",
            source_record_id="order",
            engine="PostgreSQL",
        ),
    )
    store.upsert_node(
        "BusinessCapability",
        BusinessCapability(
            id="cap:fulfillment",
            name="Order Fulfillment",
            source_system="cmdb",
            source_record_id="fulfillment",
            capability_area="Orders",
        ),
    )
    store.upsert_node(
        "BusinessCapability",
        BusinessCapability(
            id="cap:sales",
            name="Online Sales",
            source_system="cmdb",
            source_record_id="sales",
            capability_area="Commerce",
        ),
    )

    ownership = [
        ("app:storefront", "team:commerce", "Application"),
        ("app:order-mgmt", "team:commerce", "Application"),
        ("app:admin", "team:platform", "Application"),
        ("svc:order", "team:orders", "Service"),
        ("api:customer-v1", "team:platform", "API"),
        ("api:orders", "team:orders", "API"),
        ("db:customer", "team:platform", "Database"),
        ("db:order", "team:orders", "Database"),
    ]
    for source_id, team_id, source_label in ownership:
        store.upsert_relationship(
            "OWNED_BY",
            OwnedBy(
                source_id=source_id,
                target_id=team_id,
                source_system="team-ownership",
                source_record_id=source_id,
            ),
            source_label,
            "Team",
        )

    store.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="app:storefront",
            target_id="api:customer-v1",
            source_system="api-catalog",
            source_record_id="1",
        ),
        "Application",
        "API",
    )
    store.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="svc:order",
            target_id="api:customer-v1",
            source_system="api-catalog",
            source_record_id="2",
        ),
        "Service",
        "API",
    )
    store.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="app:order-mgmt",
            target_id="api:orders",
            source_system="api-catalog",
            source_record_id="3",
        ),
        "Application",
        "API",
    )
    store.upsert_relationship(
        "READS_FROM",
        ReadsFrom(
            source_id="api:customer-v1",
            target_id="db:customer",
            source_system="db-metadata",
            source_record_id="1",
        ),
        "API",
        "Database",
    )
    store.upsert_relationship(
        "READS_FROM",
        ReadsFrom(
            source_id="app:order-mgmt",
            target_id="db:order",
            source_system="db-metadata",
            source_record_id="2",
        ),
        "Application",
        "Database",
    )
    store.upsert_relationship(
        "READS_FROM",
        ReadsFrom(
            source_id="svc:order",
            target_id="db:customer",
            source_system="db-metadata",
            source_record_id="3",
        ),
        "Service",
        "Database",
    )
    store.upsert_relationship(
        "READS_FROM",
        ReadsFrom(
            source_id="app:admin",
            target_id="db:customer",
            source_system="db-metadata",
            source_record_id="5",
        ),
        "Application",
        "Database",
    )
    store.upsert_relationship(
        "WRITES_TO",
        WritesTo(
            source_id="svc:order",
            target_id="db:order",
            source_system="db-metadata",
            source_record_id="4",
        ),
        "Service",
        "Database",
    )
    store.upsert_relationship(
        "SUPPORTS",
        Supports(
            source_id="app:order-mgmt",
            target_id="cap:fulfillment",
            source_system="cmdb",
            source_record_id="1",
        ),
        "Application",
        "BusinessCapability",
    )
    store.upsert_relationship(
        "SUPPORTS",
        Supports(
            source_id="app:storefront",
            target_id="cap:sales",
            source_system="cmdb",
            source_record_id="2",
        ),
        "Application",
        "BusinessCapability",
    )
    return store


class TestResolveEntity:
    def test_exact_name_resolves(self) -> None:
        store = _seed_nl_scenario()
        result = resolve_entity(store, "Order Service")
        assert result.entity is not None
        assert result.entity.id == "svc:order"
        assert not result.ambiguous

    def test_unknown_name_does_not_resolve(self) -> None:
        store = _seed_nl_scenario()
        result = resolve_entity(store, "Totally Fake System")
        assert result.entity is None
        assert not result.ambiguous

    def test_close_scoring_names_are_ambiguous(self) -> None:
        store = _seed_nl_scenario()
        # Both "Order Service" and "Order Management" score high against a
        # bare "Order" prefix query -- FR13 must refuse to guess.
        result = resolve_entity(store, "Order")
        assert result.entity is None
        assert result.ambiguous

    def test_allowed_labels_disambiguate_same_name_types(self) -> None:
        store = _seed_nl_scenario()
        # Seed has no name collision, but the filter still must prefer only
        # allowed labels when provided.
        result = resolve_entity(
            store, "Order Management", allowed_labels=frozenset({"Application", "Service", "API"})
        )
        assert result.entity is not None
        assert result.entity.label == "Application"


class TestAskGoldenQuestions:
    def test_consumers_of(self) -> None:
        answer = ask(
            _seed_nl_scenario(),
            "What applications/services directly consume Customer API v1?",
        )
        assert answer.status == "answered"
        assert answer.question_type == "consumers_of"
        assert "Storefront" in answer.text
        assert "Order Service" in answer.text
        assert any(edge.rel_type == "CONSUMES" for edge in answer.evidence)

    def test_depends_on(self) -> None:
        answer = ask(_seed_nl_scenario(), "What does Order Service depend on?")
        assert answer.status == "answered"
        assert answer.question_type == "depends_on"
        assert "Customer API v1" in answer.text
        assert "Customer Database" in answer.text
        assert "Order Database" in answer.text

    def test_owners_downstream(self) -> None:
        answer = ask(
            _seed_nl_scenario(), "Who owns applications downstream from Customer API v1?"
        )
        assert answer.status == "answered"
        assert answer.question_type == "owners_downstream"
        assert "Commerce Platform Team" in answer.text
        assert "Storefront" in answer.text
        # Order Service is a Service, not an Application -- the type filter
        # must exclude it even though it's also a consumer of the API.
        assert "Order Service" not in answer.text

    def test_capabilities_of(self) -> None:
        answer = ask(
            _seed_nl_scenario(), "Which business capabilities depend on Order Database?"
        )
        assert answer.status == "answered"
        assert answer.question_type == "capabilities_of"
        assert "Order Fulfillment" in answer.text

    def test_path_between(self) -> None:
        answer = ask(
            _seed_nl_scenario(),
            "What is the dependency path between Storefront and Customer Database?",
        )
        assert answer.status == "answered"
        assert answer.question_type == "path_between"
        assert "Storefront" in answer.text
        assert "Customer Database" in answer.text
        assert "Customer API v1" in answer.text
        assert answer.evidence  # FR12: path edges are cited

    def test_consumed_by(self) -> None:
        answer = ask(_seed_nl_scenario(), "Which APIs are consumed by Order Management?")
        assert answer.status == "answered"
        assert answer.question_type == "consumed_by"
        assert "Orders API" in answer.text

    def test_used_by(self) -> None:
        answer = ask(_seed_nl_scenario(), "What applications use Customer Database?")
        assert answer.status == "answered"
        assert answer.question_type == "used_by"
        assert "Admin Console" in answer.text
        # Order Service is a Service, not an Application -- must be excluded.
        assert "Order Service" not in answer.text
        assert any(edge.rel_type == "READS_FROM" for edge in answer.evidence)


class TestAskNonAnswers:
    def test_unsupported_question(self) -> None:
        answer = ask(_seed_nl_scenario(), "Why does Storefront call Customer API v1?")
        assert answer.status == "unsupported"
        assert answer.evidence == []
        assert "fixed set" in answer.text.lower() or "only answer" in answer.text.lower()

    def test_unknown_entity(self) -> None:
        answer = ask(_seed_nl_scenario(), "What does Totally Fake System depend on?")
        assert answer.status == "not_found"
        assert "Totally Fake System" in answer.text

    def test_ambiguous_entity(self) -> None:
        answer = ask(_seed_nl_scenario(), "What does Order depend on?")
        assert answer.status == "ambiguous"
        assert "more than one" in answer.text.lower()


class TestAskLogging:
    def test_writes_structured_json_log_line(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log_path = tmp_path / "nlquery.log"
        monkeypatch.setenv("NLQUERY_LOG_PATH", str(log_path))
        ask(_seed_nl_scenario(), "What does Order Service depend on?")
        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["question"] == "What does Order Service depend on?"
        assert record["status"] == "answered"
        assert record["question_type"] == "depends_on"
        assert record["matched_entities"][0]["name"] == "Order Service"
        assert "latency_ms" in record
