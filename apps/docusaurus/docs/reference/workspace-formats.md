---
sidebar_position: 5
---

# Workspace File Formats

Complete format reference for every file a team member writes under `workspace/`.

:::info Example files
Every workspace directory ships with a `_example.md` (or `_example-*.md`) scaffold file.
These files are **never read by Scraut automation** — they exist only to show the expected format.
Real files must be named as documented below (e.g. `alice.md`, `okr.md`, `capacity.md`).
:::

---

## `workspace/sprint/NNN/standup/YYYY-MM-DD/{login}.md`

One file per team member per working day. Created automatically each morning by the `template-reset` workflow.

**Filename:** your exact GitHub login (e.g. `alice.md`, `bob.md`)

```markdown
# Standup — Alice — 2026-05-24

## Yesterday
- Closed #12: Authentication middleware refactor
- Reviewed PR #14 — left 2 comments, awaiting response

## Today
- Continue #15: Add rate limiting to the API gateway
- Pair with Bob on the database migration script

## Blockers
None

## Notes
OOO Friday afternoon
```

| Section | Required? | Notes |
|---------|-----------|-------|
| `## Yesterday` | Yes | What you completed. Reference `#NN` issue numbers. |
| `## Today` | Yes | What you'll work on. Reference issues where possible. |
| `## Blockers` | Yes | Write `None` if nothing is blocking you. Any other content triggers the escalation flag. |
| `## Notes` | No | OOO, reduced availability, context for the team. |

**Tips:**
- Use `#NN` issue references — Scraut links them automatically in summaries
- "Worked on auth" → bad. "Completed login form validation, tests pass" → good
- If blocked, name the dependency: "Waiting on design mockups from @carol for #23"

**Automation files in the same directory:**

When Agent Mode is enabled, AI agents submit standups in the same folder with an `agent-` prefix:

```
workspace/sprint/001/standup/2026-05-24/
  alice.md          ← Alice's standup
  bob.md            ← Bob's standup
  agent-backend.md  ← Backend agent standup (if agent mode on)
  _example.md       ← Never processed — format reference only
```

---

## `workspace/sprint/NNN/retrospective/{login}.md`

One file per team member per sprint. Fill it in during or before the retrospective ceremony.

**Filename:** your exact GitHub login (e.g. `alice.md`, `bob.md`)

```markdown
# Retro — Alice — Sprint 001

## Went well
- Code review turnaround was fast (avg < 4 hours)
- Sprint goal was clear from day one; no scope confusion
- Deployment pipeline ran without issues all sprint

## Could improve
- Standups ran over 15 minutes — need a timebox
- We added two unplanned issues mid-sprint; both hurt focus
- Grooming session was skipped — backlog priorities unclear by week 2

## Action items I'll own
- Set a 15-minute timer for standups starting next sprint
- Flag any unplanned work additions at the next retro
```

| Section | Required? | Notes |
|---------|-----------|-------|
| `## Went well` | Yes | Be specific — reference incidents, PRs, ceremonies |
| `## Could improve` | Yes | Focus on process, not people |
| `## Action items I'll own` | Yes | Personal commitments — be measurable |

Scraut's `synthesise_retrospective.py` reads all files in this folder and synthesises them into a single team retrospective document at `.scraut/sprint/NNN/retrospective/summary.md`.

---

## `workspace/sprint/NNN/meta.md`

Sprint metadata. Created once per sprint by the SM (or by the `sprint-planning` workflow).

```markdown
# Sprint 001

- Period: 2026-05-25 → 2026-06-07
- Goal: Ship rate limiting and the OAuth integration — team can deploy both to staging
- Team: alice, bob, charlie
- Committed: 32 story points across 8 issues
- Capacity note: See team/capacity.md — Bob is OOO Friday 30th

## Issues in sprint

| Issue | Title | Epic | SP | Assignee |
|-------|-------|------|----|---------|
| #15   | Add rate limiting to API gateway | API v1 | sp:5 | alice |
| #21   | OAuth integration (Google) | Auth | sp:8 | bob |
| #23   | Profile page redesign | UI | sp:3 | charlie |
```

The Sprint Goal is extracted from the `- Goal:` line and used in the sprint review narrative and retrospective synthesis.

:::tip
Keep the sprint goal short and outcome-oriented: "Team can deploy both rate limiting and OAuth to staging" beats "Work on rate limiting and OAuth".
:::

---

## `workspace/sprint/NNN/decisions/{date}-{slug}.md`

Sprint-scoped decisions. Create one file per significant decision made during the sprint. All files here are compiled into the sprint review document.

**Filename:** suggested format `YYYY-MM-DD-short-title.md`, but any `.md` name works.

