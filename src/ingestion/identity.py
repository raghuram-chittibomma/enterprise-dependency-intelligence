"""Stable natural-key `id` construction. See `docs/01_architecture/DATA_MODEL.md`'s
Identity strategy: `<type_prefix>:<source_system>:<normalized_source_record_id>`.
This is what makes re-ingesting the same source record always resolve to the
same node id -- the actual mechanism behind ingestion idempotency.
"""

from __future__ import annotations

import re

TYPE_PREFIXES: dict[str, str] = {
    "Application": "app",
    "Service": "svc",
    "API": "api",
    "Database": "db",
    "DataPipeline": "pipeline",
    "Report": "report",
    "ExternalSystem": "ext",
    "Team": "team",
    "BusinessCapability": "cap",
}


def _normalize_record_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "unknown"


def make_id(label: str, source_system: str, source_record_id: str) -> str:
    if label not in TYPE_PREFIXES:
        raise ValueError(f"Unknown label {label!r}; expected one of {sorted(TYPE_PREFIXES)}")
    prefix = TYPE_PREFIXES[label]
    normalized = _normalize_record_id(source_record_id)
    return f"{prefix}:{source_system}:{normalized}"
