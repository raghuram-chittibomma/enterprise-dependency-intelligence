# Release Notes

Status: draft

Read by: Release Manager Agent, `release-readiness-review` skill, `dependency-upgrade-agent`.

Newest entry first. One entry per release/milestone.

## [Unreleased]

### Added

- Project initiation docs finalized: `PROJECT_CHARTER.md`, `PRODUCT_BRIEF.md` (FR1–FR13, personas, use cases), `AI_ORCHESTRATOR_BRIEF.md`, `ARCHITECTURE.md`, `DATA_MODEL.md` (9 entity / 7 relationship ontology), and ADR-0001 through ADR-0004 (graph store, entity resolution, provenance, deterministic NL query layer).
- Two new Enterprise SDLC MCP catalog skills upstreamed: `knowledge-graph-modeling-review`, `graph-rag-retrieval-review` (catalog v0.8.0).
- Ontology (`src/ontology/`): Pydantic models for the 9 entity / 7 relationship types, with relationship endpoint-type validation and a type registry.
- Synthetic dataset (`src/datagen/`): the "Meridian Retail Group" scenario and 5 MVP1 source-file generators (CMDB, API catalog, DB metadata, team ownership, integration catalog).
- Graph store (`src/graph/`): `GraphStore` protocol with Neo4j (primary, via Docker) and NetworkX+SQLite (fallback) implementations, plus a CLI health check (`src/graph/healthcheck.py`).
- Ingestion pipeline (`src/ingestion/`): two-phase (nodes, then relationships) ingestion across all 5 sources, with natural-key ID generation, deterministic entity resolution (exact → normalized → fuzzy), and an unresolved-reference queue. CLI at `src/ingestion/run.py`.
- Data quality checks (`src/quality/`): automated graph invariants (no duplicate natural keys, no duplicate names per label, referential consistency, no orphan nodes, required provenance fields) as both a pure-function library and a CLI (`src/quality/run.py`) that exits non-zero on error-severity issues. The freshly ingested golden dataset (45 nodes, 101 relationships) passes with zero issues.
- **FR1 entity search**, and with it the first usable slice of the app: a FastAPI + Jinja2 + HTMX web UI (`src/api/`, `src/web/`) at `/`, backed by a word-alignment-aware fuzzy search (`src/graph/queries.py::search_entities`) tuned against the real dataset to tolerate typos and word reordering without false-positiving on unrelated multi-word names.
- **FR2 entity detail page** (`/entities/{id}`): full metadata (type, description, criticality, lifecycle, owning team, and every type-specific property) for any of the 9 node types, with the owning team itself linking back into the same detail view. Search results now link through to it.
- **FR3 direct dependencies**, added to the same detail page: "Depends on" (upstream) and "Depended on by" (downstream) lists, restricted to the 4 relationship types that represent an actual functional dependency (`CONSUMES`/`READS_FROM`/`WRITES_TO`/`INTEGRATES_WITH`), each entry linking onward and labeled with its relationship type.
- **FR4/FR5 upstream/downstream traversal with subgraph visualization**: a bounded BFS (`src/graph/queries.py::get_dependency_traversal`, depth 1–5, default 2) over the same dependency relationship types as FR3, in either direction, returning every reached node plus every dependency edge between two reached nodes (real cross-links, not just the BFS tree). Exposed as JSON at `/entities/{id}/graph` and rendered on the entity detail page as an interactive Cytoscape.js subgraph with direction and depth controls (`src/web/static/js/graph.js`).
- **FR6/FR7 dependency path explorer**: `src/graph/queries.py::get_dependency_paths` finds the shortest dependency path between two entities plus up to 3 distinct alternates no more than 2 hops longer, treating dependency edges as undirected for connectivity (a path can legitimately step downstream then upstream) while preserving each edge's real direction for display. Bounded DFS enumeration (max 8 hops, 200 explored paths) keeps it safe on denser future graphs. Added to the entity detail page as a two-step HTMX flow: search for the other entity, then render the computed path(s) as a chain of linked entity chips with relationship-type arrows. Answers golden question 5 ("What is the dependency path between Storefront and Customer Database?").

### Changed

### Fixed

### Upgraded

<!-- Dependency/runtime upgrades handled by the Dependency Upgrade Agent go here. -->
