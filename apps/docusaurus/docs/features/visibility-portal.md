---
sidebar_position: 5
---

# Visibility Portal

The Visibility Portal is a GitHub Pages dashboard that gives stakeholders a real-time view of sprint progress, team velocity, and milestone health — without needing access to GitHub issues or source code.

---

## Accessing the portal

The portal is deployed at:
```
https://your-org.github.io/your-repo/
```

It shows:
- Current sprint Kanban board (derived from GitHub issues)
- Today's standup summary
- Velocity chart (last 5 sprints)
- Milestone health indicators
- Active suggestions

---

## How it works

The portal is driven by two workflows:

### 1. Visibility Engine (board sync)

**Trigger:** Push to standup files or sprint meta, plus every 30 minutes
**Workflow:** `visibility-engine.yml`

```
Standup files change
  │
  ├─ derive_state.py
  │     Reads all workspace/ text files
  │     Reads .scraut/ generated summaries
  │     Derives sprint board state: to-do / in-progress / done
  │     NEVER reads the GitHub Projects board (text files are source of truth)
  │
  ├─ sync_board.py
  │     Updates GitHub Projects board columns from derived state
  │
  └─ Writes apps/portal/data.json  [BOT-GENERATED]
```

### 2. Portal Publish

**Trigger:** Push to `apps/portal/`
**Workflow:** `portal-publish.yml`

```
data.json updated
  │
  └─ Deploys apps/portal/ to GitHub Pages
        → portal is live with fresh data
```

---

## What the portal shows

### Sprint board

A Kanban-style view derived from issue labels and standup activity:

| To Do | In Progress | In Review | Done |
|-------|------------|-----------|------|
| #41 Export CSV (sp:5) | #21 OAuth (sp:5) — Alice | #25 Rate limiting — Bob | #33 Login bug ✓ |
| #44 Dark mode (sp:5) | #28 Dashboard (sp:8) — Charlie | | #35 Tests ✓ |

The board state is derived from:
- `in-sprint` label → card exists
- Standup "Today" section mentions issue → moves to In Progress
- PR opened with `Closes #N` → moves to In Review
- Issue closed → moves to Done

### Velocity chart

A bar chart showing completed vs. planned story points for each sprint.

### Standup summary

Today's LLM-generated standup summary, rendered as a clean team status report.

### Milestone health

Traffic-light indicator per milestone (green / yellow / red based on forecast).

---

## Making the portal private

By default, the portal is public. To restrict access:

```yaml
# workspace/scraut.yml
portal:
  public: false
```

Then in GitHub: **Settings → Pages → Visibility → Private**

Note: Private GitHub Pages requires a GitHub Enterprise or Team plan.

---

## Scenario: Stakeholder checks progress without bothering the team

**Characters:** David (CTO), Sprint 2 in progress

1. **David** wants to know if the v2.0 milestone is on track
2. He opens `https://myorg.github.io/my-repo/`
3. He sees: **Milestone v2.0 — 🟡 At Risk — forecast Sep 14 (target Aug 31)**
4. He clicks through to see which epics are behind
5. He sees the "Analytics pipeline" epic is blocked on a dependency
6. He emails the backend team directly — no status meeting needed
7. **Team is not interrupted** — they learn David checked from the portal access logs

**Total interruption to the team: 0 minutes.**
