"""Cross-reference integrity checks for the hand-authored scenario
(`src/datagen/scenario.py`) — every name referenced by one record must
resolve to an actual entity of the stated type, and every implied
relationship must satisfy the ontology's endpoint-type rules. Catching a
typo or a dangling reference here is much cheaper than discovering it via a
failed golden-dataset scenario several increments later.
"""

from __future__ import annotations

import pytest

from src.datagen import scenario
from src.ontology.relationships import Consumes, IntegratesWith, OwnedBy, ReadsFrom, WritesTo

_TYPE_TO_LABEL = {
    "application": "Application",
    "service": "Service",
    "api": "API",
    "database": "Database",
    "data_pipeline": "DataPipeline",
    "report": "Report",
}

_NAMES_BY_TYPE: dict[str, set[str]] = {
    "application": {a["name"] for a in scenario.APPLICATIONS},
    "service": {s["name"] for s in scenario.SERVICES},
    "api": {a["name"] for a in scenario.APIS},
    "database": {d["name"] for d in scenario.DATABASES},
    "data_pipeline": {p["name"] for p in scenario.DATA_PIPELINES},
    "report": {r["name"] for r in scenario.REPORTS},
}


def _assert_ref(name: str, type_: str) -> None:
    assert type_ in _NAMES_BY_TYPE, f"Unknown type {type_!r} referenced for {name!r}"
    assert name in _NAMES_BY_TYPE[type_], f"{name!r} not found among {type_} entities"


class TestEntityCounts:
    """Pinned counts (see scenario.py's module docstring) — a change here
    should be deliberate, not an accidental side effect of an edit."""

    def test_expected_counts(self) -> None:
        assert len(scenario.APPLICATIONS) == 8
        assert len(scenario.SERVICES) == 5
        assert len(scenario.APIS) == 6
        assert len(scenario.DATABASES) == 6
        assert len(scenario.DATA_PIPELINES) == 3
        assert len(scenario.REPORTS) == 2
        assert len(scenario.TEAM_OWNERSHIP) == 5

    def test_no_duplicate_names_within_a_type(self) -> None:
        for type_, names in _NAMES_BY_TYPE.items():
            all_names = [
                a["name"]
                for a in (
                    scenario.APPLICATIONS
                    if type_ == "application"
                    else scenario.SERVICES
                    if type_ == "service"
                    else scenario.APIS
                    if type_ == "api"
                    else scenario.DATABASES
                    if type_ == "database"
                    else scenario.DATA_PIPELINES
                    if type_ == "data_pipeline"
                    else scenario.REPORTS
                )
            ]
            assert len(all_names) == len(names), f"Duplicate name(s) among {type_}"


class TestCrossReferences:
    def test_api_backend_service_and_implementing_application_resolve(self) -> None:
        for api in scenario.APIS:
            backend = api.get("backend_service")
            if backend:
                _assert_ref(backend, "service")
            implementing = api.get("implementing_application")
            if implementing:
                # May name either the backend service or an application.
                assert implementing in _NAMES_BY_TYPE["service"] | _NAMES_BY_TYPE["application"]

    def test_api_consuming_applications_resolve(self) -> None:
        for api in scenario.APIS:
            for consumer in api["consuming_applications"]:
                _assert_ref(consumer["name"], consumer["type"])

    def test_db_readers_and_writers_resolve(self) -> None:
        for db in scenario.DATABASES:
            for ref in [*db["readers"], *db["writers"]]:
                _assert_ref(ref["name"], ref["type"])

    def test_team_systems_owned_resolve(self) -> None:
        for team in scenario.TEAM_OWNERSHIP:
            for system in team["systems_owned"]:
                _assert_ref(system["name"], system["type"])

    def test_integration_source_systems_resolve(self) -> None:
        for row in scenario.INTEGRATIONS:
            _assert_ref(row["source_system_name"], row["source_system_type"])

    def test_replaced_by_targets_resolve(self) -> None:
        for app in scenario.APPLICATIONS:
            successor = app.get("replaced_by")
            if successor:
                assert successor in _NAMES_BY_TYPE["application"] | _NAMES_BY_TYPE["api"]

    def test_business_capability_references_are_known(self) -> None:
        referenced = {
            a["business_capability"] for a in [*scenario.APPLICATIONS, *scenario.SERVICES]
        } | {a["business_capability"] for a in scenario.APIS}
        assert referenced <= set(scenario.CAPABILITY_AREAS)

    def test_every_entity_is_owned_at_most_once(self) -> None:
        owned_counts: dict[str, int] = {}
        for team in scenario.TEAM_OWNERSHIP:
            for system in team["systems_owned"]:
                key = f"{system['type']}:{system['name']}"
                owned_counts[key] = owned_counts.get(key, 0) + 1
        duplicates = {k: v for k, v in owned_counts.items() if v > 1}
        assert not duplicates, f"Entities owned by more than one team: {duplicates}"


class TestImpliedRelationshipsSatisfyOntologyRules:
    """Every relationship implied by the scenario data must be constructible
    under the ontology's directed endpoint-type rules (ADR-backed in
    DATA_MODEL.md) — a mismatch here means the scenario describes a
    relationship the ontology doesn't actually allow.
    """

    def test_consumes_edges(self) -> None:
        for api in scenario.APIS:
            for consumer in api["consuming_applications"]:
                Consumes.validate_endpoints(_TYPE_TO_LABEL[consumer["type"]], "API")
            if api.get("backend_service"):
                Consumes.validate_endpoints("API", "Service")

    def test_reads_from_and_writes_to_edges(self) -> None:
        for db in scenario.DATABASES:
            for ref in db["readers"]:
                ReadsFrom.validate_endpoints(_TYPE_TO_LABEL[ref["type"]], "Database")
            for ref in db["writers"]:
                WritesTo.validate_endpoints(_TYPE_TO_LABEL[ref["type"]], "Database")

    def test_integrates_with_edges(self) -> None:
        for row in scenario.INTEGRATIONS:
            source_label = _TYPE_TO_LABEL[row["source_system_type"]]
            IntegratesWith.validate_endpoints(source_label, "ExternalSystem")

    def test_owned_by_edges(self) -> None:
        for team in scenario.TEAM_OWNERSHIP:
            for system in team["systems_owned"]:
                OwnedBy.validate_endpoints(_TYPE_TO_LABEL[system["type"]], "Team")

    @pytest.mark.parametrize("source_type", ["application", "service", "api"])
    def test_supports_edges_from_applications_services_and_apis(self, source_type: str) -> None:
        from src.ontology.relationships import Supports

        Supports.validate_endpoints(_TYPE_TO_LABEL[source_type], "BusinessCapability")
