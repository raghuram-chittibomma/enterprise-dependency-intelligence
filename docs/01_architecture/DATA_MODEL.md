# Data Model

Status: accepted

Read by: Solution Architect Agent, Implementation Planner Agent, Code Reviewer Agent, `requirement-tightening` skill, `knowledge-graph-modeling-review` skill, `graph-rag-retrieval-review` skill (from MVP2), and stack-specific data skills (`synthetic-data-design`).

This is a **property graph** ontology (nodes + typed, directed relationships), not a relational schema. See `docs/01_architecture/DECISIONS/ADR-0001-graph-store-selection.md` for the store choice and `ADR-0002-entity-resolution-strategy.md` / `ADR-0003-provenance-model.md` for identity and provenance.

## Common properties

Every node carries: `id` (stable natural key — see Identity below), `name`, `description`, `lifecycle_status` (e.g. `active`, `deprecated`, `retired`, `planned`), `criticality` (where applicable — e.g. `low`/`medium`/`high`/`critical`), `source_system`, `source_record_id`, `ingested_at`.

Every relationship carries: `source_system`, `source_record_id`, `evidence_type` (`documented` | `inferred` — MVP1 ingestion only ever writes `documented`; `inferred` is reserved for MVP2+ Graph RAG-derived edges).

## Entities (10 node types)

| Entity | Description | Key fields (beyond common properties) |
|--------|-------------|------------|
| `Application` | An enterprise application (e.g. "Storefront", "Order Management"). | `technology` (property, not a node), `environment` (property, not a node) |
| `Service` | An internal backend/microservice. | `technology`, `environment` |
| `API` | A versioned API contract exposed by an application/service. | `version` (e.g. `v1`), `protocol` (e.g. `REST`, `SOAP`), `implementing_application` (display-only property naming the app that implements it — **not** a relationship; see Relationships note below) |
| `Database` | A database instance. | `engine` (e.g. `PostgreSQL`, `SQL Server`), `key_tables` (list of table names — tables are **not** graph nodes in MVP1) |
| `DataPipeline` | An ETL job or scheduled batch process (merges the earlier "BatchJob" concept — one node type, distinguished by property). | `pipeline_type` (`etl` \| `batch_job`), `schedule` (e.g. cron-style description) |
| `Report` | A BI dashboard or scheduled report artifact. | `audience` (e.g. `internal-ops`, `executive`), `refresh_frequency` (e.g. `daily`, `on-demand`) — **decided now** (not fully specified in the original planning discussion); revisit if real usage needs more |
| `ExternalSystem` | A third-party/SaaS system outside the enterprise boundary (payment gateway, external CRM, etc.). | `vendor`, `category` (e.g. `payment-gateway`, `saas-crm`) — **decided now** (not fully specified in the original planning discussion); revisit if real usage needs more |
| `Team` | An owning/support team. | `business_area` (e.g. "Commerce", "Data Platform") |
| `BusinessCapability` | A named business function (e.g. "Customer Management", "Product Catalog"). | `capability_area` (grouping, e.g. "Customer", "Commerce", "Fulfillment") |
| `Document` | An unstructured architecture / design note (MVP3 Hybrid Doc RAG — synthetic Meridian markdown under `data/sample/docs/`). | `path` (relative path in the corpus), `doc_type` (e.g. `architecture_note`) |

**Explicitly not modeled as nodes** (documented decision, not an oversight): `Table` (property of `Database`), `BatchJob` (merged into `DataPipeline`), `Owner` (folded into `Team` + `OWNED_BY`), `Technology` (property of `Application`/`Service`), `Environment` (property of `Application`/`Service`). Chunks of a `Document` are **not** graph nodes — they live in the local SQLite vector store (`ADR-0006`).

### Identity strategy

