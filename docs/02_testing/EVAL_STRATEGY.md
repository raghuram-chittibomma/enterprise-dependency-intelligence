# Eval Strategy

Status: accepted (MVP1 scope only — this doc is kept, not deleted, because the project has a planned LLM component from MVP2 onward; see `docs/00_project/PROJECT_CHARTER.md`)

Read by: Test/Eval Designer Agent, `llm-as-judge-rubric-design` skill.

## What gets evaluated

**MVP1 has no LLM-backed behavior**, so there is no LLM-as-judge evaluation yet — MVP1's "eval" is a deterministic golden dataset checked by exact-match assertions (functionally a test suite, not a quality score; see `docs/02_testing/TEST_STRATEGY.md`'s Golden dataset row). This section will activate for real once MVP2 (Graph RAG) introduces LLM-generated answers over retrieved subgraphs.

Planned for MVP2: faithfulness (does the generated answer only assert relationships actually present in the retrieved subgraph — see `graph-rag-retrieval-review` skill), citation accuracy (does every claim point to a real node/relationship id), and appropriate refusal (does the system say "insufficient evidence" instead of fabricating a path when nothing relevant is found).

## Golden scenarios

MVP1: one scenario per supported NL question (the 7 templates in `docs/00_project/PRODUCT_BRIEF.md`), plus representative FR1–FR10/FR12/FR13 behaviors, live under `evals/`. Each scenario records `id`, `question` (where applicable), `expected_entities`, `expected_relationship_types`, and `expected_path` (where applicable) — see `increment-15-release`. New scenarios are added whenever the synthetic dataset (`data/sample/`) grows to cover a new relationship shape, or a bug is found that a golden scenario should have caught.

MVP2+: this section will be extended with how open-ended (non-templated) question scenarios are authored and scored, once that work starts.

## Judge policy

Not applicable to MVP1 (no LLM-generated output to judge). To be defined at MVP2 kickoff, alongside the `ADR-0005` that will record the Graph RAG tooling choice (likely `neo4j-graphrag-python` per the original planning discussion).

## Pass/fail thresholds

MVP1: the golden dataset must be **100% pass** — every scenario is a deterministic exact-match assertion, so any failure is a bug in ingestion, entity resolution, a query template, or the NL query layer, not a quality regression to triage on a spectrum. This is enforced as part of `docs/02_testing/TEST_STRATEGY.md`'s Definition of Done and is a hard gate for `increment-15-release`.

MVP2+: score thresholds per scenario category will be defined once LLM-generated answers exist to threshold against.
