# ADR-0005: Graph RAG tooling for open-ended NL questions (MVP2)

Status: Accepted

## Context

MVP1 proved that structured graph querying alone delivers value: the closed
7-question NL layer (`ADR-0004`) answers dependency questions with zero LLM
calls and 100% deterministic golden-dataset pass. Users still need answers to
open-ended questions outside that template set (e.g. "What would break if we
retired Customer API v1?"). Introducing an LLM without a hard grounding
boundary would reintroduce fabrication risk that FR12/FR13 exist to prevent.

The architecture already reserved an `answer_generator` extension point
(`src/nlquery/answering.py`) and relationship `evidence_type=inferred` for
MVP2+ (`ADR-0003`). ADR-0001 selected Neo4j partly for first-party Graph RAG
tooling (`neo4j-graphrag-python`).

## Decision

For MVP2 open-ended Ask questions:

1. **Routing**: MVP1's 7 closed templates stay fully deterministic
   (`TemplateAnswerGenerator`). Only questions that fail MVP1 intent
   classification enter Graph RAG, gated by `GRAPH_RAG_ENABLED=true`.
2. **Retrieval**: Deterministic subgraph retrieval over the existing
   `GraphStore` query templates (entity mention resolution via `rapidfuzz`,
   then bounded dependency traversal / related rollups). No Text2Cypher in
   MVP2 v1 — free-form Cypher generation is rejected for faithfulness risk.
3. **Generation**: OpenAI Chat Completions behind a new `LLMAnswerGenerator`
   implementing the same `AnswerGenerator` Protocol. The model may only
   assert relationships present in the retrieved subgraph; otherwise it must
   refuse ("insufficient evidence"). Citations map to real node/relationship
   ids with ADR-0003 provenance (FR12).
4. **Secrets**: `OPENAI_API_KEY` from the environment (never committed). If
   Graph RAG is enabled but the key is missing, return a clear non-answer
   rather than crashing the Ask path.
5. **`neo4j-graphrag-python`**: optional helper for future vector/Cypher
   retrievers; MVP2 v1's primary path is our own structured subgraph retrieve
   so FallbackGraphStore and Neo4j behave identically for grounding.

## Consequences

- **Easier**: MVP1 golden questions and FR1–FR10 remain LLM-free and
  regression-safe; open-ended answers are opt-in via a feature flag.
- **Easier**: Faithfulness can be checked in code (cited edges ⊆ retrieved
  subgraph) without waiting for LLM-as-judge.
- **Harder**: Open-ended quality depends on mention resolution and traversal
  depth — questions that name no resolvable entity must refuse.
- **Rejected: Text2Cypher as the primary MVP2 path** — model-generated Cypher
  can invent predicates or miss provenance; revisit only with a validated
  allowlist and eval harness.
- **Rejected: rewriting the 7 closed answers with an LLM** — would add cost
  and non-determinism for no new capability vs templates.
- **Rejected: local-only LLM for MVP2 v1** — hosted OpenAI is enough for
  local-first demo; a local model can swap behind the same Protocol later.
