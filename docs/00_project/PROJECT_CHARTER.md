# Project Charter

Status: accepted

Read by: Product Analyst Agent.

## Problem statement

Large enterprises operate hundreds of applications, APIs, services, databases, pipelines, and reports. Information about how these systems depend on each other is fragmented across CMDB/ServiceNow, API catalogs, source code, data catalogs, spreadsheets, and tribal knowledge held by architects and engineers. No single system holds the full dependency picture, so questions like "what depends on this API?" or "what could break if we retire this database?" require manual investigation across many systems and people. This project builds **Enterprise Dependency Intelligence**: an application that connects fragmented enterprise technology information into a knowledge graph, so architects, TPMs, and engineers can discover dependencies, assess change/incident impact, and identify ownership with evidence rather than tribal knowledge.

## Goals

- Deliver a genuinely usable Enterprise Dependency Explorer at the end of MVP1 — search, entity detail, upstream/downstream traversal, path finding, ownership lookup, and a bounded set of natural-language questions, all grounded in graph evidence.
- Demonstrate that structured graph querying alone (no LLM) already delivers real value before any AI capability is introduced.
- Build an ontology and architecture that can grow into Graph RAG, hybrid document RAG, and bounded agentic investigation without requiring a rebuild.
- Never let the system state a dependency that isn't backed by a graph path with a traceable source.
- Use the Enterprise SDLC MCP's agents/skills as the governing delivery process rather than ad hoc development.

## Non-goals (for MVP1)

- No LLM call anywhere in the MVP1 critical path.
- No unstructured risk scoring, drift detection, or what-if analysis (deferred to MVP5).
- No authentication, multi-tenancy, or cloud deployment.
- No table-level graph nodes, or Technology/Environment as graph nodes (kept as properties — see `docs/01_architecture/DATA_MODEL.md`).

## Stakeholders

| Role | Name/Team | Interest |
|------|-----------|----------|
| Product owner / final decision maker | Repo owner (you) | Approves scope, ontology, and architecture decisions |
| Solution Architect (primary persona) | N/A — represented persona | Pre-design dependency discovery |
| Enterprise Architect (primary persona) | N/A — represented persona | Landscape/capability mapping, rationalization |
| Technical Program Manager (primary persona) | N/A — represented persona | Cross-team risk, stakeholder identification |
| Engineering Lead (primary persona) | N/A — represented persona | Blast radius before changing a shared API/DB |

## Success criteria

- 100% of the MVP1 golden question dataset (`evals/`) passes — every supported question type returns the expected entities/relationships/paths.
- All 13 functional requirements (FR1-FR13, see `PRODUCT_BRIEF.md`) are implemented and demoable end-to-end through the UI.
- Ingestion is idempotent: re-running it twice produces zero duplicate nodes/relationships.
- Every relationship surfaced in the UI carries a source system and evidence type.
- `validate_manifest` reports no missing core keys throughout development.

## Constraints

- Local-first development; no cloud dependency for MVP1.
- Graph store runs as a Docker container on a remote LAN Docker host (`192.168.4.52`), accessed via `DOCKER_HOST=tcp://192.168.4.52:2375` from the dev machine — see `docs/03_operations/RUNBOOK.md`.
- Python 3.11+ (3.14 in local dev) for all backend/ingestion/graph code.
- Synthetic data only — no real company or customer data (enforced by the `synthetic-data-design` skill).
