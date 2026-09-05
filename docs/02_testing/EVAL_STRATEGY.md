# Eval Strategy

Status: accepted (MVP1–MVP5; see `ADR-0005`–`ADR-0008`)

Read by: Test/Eval Designer Agent.

## What gets evaluated

**MVP1** has no LLM-backed behavior — its "eval" is a deterministic golden dataset checked by exact-match assertions (see `docs/02_testing/TEST_STRATEGY.md`'s Golden dataset row and `evals/`).

**MVP2** adds open-ended Graph RAG answers. Evaluated dimensions:

1. **Faithfulness** — every cited relationship in the answer exists in the retrieved subgraph (code-checked: cited edge keys ⊆ retrieved edge keys).
2. **Citation accuracy** — every claim points to a real node/relationship id present in the graph.
3. **Appropriate refusal** — when the subgraph cannot support an answer (or no entity resolves), the system returns "insufficient evidence" / not-found rather than fabricating a path.

**MVP3** extends open-ended Ask with document chunks. Additional dimensions:

1. **Doc faithfulness** — every cited `{document_id, chunk_id}` exists in the retrieved top-k set.
2. **Hybrid fusion** — answers that need both graph and doc facts cite both evidence kinds when both were retrieved and used.
3. **Refusal when docs are irrelevant** — if retrieved chunks cannot support the claim (and graph edges cannot either), refuse rather than inventing.

**MVP4** Agentic Investigate. Additional dimensions:

1. **Skeleton always runs** — required gather steps appear in the step trace before adaptive tools.
2. **Tool budget** — adaptive tool calls never exceed `AGENTIC_MAX_TOOL_CALLS`.
3. **Report faithfulness** — cited edges/chunks ⊆ evidence gathered during the run; fabricated citations refuse.
4. **Allowlist only** — only registered tools may execute (no free Cypher).

**MVP5** Advanced Intelligence (`ADR-0008`). Additional dimensions:

1. **Deterministic scores** — risk bands/factors match the documented formula for golden Meridian entities (no LLM on score path).
2. **What-if non-mutation** — retirement simulation returns blast/stakeholder sets without writing graph edges.
3. **Drift coverage** — lifecycle, `REPLACED_BY`, and unresolved-queue signal families are detectable in fixtures/evals.
4. **Narrative faithfulness** — when narrative is enabled, cited factor ids ⊆ computed factors; scores are never invented by the LLM.

## Golden scenarios

MVP1: one scenario per supported NL question (the 7 templates in `docs/00_project/PRODUCT_BRIEF.md`), plus representative FR1–FR10/FR12/FR13 behaviors, live under `evals/`. Must be **100% pass**.

MVP2: additional open-ended scenarios under `evals/` covering faithfulness, citation, and refusal. Unit tests use a **fake LLM** (no network). Optional live OpenAI runs are marked `@pytest.mark.integration` and skip without `OPENAI_API_KEY`.

MVP3: hybrid scenarios (doc-only fact, graph+doc fusion, refusal when docs irrelevant) under `evals/` with **fake embedder + fake LLM** (no network for the commit gate).

MVP4: Investigate scenarios (blast-radius style report, path+owners, refusal, budget enforcement) under `evals/` with **fake LLM** (no network for the commit gate).

MVP5: risk/what-if/drift/rationalize scenarios under `evals/` (deterministic). Narrative scenarios use **fake LLM**.

## Judge policy

MVP1: exact match only.

MVP2–MVP5 v1: **code-level grounding checks** on cited edges, doc chunk ids, and/or intelligence factor ids (no LLM-as-judge required for the release gate). LLM-as-judge rubrics may be added later if answer phrasing quality needs scoring beyond grounding.

## Pass/fail thresholds

MVP1: golden dataset **100% pass**.

MVP2–MVP5: every open-ended / hybrid / investigate / intelligence scenario must pass faithfulness (cited ⊆ gathered/computed) and refusal scenarios must not claim unsupported evidence. Fake-LLM unit tests are required on every commit touching `src/nlquery/`, `src/retrieval/`, `src/investigate/`, or `src/intelligence/`; live OpenAI integration tests are optional locally.
