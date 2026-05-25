---
sidebar_position: 3
---

# GitHub Actions Workflows

All Scraut automation runs as GitHub Actions workflows. This page covers every workflow, its trigger type, and what it does.

---

## Trigger types at a glance

Scraut has three trigger categories. Understanding which is which tells you what your team needs to do (and what you can ignore).

### 🖱️ Manual — SM triggers from Actions tab

These three workflows require a human to go to **Actions → [workflow name] → Run workflow**. They mark deliberate sprint boundaries — moments where the team intentionally starts or closes a sprint together.

| Workflow | When to trigger |
|----------|----------------|
| **Sprint Planning** | At the start of each new sprint |
| **Sprint Review** | At the end of each sprint (before retrospective) |
| **Sprint Retrospective** | At the end of each sprint (after review) |

Everything else is automatic.

---

### ⏱️ Automatic — Scheduled (time-based)

These workflows fire on a cron schedule. No action needed from your team.

| Workflow | Schedule | What it does |
|----------|----------|-------------|
| **Morning Notification** | 7:55 AM weekdays | Slack DM to each member with standup link |
| **Daily Template Reset** | ~2:00 AM weekdays | Creates today's standup file for each member |
| **Repo Sync** | 8:00 AM weekdays | Pulls commit/PR activity from connected repos |
| **Daily Standup Summary** | 9:00 AM weekdays | Summarises standups, posts to Slack |
| **Backlog Grooming** | Wednesday 9:00 AM | Labels unlabelled issues, checks scope creep |
| **Visibility Engine** | Every 30 minutes | Syncs GitHub Projects board from text files |
| **Weekly Digest** | Monday 8:00 AM | Stakeholder summary → Slack + email |
| **Suggestion Measurement** | Monday morning | Measures impact of implemented suggestions |
| **Generate Insights** | 1st of month + after sprint review | Cross-sprint pattern analysis |
| **Agent Orchestrator** | Every 4 hours, weekdays | Dispatches work to AI agents (if enabled) |
| **Agent Specialists** | Every 4 hours, weekdays | Backend/frontend/test/review agents (if enabled) |

:::info Times are approximate
All times are based on UTC crons. The exact local time depends on your `sprint.timezone` setting. The crons are hardcoded in `.github/workflows/` — adjust them if your team is far from UTC+7 (Jakarta).
:::

---

### ⚡ Automatic — Event-driven (fires on GitHub events)

These workflows fire when something happens in the repo — a push, an issue opening, a PR merge. You trigger them indirectly just by doing your normal work.

| Workflow | What triggers it | What it does |
|----------|-----------------|-------------|
| **Daily Standup Summary** | Push to `workspace/sprint/*/standup/**` | Runs the standup summary immediately on push (in addition to the scheduled run) |
| **Issue Triage** | New issue opened | Labels type and priority with LLM |
| **PR Linker** | PR opened or edited | Fills PR description with acceptance criteria from linked issue |
| **PR Close Stories** | PR merged | Closes linked sprint issues, applies `dod:pending` |
| **Definition of Done** | Issue closed | Checks DoD criteria against linked PRs |
| **Sprint Plan PR** | Planning PR merged | Applies `in-sprint` labels, links issues to milestone |
| **Estimation Tally** | Comment on issue | Starts or tallies emoji story point vote |
| **Milestone Planning** | Push to `workspace/milestones/*/milestone.md` | Decomposes milestone, generates health forecast |
| **Milestone Response** | Comment on milestone issue | Updates milestone health after sprint |
| **Incident to Backlog** | Push to `workspace/sprint/*/incidents/action-items.md` | Creates GitHub issues from action items |
| **Visibility Engine** | Push to standup/sprint files | Syncs board immediately on push (in addition to schedule) |
| **Portal Publish** | Push to `apps/portal/` | Deploys dashboard to GitHub Pages |
| **Suggestion Detection** | Sprint Review workflow completes | Detects recurring patterns → proposes improvements |
| **Generate Insights** | Sprint Review workflow completes | Cross-sprint pattern analysis (also runs on schedule) |
| **CI** | Push or PR | Runs linting, smoke tests, unit and integration tests |

---

## Sprint lifecycle — who triggers what

A full sprint from start to finish:

