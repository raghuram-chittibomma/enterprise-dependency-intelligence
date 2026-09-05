# ADR-0006: Hybrid Graph + Document RAG (MVP3)

Status: Accepted

## Context

MVP1–2 answer dependency questions from the property graph alone
(`ADR-0004`, `ADR-0005`). Architecture notes, runbooks, and similar
unstructured text often encode facts that are not yet edges (or that
explain *why* edges exist). The data model already reserved a `Document`
node and `DOCUMENTED_BY` relationship for this milestone. Introducing
document retrieval without a hard grounding boundary would allow the LLM
to invent claims that appear in neither the graph nor the docs.

## Decision

For MVP3 Hybrid Graph + Document RAG:

1. **Ontology**: Add `Document` (10th node type) and `DOCUMENTED_BY`
   (`Document` → entity it documents, 8th relationship), with ADR-0003
   provenance on every write. Natural keys use
   `doc:arch-docs:<slug>`.
2. **Corpus**: Synthetic Meridian architecture markdown only, under
   `data/sample/docs/` (datagen). No real Confluence/SharePoint or
   customer documents.
3. **Embeddings**: OpenAI `text-embedding-3-small` via existing
   `OPENAI_API_KEY`. Chunk markdown offline; upsert into a **local
   SQLite** vector store under `data/vectors/` (not Neo4j-native vector
   indexes in MVP3 v1), so Neo4j and FallbackGraphStore share the same
   retrieval path.
4. **Ask fusion**: When `HYBRID_DOC_RAG_ENABLED=true` (and Graph RAG is
   on), the open-ended path retrieves the MVP2 dependency subgraph **and**
   top-k document chunks. The LLM may assert only what is supported by
   cited graph edges and/or `{document_id, chunk_id}` citations; otherwise
   refuse (`insufficient_evidence`). Closed 7 templates stay unchanged.
5. **Feature flag**: `HYBRID_DOC_RAG_ENABLED` defaults false. Enabling it
   requires Graph RAG + an API key for live embedding/generation; unit
   tests use fake embedders/LLMs with no network.

## Consequences

- **Easier**: Doc-only and graph+doc answers share one Ask path and one
  faithfulness gate; FallbackGraphStore demos still work without Neo4j
  vector features.
- **Easier**: Citation checks stay code-level (no LLM-as-judge required
  for the release gate).
- **Harder**: Operators must run `python -m src.retrieval.index_docs`
  after regenerating/ingesting docs so the vector store stays in sync.
- **Rejected: Neo4j native vector indexes for MVP3 v1** — revisit when
  FallbackGraphStore parity is less important.
- **Rejected: real document connectors** — synthetic Meridian docs only
  until a later connector milestone.
- **Rejected: changing MVP1 FR1–FR10 or the closed 7 templates** —
  hybrid fusion applies only to open-ended Ask.
