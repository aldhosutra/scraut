---
sidebar_position: 2
---

# Milestone Planning

Milestones let you plan and track multi-sprint goals (releases, product versions, major features). Scraut automatically decomposes milestones into epics, tracks health, and generates forecasts.

---

## Creating a milestone

Create a file at:
```
workspace/milestones/v2.0.md
```

**Format:**

```markdown
# Milestone: v2.0
- Due: 2026-08-31
- Goal: Launch the analytics module with full team support
- GitHub milestone: https://github.com/myorg/my-repo/milestone/2

## Epics
- [ ] Epic: Analytics data pipeline — issues: #55, #56, #57
- [ ] Epic: Dashboard widgets — issues: #58, #59, #60, #61
- [ ] Epic: Export functionality — issues: #62, #63
- [ ] Epic: Team permissions for analytics — issues: #64

## Risks
- Analytics data pipeline depends on backend team delivering the data API (ETA: Sprint 3)
  Mitigation: Bob is coordinating with the backend team weekly

## Definition of Done
- [ ] All committed epics closed
- [ ] Analytics dashboard reviewed by 3 internal users
- [ ] Performance: < 3s load for 10k-row datasets
- [ ] Release notes drafted and stakeholders notified
```

---

## Milestone planning workflow

**Trigger:** Push to `workspace/milestones/*/milestone.md`
**Workflow:** `milestone-planning.yml`

When you push a new or updated milestone file:

```
push detected (workspace/milestones/v2.0.md changed)
  │
  ├─ planning_session.py
  │     Reads milestone.md
  │     Fetches all linked GitHub issues
  │     Calculates: total sp, completed sp, projected completion date
  │     Calls LLM: "Generate a milestone decomposition and sprint allocation plan"
  │     LLM produces: epic breakdown, sprint-by-sprint allocation
  │
  ├─ Writes .scraut/milestones/v2.0/planning-session.md  [BOT-GENERATED]
  │
  └─ Posts summary to #scraut-bot
```

---

## Milestone health monitoring

**Trigger:** End of each sprint review
**Workflow:** `milestone-planning.yml` (health check step)

Scraut recalculates milestone health after each sprint:

```markdown
<!-- BOT-GENERATED — Milestone Health — v2.0 — 2026-06-15 -->

# Milestone Health: v2.0

**Status: ⚠️ At Risk**
**Due:** 2026-08-31
**Current forecast:** 2026-09-14 (14 days late)

## Velocity analysis
- Required: 18 sp/sprint to finish on time
- Recent average: 14 sp/sprint
- Gap: 4 sp/sprint

## Open epics
| Epic | Issues | Closed | Open | SP remaining |
|------|--------|--------|------|-------------|
| Analytics pipeline | 3 | 1 | 2 | 13 sp |
| Dashboard widgets | 4 | 2 | 2 | 10 sp |
| Export functionality | 2 | 0 | 2 | 8 sp |
| Team permissions | 1 | 0 | 1 | 5 sp |

## Recommendation
To meet the deadline:
1. Increase sprint capacity by 4 sp (reduce scope elsewhere)
2. OR defer the "Team permissions" epic to v2.1 (saves 5 sp)
3. OR negotiate 2-week deadline extension

## Risk flags
- Epic "Analytics pipeline" depends on backend API (ETA: Sprint 3) — still pending
  → If API not ready by Sprint 3 end, recommend deferring pipeline epic
```

---

## The `milestone-risk` label

When a milestone is forecast to slip more than 1 sprint, Scraut automatically applies the `milestone-risk` label to related issues. This makes them visible in the GitHub Projects board and Slack alerts.

---

## Scenario: PM spots a milestone risk and responds

**Characters:** Alice (PM/PO), Charlie (SM)

**Week 4 of Sprint 2:**
1. **Charlie** triggers sprint review
2. Scraut generates milestone health report: v2.0 is 14 days behind forecast
3. Slack post in `#scraut-bot`: "⚠️ Milestone v2.0 at risk — forecast slipped to Sep 14"
4. **Alice** reads the health file: sees the analytics pipeline epic is blocked by the backend team
5. **Alice** updates `workspace/milestones/v2.0.md`:
   - Moves "Team permissions" epic to v2.1
   - Notes the scope reduction in the Risks section
6. She commits and pushes
7. Milestone planning workflow re-runs: updated forecast is Aug 28 (on time!)
8. `milestone-risk` label removed from issues

**Time: 15 minutes async. No milestone meeting needed.**