:::note
Files starting with `_` are ignored by automation (the `_example.md` scaffold uses this).
:::

```markdown
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
```

---

## `workspace/sprint/NNN/grooming/backlog-ideas.md`

Free-form mid-sprint backlog ideas. Anyone on the team can append entries at any time. The grooming agent reads this file when suggesting priorities.

```markdown
# Backlog Ideas — Sprint 001

## User story ideas

- **Password reset via email**
  - As a user, I want to reset my password via email so that I can regain access if locked out.
  - Why: 5 support tickets this month about locked accounts
  - Rough size: sp:3

- **Bulk CSV export for admins**
  - As an admin, I want to export user data as CSV for compliance audits.
  - Why: Legal team request — needed before Q3 audit
  - Rough size: sp:5

## Bug reports worth tracking

- Login page crashes on Safari iOS 16 — 2 users reported, low priority

## Technical debt ideas

- Refactor the auth module — currently 3 different token formats
  - Blocks: adding OAuth providers cleanly
```

No rigid format is required — the grooming agent reads this as a free-text source. More context and the "Why" helps it rank accurately.

---

## `workspace/sprint/NNN/adr/{NNN}-{slug}.md`

Architecture Decision Records scoped to a sprint. For long-lived ADRs that span multiple sprints, use `workspace/knowledge/` instead.

**Filename:** suggested format `NNN-short-title.md` (e.g. `001-use-postgresql.md`)

```markdown
# ADR-001: Adopt PostgreSQL as Primary Data Store

**Status:** Accepted
**Date:** 2026-05-20
**Deciders:** Alice (tech lead), Bob (backend), Charlie (PM)

## Context

Current SQLite store cannot handle concurrent writes from the API and background jobs.
Lock timeouts at ~50 req/s. Need JSONB columns for flexible event payloads.

## Considered options

1. **PostgreSQL** — battle-tested, JSONB, concurrent writes, good tooling
2. **MySQL 8** — familiar, but weaker JSONB support
3. **CockroachDB** — distributed, but over-engineered for current scale

## Decision

PostgreSQL 15. Docker Compose locally; managed RDS in production.

## Consequences

| Impact | Detail |
|--------|--------|
| Positive | Concurrent writes, JSONB, full-text search, fuzzy search via `pg_trgm` |
| Negative | Dev setup now requires Docker; ~8h migration effort |
| Risk | Migration window must avoid peak traffic hours |

## Follow-up

- Bob writes migration scripts by Sprint 002
- Update `CONTRIBUTING.md` with Docker Compose setup instructions
```

ADR files are not currently read by Scraut automation — they exist as a team record.

---

## `workspace/team/capacity.md`

Team availability for the current sprint. Scraut reads this during sprint planning to adjust story point targets.

**Filename:** must be exactly `capacity.md`

```markdown
# Team Capacity — Sprint 001

<!-- Available Days = full working days in the sprint.
     Default: 10 for a 2-week sprint (Mon–Fri × 2 weeks).
     Reduce for OOO, part-time weeks, public holidays. -->

| Login   | Available Days | Notes                               |
|---------|---------------|-------------------------------------|
| alice   | 10            | Full sprint                         |
| bob     | 8             | OOO Friday 30th (family event)      |
| charlie | 6             | Part-time — 3 days/week this sprint |

## Notes

- Team velocity last sprint: 34 sp
- Planned capacity at 85% buffer: ~29 sp
- Charlie is ramping on the new service — may need pairing time
```

Update this file at the start of each sprint. The sprint planning workflow uses `Available Days` to scale the story point target.

---

## `workspace/okr/okr.md`

Team Objectives and Key Results. Scraut reads this during sprint planning and backlog grooming to align priority recommendations.

**Filename:** suggested `okr.md`, but any `.md` file in this folder is read (files starting with `_` are skipped).

```markdown
# Objectives & Key Results — 2026 Q2

## Objective 1: Ship a reliable, production-ready API

> Ship a stable v1.0 API that developers can build on confidently.

### Key Result 1.1 — Latency
- Target: p95 API response time < 200ms
- Current: 340ms

### Key Result 1.2 — Reliability
- Target: 99.9% uptime for 30 consecutive days
- Current: 98.7%

### Key Result 1.3 — Developer adoption
- Target: 100 developers with active API keys by end of Q2
- Current: 12

---

## Objective 2: Build a product users actually understand

> Reduce time-to-first-value for new users to under 10 minutes.

### Key Result 2.1 — Onboarding completion
- Target: 60% of signups complete first API call within 10 minutes
- Current: 23%

### Key Result 2.2 — Documentation satisfaction
- Target: Docs NPS ≥ 40
- Current: Not yet measured
```

