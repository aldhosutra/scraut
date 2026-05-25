---
sidebar_position: 9
---

# Incident Management

When production incidents happen, Scraut helps capture action items and automatically converts them into tracked GitHub issues so nothing falls through the cracks.

---

## The incident flow

```
Incident occurs (production issue)
  │
  ├─ 1. Team writes incident report in .scraut/sprint/NN/incidents/
  │
  ├─ 2. Team edits action-items.md with follow-up tasks
  │
  ├─ 3. Push triggers incident-to-backlog workflow
  │
  └─ 4. Scraut creates GitHub issues for each action item
           Labels: bug (or task), p:high, sprint labelling for next sprint
```

---

## Writing an incident report

Create a file in:
```
.scraut/sprint/001/incidents/2026-05-24-api-timeout/
```

**`incident.md`:**
```markdown
# Incident: API Timeout on Bulk Requests — 2026-05-24

**Severity:** High
**Duration:** 14:00–14:45 UTC (45 minutes)
**Impact:** All users performing bulk exports timed out

## Timeline
- 14:00 — Alert fired: p95 API response > 30s
- 14:05 — Bob identified the bulk export endpoint as the culprit
- 14:22 — Rolled back bulk export feature flag
- 14:45 — Service restored

## Root cause
The bulk export query was scanning a full table without index (added in #201 last week).
The missing index caused query time to scale with dataset size.

## Resolution
Feature flag rolled back. Index will be added before re-enabling.
```

**`action-items.md`:**
```markdown
# Action Items — API Timeout Incident

- Add index to `exports` table on `user_id` column — Bob — p:high
- Add load test for bulk export endpoint to CI — Charlie — p:medium
- Add query timeout < 5s to API middleware — Alice — p:medium
- Write runbook for bulk export rollback procedure — Charlie — p:low
```

---

## Automatic backlog creation

**Trigger:** Push to `.scraut/sprint/*/incidents/**/action-items.md`
**Workflow:** `incident-to-backlog.yml`

```
action-items.md pushed
  │
  ├─ incident_to_backlog.py
  │     Parses action-items.md (each bullet → one issue)
  │     Calls LLM to enrich each action item:
  │       "Expand this action item into a proper GitHub issue with title and AC"
  │     Creates GitHub issues:
  │       - Labels: bug/task, p:high/medium/low
  │       - Assignee: from action items
  │       - Reference: links back to incident file
  │
  └─ Posts to #scraut-bot:
        "4 backlog items created from API timeout incident"
```

---

## Created issues

For action item "Add index to `exports` table on `user_id` column — Bob — p:high":

```
Issue #71: Add database index to exports table

**From incident:** API Timeout 2026-05-24
**Priority:** p:high
**Assignee:** bob

## Description
During the 2026-05-24 API timeout incident, the bulk export query scanned
the full exports table. Adding an index on user_id will reduce query time.

## Acceptance Criteria
- [ ] Index added: CREATE INDEX idx_exports_user_id ON exports(user_id)
- [ ] Query time for 10k-row export < 100ms
- [ ] Migration tested in staging before production

## References
- Incident report: .scraut/sprint/001/incidents/2026-05-24-api-timeout/incident.md
```

---

## Scenario: Incident on a Friday afternoon

**Characters:** Bob (on-call), Alice (backend), Charlie (SM)

**Friday 16:30:**
1. Alert fires — API timeouts
2. **Bob** investigates and resolves by 17:15 (rolled back feature flag)
3. **Bob** writes `incident.md` and `action-items.md` in `.scraut/sprint/001/incidents/`
4. Bob commits and pushes → `incident-to-backlog.yml` runs
5. 4 GitHub issues created, all assigned, all linked to the incident
6. Slack post in `#scraut-bot`: "4 backlog items created from API timeout incident"

**Monday morning:**
7. Charlie reviews the 4 new issues during sprint grooming
8. Prioritises the index fix for immediate action (p:high, in-sprint label added)
9. Sprint planning includes the fix — no post-incident meeting needed

**The incident is fully triaged and tracked before the team even meets Monday.**
