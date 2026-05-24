---
sidebar_position: 3
---

# Checking Sprint Status

At any point during a sprint, you can see the current health of your sprint — story points completed, blockers, and milestone forecasts — directly from the terminal.

---

## `scraut status`

```bash
scraut status
```

**Example output:**

```
==================================================
Sprint 01 Status
==================================================
# Sprint 1
- Period: 2026-05-25 → 2026-06-07
- Goal: Deliver user authentication and basic dashboard
- Team: Alice Smith, Bob Jones, Charlie Kim
- Committed: 34 story points across 8 issues

Milestone: v1.0
  Due: 2026-06-30
  Status: On track
  Forecast: 2026-06-21 (9 days early)
  Risk: Low

2 active suggestion(s):
  • Blockers are going unresolved for > 2 days (recurring pattern detected)
  • PR review cycle is averaging 4 days (suggest daily review slot)

==================================================
```

The command reads live from your local file system — no network call needed.

---

## What it shows

| Section | Source |
|---------|--------|
| Sprint header | `workspace/sprint/NN/meta.md` |
| Milestone health | `.scraut/milestones/*/health/forecast.md` |
| Active suggestions | `.scraut/suggestions/active/` |

---

## Checking the visibility portal

For a richer view, the [Visibility Portal](../features/visibility-portal) is a GitHub Pages dashboard that shows:

- Current sprint board (Kanban-style)
- Velocity chart (historical)
- Milestone timeline
- Team standup summary for today

Access it at: `https://your-org.github.io/your-repo/`

---

## Checking from GitHub Actions

You can also see sprint state by looking at:

- The **GitHub Projects** board — synced every 30 minutes by the Visibility Engine
- The **`.scraut/` folder** in your repo — all bot-generated summaries are there
- The **Actions tab** — each workflow run has detailed logs

---

## Scenario: SM does a mid-sprint health check

**Who:** Bob (scrum master), end of Sprint 01 day 7

**Steps:**

1. **Bob** runs `scraut status` in his terminal
2. He sees: `Sprint health: 18 of 34 sp completed (53%) — on track`
3. He notices: `1 active suggestion — blockers unresolved > 2 days`
4. He checks the suggestion file: `.scraut/suggestions/active/s001-unresolved-blockers.md`
5. The suggestion says: "Alice has had the same blocker for 3 days — recommend daily escalation check"
6. **Bob** creates a calendar reminder and resolves the blocker

**Time spent: 2 minutes.**
