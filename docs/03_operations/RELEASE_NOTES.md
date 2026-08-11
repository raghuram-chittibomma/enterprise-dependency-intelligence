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

### Changed

### Fixed

### Upgraded

<!-- Dependency/runtime upgrades handled by the Dependency Upgrade Agent go here. -->
