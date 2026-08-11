"""Unit tests for the ontology models (increment-1).

Covers: every node type instantiates with the fields DATA_MODEL.md
specifies, every relationship type enforces its documented endpoint-type
rules, and the registries stay at exactly 9 nodes / 7 relationships (a
regression here means the ontology drifted from the accepted data model
without the doc being updated to match).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.ontology import (
    API,
    NODE_TYPES,
    RELATIONSHIP_TYPES,
    Application,
    BusinessCapability,
    Consumes,
    Criticality,
    Database,
    DataPipeline,
    EvidenceType,
    ExternalSystem,
    LifecycleStatus,
    OwnedBy,
    ReadsFrom,
    ReplacedBy,
    Report,
    Service,
    Supports,
    Team,
    WritesTo,
)
from src.ontology.relationships import EndpointTypeError, IntegratesWith


def _common_kwargs(**overrides: object) -> dict[str, object]:
    base = {
        "id": "test:unit:1",
        "name": "Test Entity",
        "source_system": "unit-test",
        "source_record_id": "1",
    }
    base.update(overrides)
    return base


class TestNodeTypes:
    def test_registry_has_exactly_9_node_types(self) -> None:
        assert len(NODE_TYPES) == 9

    def test_application_requires_technology_and_environment(self) -> None:
        app = Application(**_common_kwargs(technology="Java/Spring Boot", environment="prod"))
        assert app.label() == "Application"
        assert app.lifecycle_status == LifecycleStatus.ACTIVE
        with pytest.raises(ValidationError):
            Application(**_common_kwargs())  # missing technology/environment

    def test_service_shares_tech_environment_shape(self) -> None:
        svc = Service(**_common_kwargs(technology="Python/FastAPI", environment="prod"))
        assert svc.label() == "Service"

    def test_api_optional_implementing_application(self) -> None:
        api = API(**_common_kwargs(version="v1", protocol="REST"))
        assert api.implementing_application is None
        api2 = API(
            **_common_kwargs(version="v1", protocol="REST", implementing_application="Storefront")
        )
        assert api2.implementing_application == "Storefront"

    def test_database_key_tables_defaults_empty(self) -> None:
        db = Database(**_common_kwargs(engine="PostgreSQL"))
        assert db.key_tables == []
        db2 = Database(**_common_kwargs(engine="PostgreSQL", key_tables=["orders", "customers"]))
        assert db2.key_tables == ["orders", "customers"]

    def test_data_pipeline_type_is_constrained(self) -> None:
        DataPipeline(**_common_kwargs(pipeline_type="etl"))
        DataPipeline(**_common_kwargs(pipeline_type="batch_job"))
        with pytest.raises(ValidationError):
            DataPipeline(**_common_kwargs(pipeline_type="not_a_real_type"))

    def test_report_requires_audience_and_refresh_frequency(self) -> None:
        report = Report(**_common_kwargs(audience="internal-ops", refresh_frequency="daily"))
        assert report.audience == "internal-ops"

    def test_external_system_requires_vendor_and_category(self) -> None:
        ext = ExternalSystem(**_common_kwargs(vendor="Stripe", category="payment-gateway"))
        assert ext.category == "payment-gateway"

    def test_team_requires_business_area(self) -> None:
        team = Team(**_common_kwargs(business_area="Commerce"))
        assert team.business_area == "Commerce"

    def test_business_capability_requires_capability_area(self) -> None:
        cap = BusinessCapability(**_common_kwargs(capability_area="Customer"))
        assert cap.capability_area == "Customer"

    def test_criticality_is_optional(self) -> None:
        app = Application(
            **_common_kwargs(
                technology="Java", environment="prod", criticality=Criticality.CRITICAL
            )
        )
        assert app.criticality == Criticality.CRITICAL

    def test_extra_fields_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Team(**_common_kwargs(business_area="Commerce", not_a_real_field="x"))


class TestRelationshipTypes:
    def test_registry_has_exactly_7_relationship_types(self) -> None:
        assert len(RELATIONSHIP_TYPES) == 7

    def test_rel_type_strings_match_data_model(self) -> None:
        assert set(RELATIONSHIP_TYPES) == {
            "CONSUMES",
            "READS_FROM",
            "WRITES_TO",
            "INTEGRATES_WITH",
            "SUPPORTS",
            "OWNED_BY",
            "REPLACED_BY",
        }

    def test_consumes_endpoint_rules(self) -> None:
        Consumes.validate_endpoints("Application", "Service")
        Consumes.validate_endpoints("API", "API")
        with pytest.raises(EndpointTypeError):
            Consumes.validate_endpoints("Database", "Service")
        with pytest.raises(EndpointTypeError):
            Consumes.validate_endpoints("Application", "Database")

    def test_reads_from_endpoint_rules(self) -> None:
        ReadsFrom.validate_endpoints("Report", "Database")
        with pytest.raises(EndpointTypeError):
            ReadsFrom.validate_endpoints("Report", "ExternalSystem")

    def test_writes_to_endpoint_rules(self) -> None:
        WritesTo.validate_endpoints("DataPipeline", "Database")
        with pytest.raises(EndpointTypeError):
            WritesTo.validate_endpoints("Report", "Database")  # Report can't write

    def test_integrates_with_endpoint_rules_and_extra_fields(self) -> None:
        IntegratesWith.validate_endpoints("Application", "ExternalSystem")
        with pytest.raises(EndpointTypeError):
            IntegratesWith.validate_endpoints("API", "ExternalSystem")  # API can't integrate
        rel = IntegratesWith(
            source_id="app:1",
            target_id="ext:1",
            source_system="integration-catalog",
            source_record_id="1",
            integration_type="batch-file",
            protocol="SFTP",
            frequency="nightly",
        )
        assert rel.evidence_type == EvidenceType.DOCUMENTED

    def test_supports_endpoint_rules(self) -> None:
        Supports.validate_endpoints("API", "BusinessCapability")
        with pytest.raises(EndpointTypeError):
            Supports.validate_endpoints("Team", "BusinessCapability")

    def test_owned_by_allows_any_entity_as_source_but_only_team_as_target(self) -> None:
        for label in NODE_TYPES:
            OwnedBy.validate_endpoints(label, "Team")
        with pytest.raises(EndpointTypeError):
            OwnedBy.validate_endpoints("Application", "Application")

    def test_replaced_by_endpoint_rules(self) -> None:
        ReplacedBy.validate_endpoints("Application", "Application")
        ReplacedBy.validate_endpoints("API", "API")
        with pytest.raises(EndpointTypeError):
            ReplacedBy.validate_endpoints("Database", "Database")

    def test_depends_on_is_not_a_relationship_type(self) -> None:
        """DEPENDS_ON is computed at query time, never persisted (DATA_MODEL.md)."""
        assert "DEPENDS_ON" not in RELATIONSHIP_TYPES
