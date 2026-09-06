# Security

## Data

This project uses **synthetic** Meridian Retail Group sample data only. Do not ingest, commit, or publish real company, customer, or personal data.

## Secrets

- Copy `.env.example` → `.env` for local config. **Never commit `.env`.**
- Leave `OPENAI_API_KEY` empty unless you intentionally enable Graph RAG / Hybrid / Investigate / narrative features.
- Default Neo4j credentials (`neo4j` / `edi-local-dev`) are for local synthetic demos only—change them if the database is reachable beyond your machine.

## Reporting

If you find a vulnerability or an accidental secret in this repository, open a private GitHub security advisory (or contact the maintainer) rather than filing a public issue with exploit details.