```
SPRINT START
  🖱️  SM: Actions → Sprint Planning → Run workflow
      → sprint/NN/ folder created, planning PR opened

DURING SPRINT (all automatic)
  ⏱️  Daily: standup templates created, summaries posted to Slack
  ⚡  On new issue: LLM labels type + priority
  ⚡  On PR open: PR description enriched with acceptance criteria
  ⚡  On PR merge: linked issues closed, DoD check triggered
  ⏱️  Wednesday: backlog groomed
  ⏱️  Every 30min: board synced

SPRINT END
  🖱️  SM: Actions → Sprint Review → Run workflow
      → review doc generated, sprint counter incremented
      → (automatically) suggestion detection fires
      → (automatically) insights generated

  🖱️  SM: Actions → Sprint Retrospective → Run workflow
      → per-member retros synthesised into team themes

NEXT SPRINT
  🖱️  SM: Actions → Sprint Planning → Run workflow (repeat)
```

---

## Detailed workflow reference

### Sprint Planning — `sprint-planning.yml`
- **Trigger:** 🖱️ Manual (`workflow_dispatch`)
- **Inputs:** `sprint_num` (required), `repo` (required, `org/repo` format)
- **What it does:** Creates `workspace/sprint/NN/` folder structure, GitHub milestone, LLM-generated planning PR with backlog + capacity analysis

### Sprint Review — `sprint-review.yml`
- **Trigger:** 🖱️ Manual (`workflow_dispatch`)
- **Inputs:** `sprint_num` (required), `repo` (required)
- **What it does:** Generates review document from closed issues and standup history, increments `current_sprint` in `scraut.yml`

### Sprint Retrospective — `sprint-retrospective.yml`
- **Trigger:** 🖱️ Manual (`workflow_dispatch`)
- **Inputs:** `sprint_num` (required)
- **What it does:** Reads all `workspace/sprint/NN/retrospective/*.md` files, LLM synthesises themes and action items → `.scraut/sprint/NN/review/retro-synthesis.md`

---

### Morning Notification — `morning-notification.yml`
- **Trigger:** ⏱️ Schedule (7:55 AM weekdays)
- **What it does:** Sends personal Slack DM to each member with `slack_id` set, containing their standup file link. Requires `SLACK_BOT_TOKEN`.

### Daily Template Reset — `template-reset.yml`
- **Trigger:** ⏱️ Schedule (1:55 AM UTC weekdays) + `workflow_dispatch`
- **What it does:** Creates `workspace/sprint/NN/standup/YYYY-MM-DD/<login>.md` for each member. Never overwrites existing files. Commits with `[skip ci]`.

### Daily Standup Summary — `daily-standup.yml`
- **Trigger:** ⏱️ Schedule (9:00 AM weekdays) + ⚡ push to `workspace/sprint/*/standup/**` + `workflow_dispatch`
- **Inputs (dispatch):** `date` (optional, defaults to today)
- **What it does:** Reads all standup files for the day, LLM generates unified summary → `.scraut/sprint/NN/standup/summary/DATE.md` → posts to Slack

### Repo Sync — `repo-sync.yml`
- **Trigger:** ⏱️ Schedule (8:00 AM weekdays) + `workflow_dispatch`
- **What it does:** Fetches commits, PRs, CI status from connected repos (configured in `scraut.yml` under `repos:`). Requires `SCRAUT_GITHUB_TOKEN`.

### Backlog Grooming — `backlog-grooming.yml`
- **Trigger:** ⏱️ Schedule (Wednesday 9:00 AM) + `workflow_dispatch`
- **What it does:** Labels unlabelled backlog issues with type/priority, checks for scope creep, processes `workspace/sprint/NN/grooming/backlog-ideas.md`

---

### Issue Triage — `issue-triage.yml`
- **Trigger:** ⚡ `issues: [opened]`
- **What it does:** Classifies the new issue with `story`/`bug`/`task`/`spike`/`chore` and `p:high`/`p:medium`/`p:low` labels via LLM

### Estimation Tally — `estimation-tally.yml`
- **Trigger:** ⚡ `issue_comment` (on "estimate this" or emoji reactions)
- **What it does:** Posts emoji voting prompt to start estimation, or tallies reactions and applies `sp:N` label

### PR Linker — `pr-linker.yml`
- **Trigger:** ⚡ `pull_request: [opened, edited]`
- **What it does:** Reads linked issues from PR body, enriches PR description with acceptance criteria

