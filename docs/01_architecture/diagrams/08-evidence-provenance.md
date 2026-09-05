# 08 — Evidence & provenance

How source tags become trust signals in the UI.

```mermaid
flowchart LR
  subgraph source [Source record]
    Rec[CMDB / API / DB / Team / Integration / Doc]
  end

  subgraph graph [Graph member]
    Node[Node or relationship]
    Prov["source_system<br/>source_record_id<br/>evidence_type"]
  end

  subgraph answer [User-visible answer]
    Claim[Claim or path hop]
    EvPanel[Evidence panel]
  end

  Rec -->|ingestion MERGE| Node
  Rec --> Prov
  Prov --> Node
  Node -->|query / retrieve| Claim
  Prov --> EvPanel
  Claim --> EvPanel
```

```mermaid
flowchart TD
  A[Any product surface] --> B{Assertion about a dependency?}
  B -->|Yes| C[Must resolve to graph edge or retrieved doc chunk]
  C --> D[Show provenance: source system, type, documented vs inferred]
  B -->|No evidence| E[Refuse or N/A — never invent]
```

Applies to explorer, closed Ask, Graph/Hybrid RAG, Investigate citations, and Intelligence factors (`ADR-0003`, FR12).
