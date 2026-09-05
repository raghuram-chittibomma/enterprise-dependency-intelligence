# Architecture & flow diagrams

Detailed Mermaid diagrams for Enterprise Dependency Intelligence. Render them in any Mermaid-capable viewer (GitHub, VS Code Mermaid preview, [mermaid.live](https://mermaid.live)).

| Diagram | What it shows |
|---------|----------------|
| [01-system-context.md](01-system-context.md) | Product context: sources → graph → personas |
| [02-runtime-components.md](02-runtime-components.md) | Component map across `src/` packages |
| [03-ingestion-flow.md](03-ingestion-flow.md) | Offline generate → parse → resolve → load → quality → recon |
| [04-request-flow.md](04-request-flow.md) | UI → FastAPI → queries / NL / Investigate / Intelligence |
| [05-ask-decision.md](05-ask-decision.md) | Closed template vs Graph RAG vs Hybrid vs refuse |
| [06-investigate-flow.md](06-investigate-flow.md) | Skeleton → allowlisted tools → citation gate → report |
| [07-intelligence-flow.md](07-intelligence-flow.md) | Risk, what-if, drift, rationalize (deterministic core) |
| [08-evidence-provenance.md](08-evidence-provenance.md) | How provenance tags flow into every answer |

Canonical narrative lives in [`../ARCHITECTURE.md`](../ARCHITECTURE.md) and ADRs under [`../DECISIONS/`](../DECISIONS/).
