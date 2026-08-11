from __future__ import annotations

from src.ingestion.resolution import EntityResolver


class TestEntityResolver:
    def test_exact_match_after_register(self) -> None:
        resolver = EntityResolver()
        resolver.register("service", "Order Service", "svc:cmdb:svc-001")
        resolved = resolver.resolve(
            "service", "Order Service", referenced_by_source="test", referenced_by_record_id="1"
        )
        assert resolved == "svc:cmdb:svc-001"
        assert resolver.unresolved == []

    def test_normalized_exact_match_ignores_case_and_punctuation(self) -> None:
        resolver = EntityResolver()
        resolver.register("service", "Order Service", "svc:cmdb:svc-001")
        resolved = resolver.resolve(
            "service", "order   service", referenced_by_source="test", referenced_by_record_id="1"
        )
        assert resolved == "svc:cmdb:svc-001"

    def test_fuzzy_match_above_threshold(self) -> None:
        resolver = EntityResolver()
        resolver.register("service", "Order Service", "svc:cmdb:svc-001")
        resolved = resolver.resolve(
            "service", "Order Servce", referenced_by_source="test", referenced_by_record_id="1"
        )  # typo
        assert resolved == "svc:cmdb:svc-001"
        assert resolver.unresolved == []

    def test_no_match_below_threshold_is_queued_unresolved(self) -> None:
        resolver = EntityResolver()
        resolver.register("service", "Order Service", "svc:cmdb:svc-001")
        resolved = resolver.resolve(
            "service",
            "Completely Different Thing",
            referenced_by_source="test-source",
            referenced_by_record_id="42",
        )
        assert resolved is None
        assert len(resolver.unresolved) == 1
        entry = resolver.unresolved[0]
        assert entry.name == "Completely Different Thing"
        assert entry.entity_type == "service"
        assert entry.referenced_by_source == "test-source"
        assert entry.referenced_by_record_id == "42"

    def test_wrong_entity_type_does_not_match(self) -> None:
        resolver = EntityResolver()
        resolver.register("service", "Order Service", "svc:cmdb:svc-001")
        resolved = resolver.resolve(
            "application", "Order Service", referenced_by_source="test", referenced_by_record_id="1"
        )
        assert resolved is None

    def test_lookup_exact_never_queues_unresolved(self) -> None:
        resolver = EntityResolver()
        assert resolver.lookup_exact("business_capability", "Nonexistent") is None
        assert resolver.unresolved == []

    def test_resolve_any_tries_every_candidate_type(self) -> None:
        resolver = EntityResolver()
        resolver.register("api", "Customer API v1", "api:api-catalog:api-001")
        result = resolver.resolve_any(
            ("application", "api"),
            "Customer API v1",
            referenced_by_source="test",
            referenced_by_record_id="1",
        )
        assert result == ("api", "api:api-catalog:api-001")
        assert resolver.unresolved == []

    def test_resolve_any_records_exactly_one_unresolved_entry_on_total_miss(self) -> None:
        resolver = EntityResolver()
        resolver.register("application", "Storefront", "app:cmdb:app-001")
        result = resolver.resolve_any(
            ("application", "api"),
            "Nonexistent Thing",
            referenced_by_source="test",
            referenced_by_record_id="1",
        )
        assert result is None
        assert len(resolver.unresolved) == 1