Update the `Current:` values at the start of each sprint so planning prompts reflect real progress.

---

## `workspace/milestones/{name}/milestone.md`

One subdirectory per milestone, with `milestone.md` inside it. Scraut reads this to prioritise issues against the milestone goal during grooming.

**Path:** `workspace/milestones/{milestone-name}/milestone.md` — the subdirectory name is the milestone identifier.

```markdown
# Milestone: v1.0

- Due: 2026-07-01
- Goal: Ship the MVP — core authentication, API v1, and the team dashboard
- GitHub milestone: https://github.com/myorg/my-repo/milestone/1

## Epics

- [ ] Epic: User Authentication — #45
- [ ] Epic: Dashboard MVP — #67
- [ ] Epic: Public API v1 — #89
- [ ] Epic: Documentation — #102

## Risks

- Third-party OAuth has had 3 outages this quarter — Mitigation: circuit breaker + fallback
- 2 team members on PTO last 2 weeks of June — Mitigation: front-load risky work early

## Definition of Done

- [ ] All committed issues closed or explicitly deferred with owner
- [ ] Load test passing: p95 < 200ms at 100 req/s
- [ ] Release notes drafted and reviewed by PM
- [ ] Stakeholders notified via email
```

The health check script also reads `roadmap.md` and `breakdown.json` from the same subdirectory if they exist (generated by the milestone planning workflow).

**Directory layout:**

```
workspace/milestones/
  v1.0/
    milestone.md        ← goal and epic list (you write this)
    roadmap.md          ← LLM-generated timeline (bot writes after planning)
    breakdown.json      ← SP breakdown (bot writes after planning)
  v2.0/
    milestone.md
```

---

## `workspace/customer/feedback.md`

Customer feedback log. The grooming agent reads this to suggest which backlog issues to prioritise.

**Filename:** must be exactly `feedback.md`

```markdown
# Customer Feedback

## Feedback Log

| Date       | Source              | Summary                                    | Priority | Linked Issue |
|------------|---------------------|--------------------------------------------|----------|--------------|
| 2026-05-10 | Support ticket #47  | Can't reset password from mobile Safari    | high     | #23          |
| 2026-05-14 | User interview (3)  | Dashboard takes 8s to load on first visit  | medium   | —            |
| 2026-05-20 | NPS survey comment  | "API docs are confusing — examples wrong"  | medium   | —            |

## Themes

- **Auth friction** — 5 separate tickets about login/password this quarter
- **Performance on first load** — 3 interviews flagged dashboard speed
- **Documentation gaps** — examples reference v0.8 API, not v1.0
```

Append rows as feedback arrives. The LLM reads the full file as context, so natural-language themes in the Themes section are also useful.

---

## `workspace/knowledge/` — Free-form knowledge base

Files here are **not read by Scraut automation**. Use this folder for any persistent team knowledge that doesn't fit in a sprint folder.

Suggested structure:

```
workspace/knowledge/
  architecture.md       ← System design, data flows, infrastructure map
  onboarding.md         ← New team member setup guide
  api-reference.md      ← Internal API notes, auth flows, rate limits
  runbooks/             ← Incident response procedures, on-call playbooks
  integrations.md       ← Third-party services, credentials location
  decisions/            ← Long-lived ADRs spanning multiple sprints
```

No format is enforced — write what's useful for your team.

---

## Naming rules at a glance

| File | Who writes | Read by Scraut? | How Scraut finds it |
|------|-----------|-----------------|---------------------|
| `standup/DATE/{login}.md` | Each team member | Yes | Exact path per login |
| `standup/DATE/agent-*.md` | AI agents | Yes | `glob("agent-*.md")` |
| `retrospective/{login}.md` | Each team member | Yes | Exact path per login |
| `sprint/NNN/meta.md` | SM / planning workflow | Yes | Exact path |
| `decisions/*.md` | Any team member | Yes | `glob("*.md")` — files starting with `_` are skipped |
| `grooming/backlog-ideas.md` | Any team member | Yes | Exact path |
| `adr/*.md` | Any team member | No | Not currently automated |
| `team/capacity.md` | SM | Yes | Exact path |
| `okr/*.md` | PO | Yes | `glob("*.md")` — files starting with `_` are skipped |
| `milestones/*/milestone.md` | PM / PO | Yes | `glob("*/milestone.md")` |
| `customer/feedback.md` | Any team member | Yes | Exact path |
| `knowledge/**` | Any team member | No | Not automated |
| `_example.md` / `_*.md` | Template — never edit | **Never** | Always skipped |
