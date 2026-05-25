---
sidebar_position: 1
---

# Sprint Planning

Sprint planning is a manual trigger ceremony where the Scrum Master initiates the sprint by clicking one button in GitHub Actions. Scraut then reads your backlog, team capacity, and OKRs to generate a proposed sprint plan as a pull request.

---

## When to run sprint planning

- At the beginning of each sprint (after the previous sprint closes)
- The SM triggers it — the team reviews and merges the resulting PR

---

## Pre-conditions

Before triggering sprint planning, make sure:

- [ ] Backlog issues exist in GitHub with type and priority labels (`story`, `p:high`, etc.)
- [ ] `workspace/team/capacity.md` reflects any OOO days or reduced availability
- [ ] `workspace/okr/okr.md` has your current objectives
- [ ] Previous sprint is closed (issues resolved or deferred)

---

## Triggering sprint planning

1. Go to **Actions** → **Scraut — Sprint Planning**
2. Click **Run workflow**
3. Fill in:
   - **Sprint number**: `2` (the next sprint number)
   - **org/repo**: `myorg/my-repo`
4. Click **Run workflow**

---

## What happens (step by step)

```
SM clicks "Run workflow"
  │
  ├─ create_sprint.py
  │     Creates workspace/sprint/002/ directory structure
  │     Creates GitHub milestone "Sprint 02"
  │
  ├─ plan_sprint.py
  │     Reads open issues (labeled story/task/bug, not in-sprint)
  │     Reads workspace/team/capacity.md
  │     Reads workspace/okr/okr.md
  │     Calculates available capacity: historical velocity × 0.85 buffer
  │     Calls LLM: "Given these stories and capacity, propose a sprint plan"
  │     LLM selects and prioritises stories
  │     Fills workspace/sprint/002/meta.md
  │
  └─ Creates a GitHub PR:
        Title: "Sprint 2 Planning"
        Body: Sprint goal, issue table, capacity breakdown
        Files: workspace/sprint/002/meta.md
```

---

## The planning pull request

**Example PR:**

```markdown
# Sprint 2 Planning — Proposed by Scraut

## Sprint Goal
Complete the authentication system and begin the dashboard MVP.
Goal aligns with OKR: "Launch v1.0 by Q2."

## Capacity
- Alice: 10 days (full sprint)
- Bob: 8 days (2 days OOO — see capacity.md)
- Charlie: 10 days
- Total: 28 person-days
- Historical velocity: 34 sp avg
- Capacity estimate: 34 × 0.85 buffer = 29 sp target

## Proposed Sprint Issues

| Issue | Title | Type | SP | Assignee | Reason |
|-------|-------|------|-----|---------|--------|
| #21 | OAuth integration | story | 5 | alice | High priority, OKR-aligned |
| #25 | API rate limiting | task | 3 | bob | Required for #21 |
| #28 | Dashboard skeleton | story | 8 | charlie | OKR-aligned |
| #31 | Profile page | story | 5 | alice | Dependent on #21 |
| #33 | Fix login redirect bug | bug | 2 | bob | High priority |
| #35 | Write auth test suite | task | 3 | charlie | DoD requirement |
| **Total** | | | **26 sp** | | Under 29 sp target |

## Not included (over capacity)
- #41 Email notification system (sp:8) — defer to Sprint 3
- #44 Dark mode (sp:5) — low priority
```

---

## Reviewing and adjusting the plan

The team reviews the PR. Common adjustments:
- Reassign stories (`alice` → `bob`)
- Swap in/out issues by editing `meta.md`
- Change the sprint goal
- Add OOO notes to capacity section

To change an assignment: edit `workspace/sprint/002/meta.md` in the PR branch directly, or push a commit to the PR branch.

---

## Merging the plan

When the team agrees, the **Scrum Master merges the PR**.

**What happens on merge (`sprint-plan-pr.yml`):**
- Applies `in-sprint` label to all issues listed in `meta.md`
- Links issues to the GitHub milestone
- Posts a confirmation to `#scraut-bot`: "Sprint 2 is GO 🚀 — 26 sp committed, 6 issues"

---

## Scenario: Sprint 2 planning with Bob OOO

**Characters:** Charlie (SM), Alice (developer), Bob (developer, 2 days OOO)

**Before:**
- Bob updates `workspace/team/capacity.md`:
  ```markdown
  | bob | 8 | OOO Mon-Tue (Sprint 2 start) |
  ```
- Alice creates 3 new issues after last sprint review
- The backlog has 15 open issues total

**Planning day:**
1. **Charlie** triggers sprint-planning for Sprint 2
2. Scraut reads Bob's reduced capacity (8 days instead of 10)
3. LLM accounts for Bob's OOO — assigns fewer high-complexity stories to him
4. PR is created with 26 sp (lower than usual 34 sp — Bob's days factored in)
5. **Alice** reviews the PR — happy with her assignments
6. **Bob** reviews his assignments — lightweight tasks for the OOO week
7. **Charlie** merges — Sprint 2 begins

**Time for the whole ceremony: ~20 minutes of async review, 0 synchronous meetings.**
