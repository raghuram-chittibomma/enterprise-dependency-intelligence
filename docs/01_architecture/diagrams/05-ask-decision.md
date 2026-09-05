# 05 — Ask decision flow

Closed templates first; optional Graph RAG / Hybrid only when flags are on.

```mermaid
flowchart TD
  Q[User question] --> Classify[Intent classification + entity resolve]
  Classify -->|Matches closed template| Closed[Dispatch FR1–FR10 query template]
  Closed --> TemplAns[TemplateAnswerGenerator]
  TemplAns --> Evidence[Attach graph evidence]
  Evidence --> Out[HTML answer]

  Classify -->|No closed match| Flags{GRAPH_RAG_ENABLED?}
  Flags -->|No| Refuse[Explicit not supported / FR13]
  Refuse --> Out

  Flags -->|Yes| Subgraph[Retrieve neighborhood subgraph]
  Subgraph --> Hybrid{HYBRID_DOC_RAG_ENABLED?}
  Hybrid -->|Yes| Docs[Top-k architecture doc chunks]
  Hybrid -->|No| LLM[LLMAnswerGenerator]
  Docs --> Fuse[Fuse subgraph + passages]
  Fuse --> LLM
  LLM --> Gate{Enough evidence to cite?}
  Gate -->|No| RefuseInsufficient[Refuse — insufficient evidence]
  Gate -->|Yes| Cited[Answer with graph/doc citations]
  RefuseInsufficient --> Out
  Cited --> Out
```

**Invariant:** answers may only cite retrieved graph/doc evidence—never free invent (`ADR-0005`, `ADR-0006`).
