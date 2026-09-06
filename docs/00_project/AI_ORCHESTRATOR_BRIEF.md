# AI Orchestrator Brief

Status: draft

Read by: Product Analyst Agent, `github-issue-quality-review` skill, `release-readiness-review` skill.

Whoever (human or agent) is coordinating delivery across issues/PRs uses this doc as the single place to check current scope, assumptions, and open questions — instead of re-deriving them from chat history each time.

## Current scope

Building MVP1 — the Knowledge Graph and Dependency Explorer — end to end: ontology, synthetic data generation for the 5 MVP1 sources, a graph store, an idempotent ingestion pipeline with entity resolution and provenance, automated data-quality checks, and the full FR1–FR13 feature set (search, detail, direct/transitive dependency traversal with subgraph visualization, path finding, ownership rollup, business capability view, a deterministic 7-question NL query layer, and an evidence/provenance panel), closing with a golden-dataset evaluation and release-readiness review. Zero LLM calls anywhere in this scope. Delivery is tracked via the agent's todo list (see increment IDs in `docs/00_project/PRODUCT_BRIEF.md`'s FR table), not GitHub issues — see the `local_only` decision below.

## Assumptions

- **Delivery tracking is local-only for MVP1** (decided over GitHub-first issue/PR tracking, 2026-08-11): work proceeds as direct commits to `main` on a local git repo, tracked via the agent todo list rather than GitHub issues/PRs/independent-review gates. If this is wrong — e.g. a second contributor joins, or history needs to be reviewable per-change — the project should retroactively stand up the GitHub repo, milestone, and one issue per FR/increment before continuing (see AGENTS.md golden rules 1 and 6, which this decision temporarily supersedes for MVP1).
- **Neo4j Community Edition via Docker Compose (localhost by default) is the MVP1 graph store** (ADR-0001). If Neo4j is unreachable, fall back to the embedded alternative documented in the same ADR (NetworkX + SQLite) rather than blocking on infrastructure.
- **The MVP1 NL query layer is fully deterministic** (ADR-0004): keyword/regex intent classification + `rapidfuzz` entity resolution + parameterized Cypher templates + string-templated answers. If a supported question can't be answered this way, that's a bug in the template/intent logic, not a signal to reach for an LLM early.
- **Synthetic data is sufficient to validate every FR** — the ~30–40 seed entities across `Meridian Retail Group` are assumed to exercise every relationship type and every one of the 7 golden questions at least once. If golden-dataset coverage reveals gaps, the synthetic dataset gets extended before any code is called "done."
- **Cardinality decisions made to fill plan gaps** (documented in `docs/01_architecture/DATA_MODEL.md`, not in the original planning conversation) are provisional: single ownership per entity (`OWNED_BY` many-to-one), and single successor per `REPLACED_BY`. If real scenarios need co-ownership or multi-successor splits, that requires an ADR before relaxing the constraint.

## Open questions

- Whether `Report` and `ExternalSystem` need additional type-specific properties beyond what's in `docs/01_architecture/DATA_MODEL.md` once synthetic data generation (increment-2) surfaces realistic examples — currently blocked on nothing, will be revisited opportunistically during that increment.
- Whether the remote Docker host stays reachable for the full build, or whether local dev should switch to the NetworkX+SQLite fallback for reliability — currently assumed reachable per the connectivity already verified; owner: whoever is running the dev session, revisit if the host drops off the LAN.
- When (if ever within this engagement) to revisit the `local_only` delivery-tracking decision and stand up GitHub issues/PRs — owner: project owner, no trigger defined yet beyond "a second contributor joins."

## Known risks

- **Graph store availability risk**: the graph store runs on a remote LAN host outside this dev machine's direct control. Mitigation: ADR-0001 documents an embedded fallback (NetworkX + SQLite) so development isn't fully blocked if the host is unreachable.
- **Scope creep into MVP2+ during MVP1 build**: Graph RAG, agentic investigation, and LLM integration are explicitly out of scope for MVP1 (see `docs/00_project/PRODUCT_BRIEF.md`). Mitigation: ADR-0004 makes the "no LLM in MVP1" boundary an explicit, checked decision, not just a norm.
- **Golden dataset false confidence**: a golden dataset with too few scenarios could pass 100% while missing real gaps. Mitigation: increment-15 requires the golden dataset to cover all 7 NL questions plus FR1–FR10/FR12/FR13 behaviors, not just a happy-path subset.
- **Skipping GitHub-first process reduces external reviewability**: with `local_only` tracking, there's no PR-level independent review gate during MVP1 build. Mitigation: a final architecture and code review pass is still run at increment-15 (release readiness) before calling MVP1 done, even without per-increment PR review.