### PR Close Stories — `pr-close-stories.yml`
- **Trigger:** ⚡ `pull_request: [closed]` (merged only)
- **What it does:** Closes linked `in-sprint` issues, applies `dod:pending` label

### Definition of Done — `dod-check.yml`
- **Trigger:** ⚡ `issues: [closed]`
- **What it does:** LLM checks DoD criteria against linked PRs, applies `dod:approved` or comments with unmet criteria

### Sprint Plan PR — `sprint-plan-pr.yml`
- **Trigger:** ⚡ `pull_request: [closed]` (planning PRs only)
- **What it does:** On merge of a planning PR, applies `in-sprint` label to all listed issues and links them to the sprint milestone

---

### Visibility Engine — `visibility-engine.yml`
- **Trigger:** ⚡ Push to standup/sprint files + ⏱️ every 30 minutes
- **What it does:** Derives board state from text files, syncs GitHub Projects board, writes `apps/portal/data.json`

### Portal Publish — `portal-publish.yml`
- **Trigger:** ⚡ Push to `apps/portal/` + `workflow_dispatch`
- **What it does:** Deploys visibility dashboard to GitHub Pages

### Weekly Digest — `weekly-digest.yml`
- **Trigger:** ⏱️ Schedule (Monday 8:00 AM) + `workflow_dispatch`
- **What it does:** Generates stakeholder summary from sprint progress, posts to Slack and optionally sends email

### Generate Insights — `generate-insights-workflow.yml`
- **Trigger:** ⚡ After Sprint Review completes (`workflow_run`) + ⏱️ first of month + `workflow_dispatch`
- **What it does:** Cross-sprint pattern analysis → `.scraut/insights/`

---

### Milestone Planning — `milestone-planning.yml`
- **Trigger:** ⚡ Push to `workspace/milestones/*/milestone.md`
- **What it does:** Decomposes milestone into epics, calculates health forecast, posts risk alerts

### Milestone Response — `milestone-respond.yml`
- **Trigger:** ⚡ Comment on milestone planning issues
- **What it does:** Updates milestone health estimates based on sprint completion

### Incident to Backlog — `incident-to-backlog.yml`
- **Trigger:** ⚡ Push to `workspace/sprint/*/incidents/action-items.md`
- **What it does:** Parses action items file, creates GitHub issues for each item

---

### Suggestion Detection — `suggestion-detect.yml`
- **Trigger:** ⚡ After Sprint Review completes (`workflow_run`) + `workflow_dispatch`
- **What it does:** Runs pattern detectors across sprint history, generates improvement suggestions in `.scraut/suggestions/active/`

### Suggestion Measurement — `suggestion-measure.yml`
- **Trigger:** ⏱️ Schedule (Monday morning) + `workflow_dispatch`
- **What it does:** Measures impact of implemented suggestions, moves to `resolved/` with outcome data

---

### Agent Orchestrator — `agent-orchestrator.yml`
- **Trigger:** ⏱️ Schedule (every 4 hours, weekdays) + `workflow_dispatch`
- **What it does:** Checks agent mode config, assigns issues to agents, coordinates handoffs. Only runs if `agents.enabled: true`.

### Agent Specialists — `agent-backend.yml`, `agent-frontend.yml`, `agent-test.yml`, `agent-review.yml`
- **Trigger:** ⏱️ Schedule (every 4 hours, weekdays, 30 min after orchestrator) + `workflow_dispatch`
- **What it does:** Each agent implements assigned issues in its specialty area, submits standup, escalates when blocked

---

### CI — `test-ci.yml`
- **Trigger:** ⚡ Push and PR to `main`
- **What it does:** Runs actionlint, flake8, import smoke tests, unit tests, integration tests

### Docs Build — `docs-build.yml`
- **Trigger:** ⚡ Push to `apps/docusaurus/**` + `workflow_dispatch`
- **What it does:** Builds Docusaurus docs to `docs/`, commits with `[skip ci]`

---

## Workflow permissions

All workflows use `GITHUB_TOKEN` (auto-provided by GitHub). Additional secrets needed:

| Workflow | Additional secret(s) required |
|----------|------------------------------|
| LLM workflows | `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` or `GOOGLE_API_KEY` |
| Morning DM | `SLACK_BOT_TOKEN` |
| Slack channel posts | `SLACK_WEBHOOK` |
| Repo sync | `SCRAUT_GITHUB_TOKEN` |
| Weekly email | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` |
