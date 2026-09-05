# Eval Strategy

Status: accepted (MVP1 complete; MVP2 Graph RAG section active — see `ADR-0005`)

Read by: Test/Eval Designer Agent.

## What gets evaluated

**MVP1** has no LLM-backed behavior — its "eval" is a deterministic golden dataset checked by exact-match assertions (see `docs/02_testing/TEST_STRATEGY.md`'s Golden dataset row and `evals/`).

**MVP2** adds open-ended Graph RAG answers. Evaluated dimensions:

1. **Faithfulness** — every cited relationship in the answer exists in the retrieved subgraph (code-checked: cited edge keys ⊆ retrieved edge keys).
2. **Citation accuracy** — every claim points to a real node/relationship id present in the graph.
3. **Appropriate refusal** — when the subgraph cannot support an answer (or no entity resolves), the system returns "insufficient evidence" / not-found rather than fabricating a path.

## Golden scenarios

MVP1: one scenario per supported NL question (the 7 templates in `docs/00_project/PRODUCT_BRIEF.md`), plus representative FR1–FR10/FR12/FR13 behaviors, live under `evals/`. Must be **100% pass**.

MVP2: additional open-ended scenarios under `evals/` covering faithfulness, citation, and refusal. Unit tests use a **fake LLM** (no network). Optional live OpenAI runs are marked `@pytest.mark.integration` and skip without `OPENAI_API_KEY`.

## Judge policy

MVP1: exact match only.

MVP2 v1: **code-level grounding checks** on cited edges (no LLM-as-judge required for the release gate). LLM-as-judge rubrics may be added later if answer phrasing quality needs scoring beyond grounding.

## Pass/fail thresholds

MVP1: golden dataset **100% pass**.

MVP2: every open-ended scenario must pass faithfulness (cited ⊆ retrieved) and refusal scenarios must not claim unsupported relationships. Fake-LLM unit tests are required on every commit touching `src/nlquery/`; live OpenAI integration tests are optional locally.
