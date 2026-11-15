# ADR-0001: Vector store and cache: pgvector on Neon, in-memory cache
- Status: Accepted (seeded from SRS v0.2 Appendix A)
- Date: 2026-11-14
- Requirements: SDD 3, 21

## Context
Options were considered during design and replaced; recorded so they are not reintroduced by mistake.
Documented: free tier, Singapore region, single database for ADK sessions, KB (HNSW + full text) and reporting (SDD 3).

Likely reasons (drafted - confirm): one datastore instead of a separate vector DB, cache service and extra bills; fewer moving parts for a solo POC; Neon branches give cheap test databases for CI; Redis/semantic cache are unnecessary at POC scale.

## Decision
pgvector (HNSW, hybrid search with RRF) on Neon Postgres; in-memory exact-match cache. Redis returns at MVP (SDD 21).

## Alternatives considered (superseded)
Pinecone vector DB; semantic cache; Redis for KB cache in POC

## Consequences
Revisit when the related spikes report back (docs/spikes/STATUS.md).
