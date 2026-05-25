---
sidebar_position: 5
---

# Your First Sprint

With Scraut installed and GitHub configured, this guide walks you through launching Sprint 1 end-to-end.

---

## Overview of Sprint 1 launch

```
1. Fill in scraut.yml            ← you do this (1 min)
2. Edit your OKRs                ← Product Owner does this (10 min)
3. Create issues in GitHub       ← anyone does this (varies)
4. Trigger sprint-planning       ← Scrum Master clicks one button
5. Review planning PR            ← team reviews, SM merges
6. Sprint begins                 ← standups start automatically next morning
```

---

## 1. Fill in team details

Open `workspace/scraut.yml` and fill in the `slack_id` and `email` for each team member:

```yaml
team:
  members:
    - login: alice
      display: Alice Smith
      role: developer
      slack_id: U0123456789    # ← find this in Slack profile
      email: alice@example.com # ← for weekly digest
```

Also update the timezone to match your team:

```yaml
sprint:
  timezone: "Asia/Jakarta"  # ← your team's timezone
```

Commit and push:

```bash
git add workspace/scraut.yml
git commit -m "chore: fill in team details [skip ci]"
git push
```

---

## 2. Define your OKRs (Product Owner)

Open `workspace/okr/okr.md` and replace the placeholder content with your team's objectives:

```markdown
# Objectives & Key Results

## Objective 1: Launch v1.0 by end of Q2
### Key Result 1.1
- Target: 1,000 registered users
- Current: 0

### Key Result 1.2
- Target: < 2s p95 API response time
- Current: baseline TBD
```

Commit:
```bash
git add workspace/okr/
git commit -m "chore: define Q2 OKRs [skip ci]"
git push
```

---

## 3. Create your backlog issues

Create GitHub issues for all the work you're considering for Sprint 1. Use these conventions:

**Title format:** `[Story] As a user, I can reset my password`

**Labels to add:**
- Type: `story`, `bug`, `task`, `spike`, or `chore`
- Priority: `p:high`, `p:medium`, or `p:low`
- Story points (add after estimation): `sp:1`, `sp:2`, `sp:3`, `sp:5`, `sp:8`, or `sp:13`

:::tip Let Scraut triage issues for you
When you create a new issue, the **Issue Triage** workflow fires automatically and suggests type and priority labels using the LLM. You can accept or adjust.
:::

---

## 4. Trigger Sprint Planning (Scrum Master)

Once you have at least a few issues in the backlog:

1. Go to **Actions** → **Scraut — Sprint Planning**
2. Click **Run workflow**
3. Fill in:
   - **Sprint number**: `1`
   - **org/repo**: `myorg/my-repo`
4. Click **Run workflow**

**What happens:**
- Scraut creates the `workspace/sprint/001/` directory structure
- Calls the LLM with your backlog + team capacity from `workspace/team/capacity.md`
- Creates a GitHub PR titled `Sprint 1 Planning` with:
  - `workspace/sprint/001/meta.md` filled in with proposed issues
  - Story point assignments
  - Sprint goal suggestion

**Example PR content:**

```markdown
# Sprint 1 Planning

- Period: 2026-05-25 → 2026-06-07 (10 working days)
- Goal: Deliver user authentication and basic dashboard
- Team: Alice Smith, Bob Jones, Charlie Kim
- Committed: 34 story points across 8 issues
- Capacity: 40 sp available × 0.85 buffer = 34 sp

## Issues in sprint
| Issue | Title | Epic | SP | Assignee |
|-------|-------|------|----|---------|
| #12 | As a user, I can register | Auth | 3 | alice |
| #13 | As a user, I can log in | Auth | 2 | alice |
| #14 | Add password reset flow | Auth | 5 | bob |
...
```

---

## 5. Review and merge the planning PR

The whole team reviews the planning PR:
- Check that the goal makes sense
- Adjust story assignments if needed
- Edit `workspace/sprint/001/meta.md` directly in the PR

When everyone agrees, the Scrum Master merges it.

:::info What happens on merge
The `sprint-plan-pr.yml` workflow fires, applies the `in-sprint` label to all listed issues, and creates the corresponding GitHub milestone.
:::

---

## 6. Sprint begins

The next morning at 7:55 am (your configured timezone), every team member gets a Slack DM:

> Good morning Alice! Time for your standup 🌅
> Open your file: `workspace/sprint/001/standup/2026-05-26/alice.md`
> Sprint 1 ends in 14 days.

The team opens their standup files (via the link or `scraut standup`), fills them in, and pushes. Scraut takes care of the rest.

---

## Sprint 1 checklist

- [ ] `workspace/scraut.yml` — `slack_id` and `email` filled for all members
- [ ] `workspace/okr/okr.md` — team OKRs defined
- [ ] `workspace/team/capacity.md` — any OOO days noted
- [ ] GitHub Issues — initial backlog created
- [ ] GitHub Secrets — all required secrets set
- [ ] GitHub Labels — all labels created
- [ ] GitHub Pages — enabled in repo settings
- [ ] Sprint Planning workflow triggered and PR merged

---

## What's automated from here

Once Sprint 1 starts, Scraut runs on autopilot for everything during the sprint:

| When | What Scraut does automatically |
|------|-------------------------------|
| ⏱️ Every weekday ~2:00 AM | Creates today's standup file for each member |
| ⏱️ Every weekday 7:55 AM | Sends morning standup DM to each member |
| ⏱️ Every weekday 9:00 AM | Summarises standups → `.scraut/sprint/001/standup/summary/` → posts to Slack |
| ⚡ When a new issue opens | Labels type and priority with LLM |
| ⚡ When a PR opens | Fills PR description from linked issue acceptance criteria |
| ⚡ When a PR merges | Closes linked sprint issues, triggers DoD check |
| ⚡ When an issue closes | Checks Definition of Done criteria |
| ⏱️ Every Wednesday | Backlog grooming — prioritises unlabelled issues, checks scope creep |
| ⏱️ Every 30 minutes | Syncs board state from text files |
| ⏱️ Every Monday | Sends weekly stakeholder digest |

Your team's only job during the sprint: **commit your standup file each morning.**

---

## End of sprint — manual steps required

Three ceremonies at the end of each sprint require the Scrum Master to trigger them manually from the **Actions** tab:

:::warning These do not run automatically
Sprint Review, Sprint Retrospective, and the next Sprint Planning must be triggered by the SM. They mark deliberate sprint boundaries.
:::

**Step 1 — Sprint Review** (SM triggers)

Go to **Actions → Scraut — Sprint Review → Run workflow**

Fill in:
- Sprint number: `1`
- org/repo: `myorg/my-repo`

This generates `.scraut/sprint/001/review/sprint-review.md` from closed issues, increments `current_sprint` in `scraut.yml`, and automatically kicks off suggestion detection.

**Step 2 — Sprint Retrospective** (SM triggers)

Go to **Actions → Scraut — Sprint Retrospective → Run workflow**

Ask each team member to fill in their retro file first:
```
workspace/sprint/001/retrospective/<login>.md
```

Then trigger the workflow with sprint number `1`. It synthesises all per-member retros into a team themes document.

**Step 3 — Next Sprint Planning** (SM triggers, start of new sprint)

Go to **Actions → Scraut — Sprint Planning → Run workflow**

Fill in the new sprint number (`2`, `3`, etc.). This creates the next sprint folder, opens a new planning PR, and the cycle repeats.
