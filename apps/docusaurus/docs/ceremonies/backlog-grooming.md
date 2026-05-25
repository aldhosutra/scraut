---
sidebar_position: 4
---

# Backlog Grooming

Backlog grooming happens automatically every Wednesday mid-sprint. Scraut reviews the current backlog, prioritises unlabelled issues, checks for scope creep, and posts recommendations to Slack — all without a meeting.

---

## Automatic mid-sprint grooming

**Trigger:** Every Wednesday at 9:00 AM (your timezone) — `cron: '0 2 * * 3'`
**Workflow:** `backlog-grooming.yml`
**Manual trigger:** Available via GitHub Actions UI

---

## What grooming does

```
Grooming workflow fires
  │
  ├─ prioritize_backlog.py
  │     Fetches all open issues NOT labeled in-sprint
  │     For each unlabelled issue:
  │       Calls LLM: "Suggest type (story/bug/task) and priority for this issue"
  │       Applies suggested labels
  │     Posts: "Labelled 5 new issues — see #scraut-bot for details"
  │
  ├─ scope_creep_check.py
  │     Counts in-sprint issues added after sprint planning
  │     If count > threshold: posts alert to SM
  │
  └─ Posts summary to #scraut-bot
```

---

## Prioritising the backlog

The **Product Owner** can also influence grooming by editing:

```
workspace/sprint/001/grooming/backlog-ideas.md
```

**Template:**

```markdown
# Backlog Ideas
<!-- Append new ideas below. Anyone can add. -->

## 2026-05-28
- Idea: Add CSV export for the analytics dashboard
  → Would help the data team extract reports without hitting the API
  → Priority: medium

## 2026-05-29
- Customer request (Jane at Acme): "Can we bulk-delete old projects?"
  → Mentioned in support ticket ST-445
  → Priority: high
```

When the grooming workflow runs, it reads this file and uses the ideas as context for issue prioritisation.

---

## Grooming output

Slack post in `#scraut-bot`:

```
🌿 Backlog Grooming — Sprint 01, Week 1

📋 Labelled 5 new issues:
  #44 CSV export for analytics (story, p:medium, sp:5)
  #45 Bulk delete projects (story, p:high, sp:3)
  #46 Fix null pointer in parser (bug, p:high, sp:2)
  #47 Update README (chore, p:low, sp:1)
  #48 Performance spike for dashboard (spike, p:medium, sp:3)

⚠️ Scope creep alert:
  3 issues added to sprint AFTER planning: #43, #44, #46
  Currently at 37 sp — 3 sp over sprint target (34 sp)
  Recommendation: defer #47 (sp:1, low priority) to backlog

💡 Backlog ideas processed: 2 ideas from backlog-ideas.md added as issues.
```

---

## Scope creep detection

If issues are added to a sprint after planning (by applying the `in-sprint` label mid-sprint), Scraut detects this and alerts:

- Posts warning to `#scraut-bot`
- Flags which issues were added post-planning
- Calculates whether the sprint is over capacity
- Recommends which issues to defer

---

## Manual grooming session

You can also trigger grooming manually at any time:

1. Go to **Actions** → **Scraut — Backlog Grooming**
2. Click **Run workflow** → **Run workflow**

Useful before sprint planning to ensure all backlog items are labelled.

---

## Scenario: Customer feedback triggers backlog update

**Characters:** Alice (product owner), the grooming bot

**Events:**

1. **Alice** receives customer feedback: "The export button is broken on Firefox"
2. **Alice** opens `workspace/sprint/001/grooming/backlog-ideas.md` and adds:
   ```markdown
   ## 2026-05-28
   - Bug: Export button broken on Firefox (reported by customer John at MegaCorp)
     → Repro: click export on any dashboard on Firefox 124
     → Priority: high (customer-facing bug)
   ```
3. **Alice** commits and pushes
4. **Wednesday arrives** — grooming runs automatically
5. Scraut creates a new issue: `[Bug] Export button broken on Firefox` with labels `bug`, `p:high`, `sp:2`
6. Slack post notifies the team
7. **Bob** picks up the issue for next sprint

**Time for Alice: 3 minutes to write the backlog idea. The rest is automatic.**
