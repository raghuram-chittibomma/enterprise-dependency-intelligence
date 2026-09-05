# 01 — System context

Who uses the product, and what external systems it depends on.

```mermaid
flowchart TB
  subgraph personas [Personas]
    Arch[Architect]
    TPM[TPM / Program manager]
    Eng[Engineer]
  end

  subgraph product [Enterprise Dependency Intelligence]
    UI[Search · Ask · Investigate · Intelligence UI]
    API[FastAPI application]
    GraphQ[Graph query templates]
    NL[NL / RAG / Investigate / Intelligence]
  end

  subgraph stores [Stores]
    Neo4j[(Neo4j knowledge graph)]
    Vectors[(SQLite doc vectors)]
  end

  subgraph sources [Synthetic Meridian sources]
    CMDB[CMDB]
    APICat[API Catalog]
    DBMeta[DB Metadata]
    Teams[Team Ownership]
    IntCat[Integration Catalog]
    Docs[Architecture docs]
  end

  Arch --> UI
  TPM --> UI
  Eng --> UI
  UI --> API
  API --> GraphQ
  API --> NL
  GraphQ --> Neo4j
  NL --> Neo4j
  NL --> Vectors
  CMDB --> Neo4j
  APICat --> Neo4j
  DBMeta --> Neo4j
  Teams --> Neo4j
  IntCat --> Neo4j
  Docs --> Neo4j
  Docs --> Vectors
```

**Notes**

- All catalog data is fictional Meridian Retail Group content from `src/datagen/`.
- Provenance on every node/relationship ties answers back to a source system (`ADR-0003`).
