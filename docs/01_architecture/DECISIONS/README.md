# Architecture Decision Records

One file per decision: `ADR-<NNN>-<short-slug>.md`, numbered sequentially, never reused. Never edit an ADR's decision after acceptance — if circumstances change, write a new ADR that supersedes it and link back to the old one.

## Format

```markdown
# ADR-<NNN>: <Title>

Status: Proposed | Accepted | Superseded by ADR-<NNN>

## Context

What forces (technical, business, timeline) are driving this decision?

## Decision

What was decided, stated as a single clear sentence.

## Consequences

What becomes easier or harder as a result. Include the rejected alternatives
and why they lost, not just the winning option.
```

## When to write one

Any decision that would be expensive to reverse or non-obvious to a future
reader: choice of a datastore, a runtime/hosting model, an API contract
shape, a security/guardrail boundary, a build-vs-buy call. Not every PR needs
one — most day-to-day implementation choices don't.
