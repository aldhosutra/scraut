> **This file is never read by Scraut.** It exists to show the ADR format.
> Create one `.md` file per Architecture Decision Record.
> Suggested naming: `NNN-short-title.md` (e.g. `001-use-postgresql.md`)

---

# ADR-001: Adopt PostgreSQL as Primary Data Store

**Status:** Accepted
**Date:** 2026-05-20
**Deciders:** Alice (tech lead), Bob (backend), Charlie (PM)

## Context

The current SQLite store cannot handle concurrent writes from the API and background
jobs. We're hitting lock timeouts at ~50 req/s. We also need JSONB columns for
flexible event payloads.

## Considered options

1. **PostgreSQL** — battle-tested, JSONB, concurrent writes, good tooling
2. **MySQL 8** — familiar to the team, but weaker JSONB support
3. **CockroachDB** — distributed, but over-engineered for our scale

## Decision

PostgreSQL 15. Deployed via Docker Compose locally; managed RDS in production.

## Consequences

| Impact | Detail |
|--------|--------|
| Positive | Concurrent writes, JSONB, full-text search, `pg_trgm` for fuzzy search |
| Negative | Dev setup now requires Docker; ~8h migration effort |
| Risk | Migration window must avoid peak traffic hours |

## Follow-up

- Bob writes migration scripts by Sprint 002 end
- Update `CONTRIBUTING.md` with Docker Compose setup instructions
