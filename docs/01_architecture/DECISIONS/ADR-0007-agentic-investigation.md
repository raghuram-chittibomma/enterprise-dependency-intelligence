# ADR-0007: Bounded agentic investigation (MVP4)

Status: Accepted

## Context

MVP1–3 answer dependency questions via closed templates, single-shot Graph
RAG, and optional Hybrid Doc RAG (`ADR-0004`–`ADR-0006`). Users still need
multi-step change-impact style investigations (blast radius, stakeholders,
supporting docs) that a single retrieve+generate pass may under-cover.
Unconstrained agents (free Cypher, unlimited tools) would break the
faithfulness boundary that FR12/FR15/FR16/FR19 enforce.

## Decision

For MVP4 Agentic Investigation:

1. **Separate entry**: A dedicated Investigate UI/API (`/investigate`), not
   an auto-escalation of Ask. Closed templates and open-ended Ask remain
   unchanged.
2. **Hybrid control (skeleton + tools)**: Always run a required evidence
   skeleton (entity detail, direct deps / shallow traversal, ownership,
   capabilities, optional doc chunks when Hybrid is on). Then allow the LLM
   up to `AGENTIC_MAX_TOOL_CALLS` (default 3) **allowlisted** tool calls
   that wrap existing `GraphStore` query templates and doc retrieve — never
   Text2Cypher or arbitrary code.
3. **Report**: LLM synthesizes a structured report citing only gathered
   graph edges and/or document chunks; code filters citations and refuses
   when unsupported. UI shows report, evidence, and a compact step trace.
4. **Flag**: `AGENTIC_INVESTIGATION_ENABLED` (default false); requires
   `OPENAI_API_KEY`. Graph/Hybrid flags stay independent; doc tools no-op
   when Hybrid is off.
5. **Evals**: Fake-LLM unit/eval scenarios must prove skeleton always runs,
   tool budget is enforced, and fabricated citations are rejected.

## Consequences

- **Easier**: Ask regression surface stays small; investigation quality can
  be evaluated as a report artifact with a step trace.
- **Easier**: Faithfulness remains code-checkable (cited ⊆ gathered).
- **Harder**: Adaptive tool choice is non-deterministic — budgets and
  allowlists are mandatory.
- **Rejected: Ask auto-escalate in MVP4 v1** — revisit after Investigate
  proves useful.
- **Rejected: free Text2Cypher / unconstrained tools** — same risk as
  ADR-0005.
- **Rejected: rewriting closed 7 templates with an LLM** — unchanged.