Every node's `id` is a **stable natural key** derived deterministically from its source record — never an opaque auto-increment. Format: `<type_prefix>:<source_system>:<normalized_source_record_id>` (e.g. `app:cmdb:storefront-001`, `api:api-catalog:customer-api-v1`). This makes ingestion idempotent by construction: re-ingesting the same source record always resolves to the same node `id`, so `MERGE` never creates a duplicate. See `ADR-0002-entity-resolution-strategy.md` for how records that don't share an exact natural key (e.g. an API referenced by name only in the Integration Catalog, without the API Catalog's own ID) get resolved to the same node.

## Relationships (8 types)

| Relationship | Direction (source → target) | Cardinality | Meaning |
|---|---|---|---|
| `CONSUMES` | `(Application \| Service \| API) → (Service \| API)` | Many-to-many | Synchronous functional dependency — the source calls the target to do its job. An API acting as a facade may itself `CONSUMES` a backend `Service`. |
| `READS_FROM` | `(Application \| Service \| API \| DataPipeline \| Report) → (Database \| API \| DataPipeline)` | Many-to-many | The source reads data from the target. |
| `WRITES_TO` | `(Application \| Service \| API \| DataPipeline) → (Database \| DataPipeline)` | Many-to-many | The source writes data to the target. |
| `INTEGRATES_WITH` | `(Application \| Service) → (ExternalSystem)` | Many-to-many | The source integrates with a third-party/SaaS system (carries `integration_type`, `protocol`, `frequency` from the Integration Catalog source). |
| `SUPPORTS` | `(Application \| Service \| API) → (BusinessCapability)` | Many-to-many | The source technical entity implements/supports the business capability. |
| `OWNED_BY` | `(any entity type) → (Team)` | **Many-to-one for MVP1** (decided now: each entity has exactly one owning team) | The team accountable for the source entity. Revisit via ADR if co-ownership scenarios appear in real data. |
| `REPLACED_BY` | `(Application \| API) → (Application \| API)` | **One-to-one for MVP1** (decided now: one successor per entity) | Lifecycle/migration edge — the source is being retired in favor of the target. Revisit via ADR if a split-into-multiple-successors scenario appears. |
| `DOCUMENTED_BY` | `Document → (Application \| Service \| API \| Database \| DataPipeline \| Report \| ExternalSystem \| BusinessCapability)` | Many-to-many | The source document describes / documents the target entity (`ADR-0006`). Direction is Document → entity (not the colloquial "entity is documented by"). |

**`DEPENDS_ON` is intentionally never persisted.** "What does X depend on" is answered at query time by traversing the outbound `CONSUMES` / `READS_FROM` / `WRITES_TO` / `INTEGRATES_WITH` edges — a persisted generic `DEPENDS_ON` edge would duplicate information already in the typed edges and could drift out of sync with them (see `knowledge-graph-modeling-review` skill).

**Explicitly not modeled as relationships**: `HOSTS`, `RUNS_ON` (infra-hosting detail, out of MVP1 scope), `CALLS` (collapsed into `CONSUMES` — a separate "calls" edge would only restate what `CONSUMES` already encodes). An API's "implementing application" is a **display-only property on `API`**, not a relationship — it's provided by the API Catalog source directly and isn't itself traversed by any FR.

## Storage

All nodes and relationships live in a single Neo4j Community Edition graph (database `neo4j`, default) — see `ADR-0001-graph-store-selection.md`. Node labels match the entity type names above 1:1 (`:Application`, `:Service`, `:API`, `:Database`, `:DataPipeline`, `:Report`, `:ExternalSystem`, `:Team`, `:BusinessCapability`, `:Document`). Relationship types match the relationship names above 1:1. A uniqueness constraint on `id` per label is created during graph bootstrap (increment-3) to make `MERGE`-based ingestion safe.

Document **chunks and embeddings** for Hybrid Doc RAG live in a separate local SQLite store under `data/vectors/` (`ADR-0006`) — not in Neo4j vector indexes for MVP3 v1. The unresolved-entity queue from entity-resolution (`ADR-0002`) is persisted as a local JSON/SQLite file under `data/` for inspection — not in the graph itself, since an unresolved reference is not yet a fact about the enterprise.

## Data lifecycle

- **Source of truth**: the synthetic Meridian source datasets under `data/sample/` (CMDB, API Catalog, DB Metadata, Team Ownership, Integration Catalog, plus MVP3 architecture docs under `data/sample/docs/`) are the system of record. The graph (and the local vector index) are derived, rebuildable projections of them.
- **Retention**: no retention policy needed — synthetic data only, regenerable at will. No PII, no real company data (enforced by `synthetic-data-design`).
- **Re-ingestion**: the ingestion pipeline (increment-4) is idempotent and safe to re-run at any time; re-running after a source dataset changes updates existing nodes/relationships in place via `MERGE` on natural key rather than duplicating them.
- **Deletion / reconciliation**: After upsert, ingestion diffs the graph against the current source parse set and **reports** stale nodes/relationships (`ADR-0009`, FR28). Hard-delete apply is not enabled in v1 (no flag). Soft tombstones are out of scope. Vector chunks are not reconciled in this pass.
