---
sidebar_position: 3
---

# GitHub Actions Workflows

All Scraut automation runs as GitHub Actions workflows. This reference lists every workflow, its trigger, inputs, and what it does.

---

## Ceremony workflows

### `sprint-planning.yml`
**Name:** Scraut — Sprint Planning
**Trigger:** Manual (`workflow_dispatch`)
**Inputs:** `sprint_num`, `repo`
**What it does:** Creates sprint folder structure, GitHub milestone, generates planning PR with AI-suggested issue selection and story assignments.

### `sprint-review.yml`
**Name:** Scraut — Sprint Review
**Trigger:** Manual (`workflow_dispatch`)
**Inputs:** `sprint_num`, `repo`
**What it does:** Generates review document from closed issues and standup history, increments sprint counter, triggers suggestion detection.

### `sprint-retrospective.yml`
**Name:** Scraut — Sprint Retrospective
**Trigger:** Manual (`workflow_dispatch`)
**Inputs:** `sprint_num`
**What it does:** Reads all per-member retro files, calls LLM to synthesise themes and action items, writes synthesis to `.scraut/sprint/NN/review/retro-synthesis.md`.

---

## Daily workflows

### `daily-standup.yml`
**Name:** Scraut — Daily Standup Summary
**Trigger:** Schedule (9:00 AM weekdays) + `workflow_dispatch`
**Inputs:** `date` (optional, defaults to today)
**What it does:** Reads all standup files for the date, generates LLM summary, commits to `.scraut/sprint/NN/standup/summary/DATE.md`, posts to Slack.

### `morning-notification.yml`
**Name:** Scraut — Morning Notification
**Trigger:** Schedule (7:55 AM weekdays) + `workflow_dispatch`
**What it does:** Sends a personal Slack DM to each team member with `slack_id` configured, containing their standup file link.

### `template-reset.yml`
**Name:** Scraut — Template Reset (standup templates)
**Trigger:** Schedule (9:00 AM weekdays) + `workflow_dispatch`
**What it does:** Creates standup template files for today for each team member (idempotent — never overwrites existing files).

---

## Backlog workflows

### `backlog-grooming.yml`
**Name:** Scraut — Backlog Grooming
**Trigger:** Schedule (Wednesday 9:00 AM) + `workflow_dispatch`
**What it does:** Prioritises unlabelled backlog issues with LLM, checks for scope creep, processes backlog-ideas.md.

### `issue-triage.yml`
**Name:** Scraut — Issue Triage
**Trigger:** `issues: [opened]`
**What it does:** Classifies new issues with type and priority labels using LLM.

### `estimation-tally.yml`
**Name:** Scraut — Estimation Tally
**Trigger:** `issue_comment` (on "estimate this") + `workflow_dispatch`
**Inputs:** `issue_number`
**What it does:** Posts emoji voting comment or tallies reactions and applies `sp:N` label.

---

## PR workflows

### `pr-linker.yml`
**Name:** Scraut — PR Linker
**Trigger:** `pull_request: [opened, edited]`
**What it does:** Reads linked issues from PR body, enriches PR description with acceptance criteria and test instructions.

### `pr-close-stories.yml`
**Name:** Scraut — Close Sprint Stories on PR Merge
**Trigger:** `pull_request: [closed]` (merged only)
**What it does:** When a PR is merged, closes linked `in-sprint` issues and applies `dod:pending` label for DoD check.

### `dod-check.yml`
**Name:** Scraut — Definition of Done Check
**Trigger:** `issues: [closed]`
**What it does:** Checks DoD criteria for closed sprint issues using LLM analysis of linked PRs.

### `sprint-plan-pr.yml`
**Name:** Scraut — Sprint Plan PR Actions
**Trigger:** `pull_request: [closed]` (planning PRs only)
**What it does:** On merge of planning PR, applies `in-sprint` labels and links issues to GitHub milestone.

---

## Monitoring and visibility

### `visibility-engine.yml`
**Name:** Scraut — Visibility Engine
**Trigger:** Push to standup/sprint files + schedule (every 30 min)
**What it does:** Derives board state from text files, syncs GitHub Projects, writes `apps/portal/data.json`.

### `portal-publish.yml`
**Name:** Scraut — Publish Portal (GitHub Pages)
**Trigger:** Push to `apps/portal/`
**Permissions:** `pages: write`, `id-token: write`
**What it does:** Deploys `apps/portal/` to GitHub Pages.

### `generate-insights-workflow.yml`
**Name:** Scraut — Generate Insights
**Trigger:** `workflow_dispatch`
**What it does:** Generates cross-sprint insights report in `.scraut/insights/`.

---

## Milestone workflows

### `milestone-planning.yml`
**Name:** Scraut — Milestone Planning
**Trigger:** Push to `workspace/milestones/*/milestone.md`
**What it does:** Decomposes milestone into epics, calculates health forecast, posts risk alerts.

### `milestone-respond.yml`
**Name:** Scraut — Milestone Response
**Trigger:** After sprint review
**What it does:** Updates milestone health after each sprint.

---

## Suggestions

### `suggestion-detect.yml`
**Name:** Scraut — Suggestion Detection
**Trigger:** After sprint review completes (`workflow_run: sprint-review`)
**What it does:** Runs pattern detectors across sprint history, generates process improvement suggestions.

### `suggestion-measure.yml`
**Name:** Scraut — Suggestion Measurement
**Trigger:** After sprint review (if suggestions are in `implemented/`)
**What it does:** Measures impact of implemented suggestions, moves to `resolved/` with outcome data.

---

## Repo sync

### `repo-sync.yml`
**Name:** Scraut — Repo Sync
**Trigger:** Schedule (8:00 AM weekdays) + `workflow_dispatch`
**What it does:** Fetches commits, PRs, and CI status from connected repos.

---

## Incident management

### `incident-to-backlog.yml`
**Name:** Scraut — Incident to Backlog
**Trigger:** Push to `.scraut/sprint/*/incidents/**/action-items.md`
**What it does:** Creates GitHub issues from incident action items.

---

## Agent workflows

### `agent-orchestrator.yml`
**Name:** Scraut — Agent Orchestrator
**Trigger:** Schedule (every 4 hours, weekdays) + `workflow_dispatch`
**What it does:** Checks agent mode config, dispatches work to specialist agents.

### `agent-backend.yml`, `agent-frontend.yml`, `agent-test.yml`, `agent-review.yml`
**Name:** Scraut — Agent [Specialty]
**Trigger:** Called by orchestrator or `workflow_dispatch`
**What it does:** Implements assigned issues in their specialty area.

---

## CI / developer workflows

### `test-ci.yml`
**Name:** Scraut CI
**Trigger:** Push and PR to main
**What it does:** Runs linting (actionlint, flake8), import smoke tests, unit tests, and integration tests (--help coverage).

---

## Workflow permissions summary

| Workflow | Needs write to repo? | Needs GitHub token? |
|----------|---------------------|-------------------|
| daily-standup | Yes (commits summary) | Auto |
| sprint-planning | Yes (creates PR) | Auto |
| agent-* | Yes (commits standup, opens PRs) | Auto |
| portal-publish | pages:write | Auto |
| All others | Yes (commits generated files) | Auto |
