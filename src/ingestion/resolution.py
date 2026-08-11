"""Entity resolution for name-only cross-source references (ADR-0002).

Every MVP1 source that isn't the one that *originates* an entity (CMDB for
Application/Service/DataPipeline/Report, API Catalog for API, DB Metadata for
Database, Team Ownership for Team) refers to that entity by **name only** --
e.g. the API Catalog's `consuming_applications`, DB Metadata's
`readers`/`writers`, Team Ownership's `systems_owned`, and the Integration
Catalog's `source_system_name`. This module resolves those name references
back to the stable `id` assigned when the entity was created, in escalating,
fully deterministic steps -- no LLM involved:

1. Exact normalized-name match against the registry for that entity type.
2. `rapidfuzz`-based fuzzy match above a high-confidence threshold.
3. Unresolved queue -- never silently dropped, never auto-created as a new
   node.

(True step-1 "exact natural-key" matching, in the ADR-0002 sense, instead
happens implicitly whenever the *same* record is re-ingested: `identity.py`'s
`make_id()` is deterministic, so re-ingestion always produces the same `id`
without going through this resolver at all.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

DEFAULT_FUZZY_THRESHOLD = 90.0


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.strip().lower()).strip()


@dataclass
class UnresolvedReference:
    name: str
    entity_type: str
    referenced_by_source: str
    referenced_by_record_id: str


@dataclass
class EntityResolver:
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD
    # entity_type -> {normalized_name: id}
    _registry: dict[str, dict[str, str]] = field(default_factory=dict)
    unresolved: list[UnresolvedReference] = field(default_factory=list)

    def register(self, entity_type: str, name: str, id_: str) -> None:
        """Record that `name` (of `entity_type`) resolves to `id_` -- called
        once, right after a node is created from its originating source.
        """
        self._registry.setdefault(entity_type, {})[normalize_name(name)] = id_

    def lookup_exact(self, entity_type: str, name: str) -> str | None:
        """Normalized-exact lookup only, with no fuzzy fallback and no
        unresolved-queue side effect -- used when *creating* a derived node
        (e.g. BusinessCapability, ExternalSystem) to check whether it
        already exists, not when resolving a dependency reference.
        """
        return self._registry.get(entity_type, {}).get(normalize_name(name))

    def resolve(
        self,
        entity_type: str,
        name: str,
        *,
        referenced_by_source: str,
        referenced_by_record_id: str,
    ) -> str | None:
        """Resolve a name reference to an id, escalating through the steps
        described in this module's docstring. Returns `None` (and records an
        `UnresolvedReference`) if nothing clears the fuzzy threshold.
        """
        normalized = normalize_name(name)
        registry = self._registry.get(entity_type, {})

        exact = registry.get(normalized)
        if exact is not None:
            return exact

        if registry:
            match = process.extractOne(
                normalized,
                registry.keys(),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=self.fuzzy_threshold,
            )
            if match is not None:
                matched_name, _score, _index = match
                return registry[matched_name]

        self.unresolved.append(
            UnresolvedReference(
                name=name,
                entity_type=entity_type,
                referenced_by_source=referenced_by_source,
                referenced_by_record_id=referenced_by_record_id,
            )
        )
        return None

    def resolve_any(
        self,
        entity_types: tuple[str, ...],
        name: str,
        *,
        referenced_by_source: str,
        referenced_by_record_id: str,
    ) -> tuple[str, str] | None:
        """Like `resolve()`, but for a reference whose entity type isn't
        known up front (e.g. `REPLACED_BY`'s target, which may be an
        Application or an API) -- tries every candidate type and only
        records a single unresolved entry if none of them match.
        """
        normalized = normalize_name(name)

        for entity_type in entity_types:
            exact = self._registry.get(entity_type, {}).get(normalized)
            if exact is not None:
                return entity_type, exact

        best: tuple[str, str, float] | None = None
        for entity_type in entity_types:
            registry = self._registry.get(entity_type, {})
            if not registry:
                continue
            match = process.extractOne(
                normalized,
                registry.keys(),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=self.fuzzy_threshold,
            )
            if match is not None:
                matched_name, score, _index = match
                if best is None or score > best[2]:
                    best = (entity_type, registry[matched_name], score)
        if best is not None:
            return best[0], best[1]

        self.unresolved.append(
            UnresolvedReference(
                name=name,
                entity_type="|".join(entity_types),
                referenced_by_source=referenced_by_source,
                referenced_by_record_id=referenced_by_record_id,
            )
        )
        return None
