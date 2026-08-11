# ADR-0003: Universal provenance model

Status: Accepted

## Context

The product's core trust promise is that every dependency claim traces back to real evidence (FR12) — never a fabricated or unverifiable relationship. This has to be true structurally, not just as an aspiration, or it can't be enforced or tested.

## Decision

Every node and every relationship in the graph carries provenance fields, populated at ingestion time and never left optional:

- **Nodes**: `source_system` (which of the 5 sources produced this record), `source_record_id` (the identifying value from that source, pre-normalization), `ingested_at` (timestamp).
- **Relationships**: `source_system`, `source_record_id`, and `evidence_type` — either `documented` (explicitly stated by a source record, e.g. the API Catalog explicitly lists a consuming application) or `inferred` (derived rather than explicitly stated). **MVP1 ingestion only ever writes `documented`** — no MVP1 code path infers a relationship; `inferred` is reserved for MVP2+ Graph RAG-derived edges, so its presence in the schema now avoids a breaking schema change later.

Every FR12 evidence panel and every NL query answer (FR11) reads these fields directly from the query result that produced the answer — provenance is never re-derived or looked up separately after the fact, which would risk it drifting from what was actually matched.

## Consequences

- **Easier**: "show your evidence" (FR12) is a straightforward projection of fields already on the matched nodes/relationships, not a separate subsystem to build or keep in sync.
- **Easier**: data-quality checks (increment-5) can assert "no node/relationship is missing provenance fields" as a hard invariant, catching an ingestion bug immediately rather than surfacing as a confusing UI gap later.
- **Harder**: every new source parser (`SourceParser` extension point) must populate these fields correctly from day one — there's no generic default that makes sense, since provenance is inherently source-specific.
- **Sets up MVP2 cleanly**: the `documented`/`inferred` distinction already exists in the schema before Graph RAG needs it, so MVP2 doesn't need a migration to add it retroactively — it can start writing `inferred` edges (with citation back to *which* MVP1 documented edges + retrieval step produced the inference) without changing MVP1 data.
