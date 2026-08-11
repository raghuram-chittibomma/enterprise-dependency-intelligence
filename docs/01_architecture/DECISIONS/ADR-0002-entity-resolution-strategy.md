# ADR-0002: Entity resolution strategy

Status: Accepted

## Context

The 5 MVP1 sources reference the same real-world entity inconsistently: the CMDB might key an application by an internal asset ID, while the Integration Catalog or API Catalog references it by name only. Ingestion must resolve these references to a single, stable graph node without creating duplicates, and without silently merging two genuinely different entities that happen to have similar names.

## Decision

Resolve entity identity in a fixed, escalating, fully deterministic order — **no LLM involved**:

1. **Exact natural-key match**: if the record carries the same identifying field(s) used to construct another entity's `id` (see `docs/01_architecture/DATA_MODEL.md`'s Identity strategy — `<type_prefix>:<source_system>:<normalized_source_record_id>`), resolve to that existing node.
2. **Normalized exact match**: if no exact natural-key match exists, normalize the candidate name (lowercase, strip whitespace/punctuation, expand known abbreviations from a small static lookup table) and compare against normalized names of existing nodes of the expected type.
3. **Fuzzy match via `rapidfuzz`**: if no normalized exact match exists, compute similarity scores against existing node names of the expected type; resolve automatically only above a high-confidence threshold (initial value: 90/100 token-sort ratio), tuned during increment-4 against the synthetic dataset.
4. **Unresolved queue**: anything that clears none of the above is written to a local unresolved-entity queue (file under `data/`) for inspection — never auto-created as a new node and never silently dropped.

## Consequences

- **Easier**: fully deterministic and debuggable — every resolution decision can be traced to which of the 4 steps fired and why, with no model non-determinism to account for.
- **Easier**: keeps entity resolution testable with exact-match pytest cases (per `docs/02_testing/TEST_STRATEGY.md`) instead of needing eval-style scoring.
- **Harder**: the fuzzy-match threshold is a manually tuned constant that may need revisiting as the synthetic dataset grows; a threshold that's too loose risks merging distinct entities, too strict risks flooding the unresolved queue.
- **Rejected: LLM-based entity resolution** — would introduce non-determinism and a dependency the MVP1 scope explicitly excludes (zero LLM calls in the MVP1 critical path). Revisit only if `rapidfuzz` proves insufficient at a scale well beyond the ~30–40 seed entities.
- **Rejected: embedding-based similarity** — more setup (embedding model, vector comparison) than the problem currently warrants at MVP1's scale; `entity_resolver` is a named extension point (`src/ingestion/resolution.py`) specifically so this can be swapped in later without touching the loader.
