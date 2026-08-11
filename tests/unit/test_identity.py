from __future__ import annotations

import pytest

from src.ingestion.identity import make_id


class TestMakeId:
    def test_is_deterministic(self) -> None:
        first = make_id("Application", "cmdb", "APP-001")
        second = make_id("Application", "cmdb", "APP-001")
        assert first == second

    def test_normalizes_the_record_id(self) -> None:
        assert make_id("Application", "cmdb", "APP-001") == "app:cmdb:app-001"
        assert make_id("Team", "team-ownership", "Commerce Platform Team") == (
            "team:team-ownership:commerce-platform-team"
        )

    def test_different_labels_or_sources_never_collide(self) -> None:
        a = make_id("Application", "cmdb", "1")
        b = make_id("Service", "cmdb", "1")
        c = make_id("Application", "other-source", "1")
        assert len({a, b, c}) == 3

    def test_rejects_unknown_label(self) -> None:
        with pytest.raises(ValueError, match="Unknown label"):
            make_id("NotARealLabel", "cmdb", "1")
