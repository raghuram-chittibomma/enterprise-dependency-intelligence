# Product Brief

Status: accepted

Read by: Product Analyst Agent, Implementation Planner Agent, `github-backlog-creation` skill.

Scenario enterprise: **Meridian Retail Group** (fictional, synthetic-only — see `synthetic-data-design` skill and `docs/00_project/PROJECT_CHARTER.md`).

## Personas

| Persona | Tier | Key question they need answered |
|---|---|---|
| Solution Architect | Primary | "What already exists that touches this domain, before I design something new?" |
| Enterprise Architect | Primary | "What does our application/capability landscape actually look like, and where's the duplication?" |
| Technical Program Manager | Primary | "Which teams do I need in the room before we change this system?" |
| Engineering Lead | Primary | "What breaks if I change or retire this API/database?" |
| SRE / Production Support | Secondary | "This system is down — what else is affected, and who do I page?" |
| Release / Change Manager | Secondary | "What's the test and stakeholder scope for this change?" |
| Data Architect / Engineer | Secondary | "Where does this data come from, and where does it flow to?" |
| Product Manager | Secondary | "Which systems actually implement this business capability?" |

## Use cases (ranked by value)

1. **Dependency Discovery** — "what depends on X?" / "what does X depend on?" (foundational; every other use case builds on this).
2. **Ownership & Stakeholder Discovery** — who owns a system, and who needs to be in a change conversation about it (traversal + `OWNED_BY` rollup).
3. **Change Impact Analysis** — dependency discovery + ownership, composed with a path explanation, before making a change.
4. **Dependency Path Investigation** — the shortest (and alternate) path(s) between two named systems.
5. **Architecture Discovery** — a presentation-oriented view over #1 (landscape browsing rather than a specific question).
6. **Incident Blast-Radius Analysis** — structural blast radius in MVP1 (what's reachable downstream); confirmed-vs-potential-vs-unknown impact maturity comes in MVP2+ once Graph RAG can reason over evidence quality.
7. **Application Retirement / Modernization Assessment** — a capstone view composing #1–#3 to answer "what would break, and who needs to sign off, if we retired this?"

## Functional requirements (MVP1)

Each FR is traceable to an increment todo (this project tracks delivery via the agent's todo list, not GitHub issues, per the `local_only` delivery-tracking decision recorded in `docs/00_project/AI_ORCHESTRATOR_BRIEF.md`).

| ID | Requirement | Increment |
|----|-------------|-------------|
| FR1 | Search for any entity by name (fuzzy match). | increment-6-search |
| FR2 | View entity metadata (type, description, owner, criticality, lifecycle, environment). | increment-7-detail |
| FR3 | View direct upstream and downstream dependencies of an entity. | increment-8-direct-deps |
| FR4 | Traverse upstream/downstream dependencies to a configurable depth. | increment-9-traversal |
| FR5 | View a visual subgraph of a traversal result. | increment-9-traversal |
| FR6 | Find the shortest dependency path between two entities. | increment-10-paths |
| FR7 | View alternate paths between two entities when they exist. | increment-10-paths |
| FR8 | View the owning team of any entity. | increment-11-ownership |
| FR9 | View a rollup of all owning teams across a dependency subtree (stakeholder discovery). | increment-11-ownership |
| FR10 | View business capabilities supported by an entity. | increment-12-capabilities |
| FR11 | Ask one of a defined set of natural-language dependency questions and receive a grounded answer. | increment-13-nlquery |
| FR12 | See the graph evidence (path, relationship types, source system) backing every answer. | increment-14-evidence |
| FR13 | Receive an explicit "not supported" response for out-of-scope questions rather than a fabricated one. | increment-13-nlquery |

### The 7 supported natural-language questions (FR11/FR13 closed template set)

1. What applications/services directly consume Customer API v1?
2. What does Order Service depend on?
3. Who owns applications downstream from Customer API v1?
4. Which business capabilities depend on Order Database?
5. What is the dependency path between Storefront and Customer Database?
6. Which APIs are consumed by Order Management?
7. What applications use Customer Database?

Any question outside this set (or referencing an unresolvable entity) returns an explicit "not supported" / "entity not found" response (FR13) — never a best-effort guess.

## Non-functional requirements

| Category | Requirement |
|---|---|
| AI boundary | Zero LLM calls in the MVP1 critical path (search, detail, traversal, paths, ownership, capabilities, NL query, evidence). All MVP1 answers are produced by deterministic graph queries. |
| Correctness | No fabricated relationships. The NL query layer's answer space is closed and enumerable (the 7 questions above); anything else is an explicit non-answer (FR13). |
| Performance | Sub-second response for traversals up to depth 4 over the ~150–250 node / synthetic-scale MVP1 graph. |
| Idempotency | Ingestion is safe to re-run: re-running the pipeline twice produces zero duplicate nodes/relationships (`MERGE` on natural key). |
| Provenance | Every node and relationship carries `source_system`, `source_record_id`, and (relationships only) `evidence_type` (`documented` \| `inferred`). MVP1 sources only ever write `documented`. |
| Data sensitivity | Synthetic/fictional data only (Meridian Retail Group) — no real company, customer, or personal data, per `synthetic-data-design`. |
| Deployment | Local-first, single dev machine; no cloud dependency, no auth, no multi-tenancy in MVP1. |
| Testing | Automated coverage from day one: ingestion, entity resolution, query templates, and a 100%-pass golden question dataset (see `docs/02_testing/TEST_STRATEGY.md`). |
| Observability | Structured JSON log line per NL query (question, resolved intent, matched entities, latency) written locally — no dashboard in MVP1. |
| Accessibility | Semantic HTML and keyboard-navigable search in the MVP1 UI — not a full WCAG audit. |

## Domain concepts / taxonomy

- **Entity** — any node in the dependency graph: `Application`, `Service`, `API`, `Database`, `DataPipeline`, `Report`, `ExternalSystem`, `Team`, `BusinessCapability`. See `docs/01_architecture/DATA_MODEL.md` for the full ontology.
- **Dependency** — a directed relationship meaning "the source needs the target to function or to be considered complete": `CONSUMES`, `READS_FROM`, `WRITES_TO`, `INTEGRATES_WITH`. Never persisted as a single generic `DEPENDS_ON` edge — always one of the specific typed relationships, computed/traversed as needed.
- **Upstream** — an entity that the entity in question depends on (outbound dependency edges).
- **Downstream** — an entity that depends on the entity in question (inbound dependency edges).
- **Direct dependency** — a dependency reachable in exactly one hop (FR3).
- **Transitive dependency** — a dependency reachable in 2+ hops (FR4).
- **Blast radius** — the set of entities structurally reachable downstream from a given entity, within a bounded depth.
- **Ownership** — the `OWNED_BY` relationship from any entity to the `Team` accountable for it.
- **Business capability** — a named business function (e.g. "Customer Management") that one or more technical entities `SUPPORTS`.
- **Evidence / provenance** — the source system, source record, and (for relationships) documented-vs-inferred status backing a fact in the graph; every UI answer must be traceable to evidence (FR12).
- **Golden question** — one of the 7 fixed NL question templates (or the corresponding golden-dataset scenario) used to evaluate the NL query layer.

## Out of scope (MVP1)

- Any LLM call anywhere in the critical path (deferred to MVP2 — Graph RAG).
- Unstructured document ingestion, vector search, or the `Document` entity (deferred to MVP3 — Hybrid Graph + Document RAG).
- Multi-step agentic investigation (deferred to MVP4).
- Risk scoring, drift detection, what-if analysis, technology rationalization reporting (deferred to MVP5).
- Authentication, authorization, multi-tenancy, cloud deployment.
- `Table` as a graph node (databases carry a `key_tables` property list instead).
- `Technology` and `Environment` as graph nodes (kept as properties on `Application`/`Service`).
- `Owner` as a separate node type (folded into `Team` + `OWNED_BY`).
- Open-ended/free-form natural-language questions outside the 7 supported templates (explicit non-answer per FR13, not a best-effort guess).
- Cardinality enforcement beyond what's documented in `docs/01_architecture/DATA_MODEL.md` (e.g. co-ownership by multiple teams) — MVP1 assumes single ownership; revisit via ADR if real scenarios need otherwise.
