# ADR-0008: Advanced Enterprise Intelligence (MVP5)

Status: Accepted

## Context

MVP1–4 provide search, traversal, ownership/capability rollups, closed and
open-ended Ask, Hybrid Doc RAG, and bounded Investigate (`ADR-0004`–
`ADR-0007`). Personas still need **numeric change risk**, **retirement
what-if**, **catalog/graph drift signals**, and **technology
rationalization** views. Letting an LLM invent risk numbers or mutate the
graph for scenarios would break FR12 faithfulness.

## Decision

For MVP5 Advanced Enterprise Intelligence:

1. **All four pillars** ship in v1: risk scoring (FR23), what-if retirement
   simulation (FR24), drift signals (FR25), technology/engine
   rationalization (FR26).
2. **Deterministic compute**: scores, simulations, drift lists, and
   rationalization buckets are pure functions over existing
   `src/graph/queries.py` primitives, node properties, evidence edges
   (`REPLACED_BY`), and the ingestion unresolved queue. No Text2Cypher.
3. **What-if is non-mutating**: retirement impact is a bounded downstream
   (and upstream) traversal + rollups. Hypothetical edges are never written
   to Neo4j.
4. **Optional narrative**: `INTELLIGENCE_NARRATIVE_ENABLED` (default false)
   may call an LLM to explain factor lists; the model must cite factor ids
   present in the payload and must **not** invent scores. Requires
   `OPENAI_API_KEY`. Core intelligence works with the flag off.
5. **UI entry**: Intelligence hub + entity-detail risk/what-if panels.
   Closed Ask templates and Investigate remain unchanged in MVP5 v1.
6. **Score constants**: tunable module constants in `src/intelligence/`
   (documented below), not a large env surface.

### Risk formula constants (v1)

| Factor id | Points (capped) | Signal |
|-----------|-----------------|--------|
| `criticality` | critical 25 / high 18 / medium 10 / low 4 | entity `criticality` |
| `lifecycle` | deprecated 15 / retired 12 / planned 5 | entity `lifecycle_status` |
| `blast_radius` | min(20, (downstream nodes − 1) × 2) | FR4 downstream traversal |
| `fan_in` | min(15, inbound direct deps × 3) | FR3 downstream edges |
| `ownership_gap` | seed missing owner 10; else min(15, floor(unowned% × 15)) | FR8/FR9 |
| `capability_exposure` | min(15, capability rollup groups × 3) | FR10 rollup |

Score = min(100, sum). Bands: 0–24 `low`, 25–49 `medium`, 50–74 `high`,
75–100 `critical`.

### Drift signal families (v1)

1. Lifecycle: `deprecated`/`retired` with inbound dependency consumers.
2. Replacement: outbound `REPLACED_BY` while inbound dependency consumers remain.
3. Resolution: open rows in `data/unresolved/unresolved.json`.

## Consequences

- **Easier**: unit-testable scores and drift without network or LLM.
- **Easier**: Ask/Investigate regression surface stays small.
- **Harder**: formula tuning may need revisiting as Meridian data grows —
  constants live in one module for that reason.
- **Rejected: mutating what-if / scenario history** — deferred.
- **Rejected: full delete-on-source-removal reconciliation** — deferred;
  resolution-queue drift is the v1 catalog consistency signal.
- **Rejected: Technology/Environment as graph nodes** — stay properties
  (`DATA_MODEL.md`).
