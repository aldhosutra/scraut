> **This file is never read by Scraut.** It exists to show the format.
> Create any `.md` file in this folder to record a sprint decision.
> All files here are compiled into the sprint review document automatically.
> Suggested naming: `YYYY-MM-DD-short-title.md`

---

# Decision: Use PostgreSQL instead of SQLite

**Date:** 2026-05-20
**Decided by:** Alice, Bob
**Status:** Accepted

## Context

The app currently uses SQLite. We're seeing lock contention under concurrent writes
and need JSONB for flexible schema fields.

## Decision

Migrate the main data store to PostgreSQL 15. Use PgBouncer for connection pooling.

## Consequences

- **Positive:** Concurrent writes, JSONB support, full-text search
- **Negative:** Docker Compose required for local dev; higher memory baseline
- **Neutral:** Bob owns the migration path; estimated 2 sprints of work
