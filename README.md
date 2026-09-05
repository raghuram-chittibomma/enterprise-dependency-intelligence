# Enterprise Dependency Intelligence

A knowledge-graph-backed application for enterprise dependency discovery, change-impact analysis, and (from MVP2 onward) Graph RAG and agentic investigation — built incrementally over a synthetic enterprise, **Meridian Retail Group**.

**Current milestone: MVP4 — Agentic Investigation (building on MVP1–3).**
MVP1–3 Ask paths remain fully usable. Investigate runs a required evidence
skeleton plus bounded allowlisted tools and returns a grounded report when
`AGENTIC_INVESTIGATION_ENABLED` is on (`ADR-0007`). See
`docs/00_project/PROJECT_CHARTER.md` and `docs/00_project/PRODUCT_BRIEF.md`.

## What this does today (MVP1)

- Ingests 5 synthetic enterprise data sources (CMDB, API Catalog, DB Metadata, Team Ownership, Integration Catalog) into a Neo4j knowledge graph, with entity resolution and full provenance tagging.
- Lets you search for any application, service, API, database, pipeline, report, external system, team, or business capability by name.
- Shows direct and transitive (configurable-depth) upstream/downstream dependencies, with a visual subgraph.
- Finds the shortest — and alternate — dependency paths between two entities.
- Rolls up owning teams across a dependency subtree, for stakeholder discovery before a change.
- Shows which business capabilities a given entity supports.
- Answers 7 fixed natural-language dependency questions with a grounded, evidence-backed answer — and gives an explicit "not supported" response for anything else, never a guess.
- Shows the graph evidence (path, relationship types, source system) behind every answer.

## Repository layout

```
src/            Runtime application code (datagen, ingestion, graph, nlquery, api, web)
tests/          Unit and integration tests
evals/          Golden dataset — one scenario per supported NL question / key behavior
data/sample/    Generated synthetic source datasets (regenerable, not hand-edited)
docs/           Project docs — see AGENTS.md "Where things live"
.skills/        Project-specific SDLC skill overlay (empty unless a domain gap appears)
```

## Getting started

See `docs/03_operations/RUNBOOK.md` for the full local development setup (Python environment, remote Docker/Neo4j connectivity, running ingestion, running the app, running tests).

## Development process

Operating rules for AI coding agents live in `AGENTS.md`. Delivery tracking for MVP1 is local-only (todo list + direct commits), not GitHub issues/PRs — see `docs/00_project/AI_ORCHESTRATOR_BRIEF.md` for why. The Enterprise SDLC MCP server is turned off for this project; use built-in agent/review capabilities instead.

## Roadmap beyond MVP1

| Milestone | Adds |
|---|---|
| MVP2 — Graph RAG | Grounded LLM answers for open-ended questions, via dynamic graph retrieval over the same graph. **Done.** |
| MVP3 — Hybrid Graph + Document RAG | Unstructured architecture documentation fused with graph evidence. **Done.** |
| MVP4 — Agentic Investigation | Bounded, multi-step investigation producing evidence-backed reports. **Done.** |
| MVP5 — Advanced Enterprise Intelligence | Risk scoring, drift detection, what-if analysis. |

Each milestone adds value on top of the previous one — MVP1's UI, API, and deterministic query layer stay usable through every later milestone.
