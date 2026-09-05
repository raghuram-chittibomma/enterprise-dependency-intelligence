# 04 — Request-time flow

How a UI action becomes an evidence-backed HTML partial.

```mermaid
flowchart TD
  User[User action in UI] --> HTMX[HTMX request]
  HTMX --> Route[FastAPI route]

  Route -->|Search / detail / path / ownership / capabilities| Q[graph/queries.py]
  Route -->|Ask| NL[nlquery layer]
  Route -->|Investigate| Inv[investigate agent]
  Route -->|Risk / what-if / drift / rationalize| Intel[intelligence]

  NL --> Q
  Inv --> Q
  Intel --> Q

  Q --> Store[(GraphStore)]
  NL -->|optional Hybrid| Vec[(Doc vectors)]
  Inv -->|optional doc tool| Vec

  Store --> Render[Jinja2 partial + evidence]
  Vec --> Render
  Render --> DOM[HTMX swaps DOM]
  Q -->|subgraph JSON| Cyto[Cytoscape.js graph]
  Cyto --> DOM
```

```mermaid
sequenceDiagram
  participant U as Browser
  participant A as FastAPI
  participant S as Service layer
  participant G as GraphStore

  U->>A: GET/POST (HTMX)
  A->>S: dispatch by route
  S->>G: parameterized query / retrieval
  G-->>S: entities, paths, provenance
  S-->>A: structured result + evidence
  A-->>U: HTML partial (or graph JSON)
```

Structured FR1–FR10 paths never call an LLM. Ask / Investigate / narrative are flag-gated (`ADR-0004`–`ADR-0008`).
