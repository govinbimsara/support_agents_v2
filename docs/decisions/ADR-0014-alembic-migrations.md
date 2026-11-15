# ADR-0014: Alembic for application schema migrations
- Status: Accepted
- Date: 2026-11-16
- Requirements: NFR-REL-04, SDD section 5.2 (DB driver), schemas kb / convo / audit / app

## Context
ADK's `DatabaseSessionService` creates and manages the `adk.*` tables itself, so those are never migrated by us. Everything else (knowledge base and vectors, conversation records, audit, strikes, reporting, app tables) needs versioned, repeatable schema changes. The codebase is handed to a team after the demo, so the tool should be one they already know. NFR-REL-04 requires migrations to use the direct (non-pooled) Neon endpoint.

## Decision
Use Alembic with SQLAlchemy for every schema except `adk`.
- Migrations live in `migrations/` and run against `DATABASE_URL_DIRECT` only.
- Alembic is configured to ignore the `adk` schema (`include_object` filter), so autogenerate never touches ADK tables.
- Application traffic keeps using the pooled endpoint with NullPool.
- Every migration is reviewed by hand before commit; autogenerate output is a draft, not the result.
- CI applies all migrations to a fresh Neon branch before integration tests run.

## Alternatives considered
- Plain versioned `.sql` files with a small runner - simpler to read, but we would own and maintain the runner, and a receiving team would expect a standard tool.
- ORM `create_all()` at startup - no history, no rollback, unsafe next to ADK-managed tables.

## Consequences
- Good: standard tooling, history, upgrade and downgrade paths, works with SQLAlchemy already required by ADK.
- Bad: more setup than raw SQL; autogenerate can propose changes to objects it should not touch, hence the `adk` filter and manual review.
- Follow-ups: pgvector extension and HNSW index creation go in migrations written by hand (autogenerate does not cover them well). Verify the exact Alembic and pgvector setup through context7 during slice 0, not from memory.
