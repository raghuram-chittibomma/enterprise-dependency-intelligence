# Release Notes

Status: draft

Read by: Release Manager Agent, `release-readiness-review` skill, `dependency-upgrade-agent`.

Newest entry first. One entry per release/milestone.

## [Unreleased]

### Added

- **MVP3 Hybrid Graph + Document RAG (FR17–FR19, ADR-0006):** `Document` + `DOCUMENTED_BY`, synthetic Meridian architecture docs, local SQLite vector index (`src/retrieval/`), and open-ended Ask fusion of subgraph + top-k chunks when `HYBRID_DOC_RAG_ENABLED=true`. Citations may be graph edges and/or document chunk ids; unsupported claims refuse.
- **MVP2 Graph RAG (FR14–FR16, ADR-0005):** open-ended Ask over a deterministically retrieved dependency subgraph with OpenAI-backed grounded generation (`LLMAnswerGenerator`). Closed 7-question templates remain fully deterministic. Opt-in via `GRAPH_RAG_ENABLED` + `OPENAI_API_KEY`. Citations are filtered to the retrieved subgraph; unanswered / fabricated citations become `insufficient_evidence`.
- Open-ended retrieval (`src/nlquery/graphrag.py`), config helpers, Ask routing, homepage hint, faithfulness/refusal evals (`evals/test_mvp2_graphrag.py`, `evals/test_mvp3_hybrid.py`) and fake-LLM / fake-embedder unit tests.

### Changed

- Docs: ARCHITECTURE, DATA_MODEL (10 nodes / 8 relationships), PRODUCT_BRIEF, EVAL_STRATEGY, RUNBOOK updated for MVP2/MVP3 boundaries.
- Ontology expands to `Document` / `DOCUMENTED_BY`; datagen writes `data/sample/docs/`.

### Fixed

### Upgraded

- `openai>=1.40,<2` used for Graph RAG generation and `text-embedding-3-small` embeddings.

<!-- Dependency/runtime upgrades handled by the Dependency Upgrade Agent go here. -->

## [MVP1] - 2026-08-12

Knowledge Graph and Dependency Explorer — first usable release. Zero LLM calls
in the critical path; every answer is a deterministic graph query with
ADR-0003 provenance.

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
- **FR8/FR9 ownership and stakeholder rollup**: `get_owning_team` (a standalone FR8 primitive alongside FR2's inline owner lookup) and `get_ownership_rollup` (FR9) — every distinct owning team across an entity's dependency subtree, reusing the same bounded `get_dependency_traversal` as FR4/FR5, grouped by team (with an explicit "no owning team recorded" bucket for ownership gaps) and including the root entity's own team. Added to the entity detail page as a "Stakeholder rollup" section with direction/depth controls, defaulting to downstream — "who do I need in the room before I change this system" (the TPM persona). Answers golden question 3 ("Who owns applications downstream from Customer API v1?").
- **FR10 business capability view**: `get_direct_capabilities` (the entity's own `SUPPORTS` edges) and `get_capability_rollup` (the same bounded subtree traversal as FR9, but grouped by `BusinessCapability` instead of owning team) — the latter is what makes "which capabilities depend on X" answerable for node types (`Database`, `DataPipeline`, ...) that never `SUPPORTS` a capability directly, by rolling up what their dependents support. Added to the entity detail page as a "Business capabilities" section (direct list plus a direction/depth-controlled rollup). Answers golden question 4 ("Which business capabilities depend on Order Database?").
- **FR11/FR13 deterministic NL query layer** (`src/nlquery/`): keyword/regex intent classification for the 7 fixed question shapes, `rapidfuzz` entity resolution reusing FR1 search with a stricter confidence bar (and question-type label filters so e.g. "Order Management" the Application wins over the same-named BusinessCapability for "APIs consumed by …"), dispatch to the same FR1–FR10 query templates, fixed-template answers, and explicit non-answers for unsupported / not-found / ambiguous questions. Homepage Ask box posts to `/ask`; structured JSON log lines go to `data/nlquery.log`.
- **FR12 evidence/provenance panel**: dependency lists, path chains, and NL answer evidence carry `source_system` / `source_record_id` / `evidence_type` from the same relationship row that produced the claim (ADR-0003). Entity detail adds an Evidence section via `get_entity_evidence` listing every inbound/outbound relationship with provenance.
- **Golden dataset** (`evals/`): 7 NL golden questions plus representative FR1–FR4/FR6/FR8–FR13 scenarios against the fully ingested Meridian graph (45 nodes / 101 relationships). Required 100% pass gate for this release.

### Changed

### Fixed

- NL entity resolution for golden question 6: same-name Application vs BusinessCapability collision ("Order Management") no longer forces an FR13 ambiguous non-answer; `consumed_by` (and related question types) restrict candidates to labels that can participate in the question's relationship shape.

### Upgraded
