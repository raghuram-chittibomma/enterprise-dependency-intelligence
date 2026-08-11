# ADR-0004: Deterministic natural-language query layer for MVP1

Status: Accepted

## Context

FR11 asks for natural-language dependency questions to be answerable; FR13 requires an explicit non-answer for anything unsupported. The project's charter also requires zero LLM calls anywhere in the MVP1 critical path, both to prove that structured graph querying alone already delivers value, and to keep MVP1's answer space fully closed and testable (no fabrication risk) before any generative component is introduced in MVP2.

The natural-language surface only needs to support 7 fixed question templates (see `docs/00_project/PRODUCT_BRIEF.md`), each of which maps directly onto an existing structured query (FR1–FR10) — this is a much narrower problem than open-ended question answering.

## Decision

Implement the MVP1 NL query layer as a fully deterministic pipeline, with **no LLM call**:

1. **Intent classification**: keyword/regex matching against the 7 known question shapes (e.g. presence of "consume" + an API name maps to question 1; "depend on" maps to question 2, etc.).
2. **Entity resolution**: extract candidate entity name(s) from the question text and resolve them using the same `rapidfuzz`-based approach as ingestion-time entity resolution (`ADR-0002`), against the already-ingested graph.
3. **Template dispatch**: route to the *same* Cypher query template a structured FR1–FR10 route would use — the NL layer is a thin front-end over existing queries, not a parallel answer path.
4. **String-templated answer generation**: format the query result into a sentence using a fixed string template per question type, always including the evidence fields needed for FR12.
5. **Explicit non-answer (FR13)**: if intent classification doesn't match one of the 7 shapes, or entity resolution can't confidently resolve a named entity, return a fixed "not supported" / "entity not found" response — never fall through to a best-effort guess.

## Consequences

- **Easier**: the entire NL answer space is enumerable and can be tested with exact-match pytest cases and a 100%-pass golden dataset (`docs/02_testing/TEST_STRATEGY.md`) — there's no model output variance to account for.
- **Easier**: proves the product's core value (grounded dependency answers) works before any LLM cost, latency, or fabrication risk is introduced — directly supports the charter goal that "structured graph querying alone already delivers real value."
- **Harder**: adding an 8th question type means writing new intent-matching logic and a new template, not just extending a prompt — this is a deliberate tradeoff (explicit closed scope over flexible-but-riskier open scope) for MVP1.
- **Sets up MVP2 cleanly**: the `AnswerGenerator` extension point (`src/nlquery/answering.py`) isolates step 4 specifically so MVP2 can swap in LLM-backed grounded generation over the *same* retrieved subgraph from steps 2–3, without touching entity resolution or query dispatch.
- **Rejected: any LLM-assisted intent classification or answer generation in MVP1** — would blur the "zero LLM calls in MVP1" boundary this ADR exists to make explicit and checkable, and isn't needed given the closed 7-question scope.
