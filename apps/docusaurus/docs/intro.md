---
id: intro
slug: /
sidebar_position: 1
---

# What is Scraut?

**Scraut** (Scrum Automation) is a fully automated Scrum system built on GitHub infrastructure. It replaces Scrum-management apps and reduces ceremony overhead by treating **text files as the single source of truth** and letting GitHub Actions + an LLM do the rest.

> **One sentence:** Text files in — automation out.

---

## The core idea

Traditional Scrum tools require you to:
- Log into a separate platform every morning
- Manually update ticket statuses
- Copy-paste information between Slack, GitHub, and your PM tool
- Run stand-up calls even when updates are predictable

Scraut flips this model. Your team edits simple Markdown files directly in GitHub. Every commit triggers the right workflow automatically — summaries are generated, Slack is notified, the board is updated, blockers are escalated.

**Your team stays in GitHub. Everything else is handled.**

---

## Architecture overview

```
┌─────────────────────────────────────────────────────┐
│                   Your GitHub Repo                   │
│                                                      │
│  workspace/          ← Human-edited source of truth  │
│  ├── sprint/01/                                      │
│  │   ├── standup/2026-05-24/alice.md  ← Alice edits  │
│  │   ├── retrospective/alice.md       ← Alice edits  │
│  │   └── meta.md                      ← SM edits     │
│  ├── milestones/v2.0.md               ← PM edits     │
│  ├── team/capacity.md                 ← SM edits     │
│  └── okr/okr.md                       ← PO edits     │
│                                                      │
│  .scraut/            ← Bot-generated output          │
│  ├── sprint/01/standup/summary/       ← LLM writes   │
│  ├── sprint/01/review/                ← LLM writes   │
│  ├── insights/                        ← LLM writes   │
│  └── suggestions/active/             ← LLM writes   │
└─────────────────────────────────────────────────────┘
         │ git push triggers
         ▼
┌─────────────────────────────────────────────────────┐
│              GitHub Actions Workflows                │
│                                                      │
│  daily-standup.yml   → summarise standups → Slack    │
│  sprint-planning.yml → generate sprint plan PR       │
│  suggestion-detect   → detect process patterns       │
│  visibility-engine   → sync GitHub Projects board    │
│  portal-publish.yml  → deploy GitHub Pages dashboard │
└─────────────────────────────────────────────────────┘
```

---

## Key features

| Feature | How it starts | What it does |
|---------|--------------|-------------|
| **Morning Notifications** | ⏱️ 7:55 AM weekdays | DMs each team member their standup link |
| **Daily Standup** | ⚡ Push to standup file | Bot summarises all standups and posts to Slack |
| **Issue Triage** | ⚡ New issue opened | Auto-labels type and priority with LLM |
| **PR Enrichment** | ⚡ PR opened | Fills PR description with acceptance criteria |
| **Definition of Done** | ⚡ Issue closed | Checks DoD criteria against linked PRs |
| **Backlog Grooming** | ⏱️ Every Wednesday | AI prioritises unlabelled issues mid-sprint |
| **Velocity Tracking** | ⚡ After sprint review | Calculates and tracks story point velocity |
| **Visibility Portal** | ⏱️ Every 30 minutes | GitHub Pages dashboard synced from text files |
| **Milestone Planning** | ⚡ Push to milestone file | Decomposes milestones; generates health forecasts |
| **Incident to Backlog** | ⚡ Push action-items.md | Converts incident action items to GitHub issues |
| **Weekly Digest** | ⏱️ Monday 8:00 AM | Sends stakeholder summary to Slack + email |
| **Suggestions System** | ⚡ After sprint review | Detects recurring pain points; proposes improvements |
| **Repo Sync** | ⏱️ Daily 8:00 AM | Pulls code activity from connected repos |
| **Sprint Planning** | 🖱️ SM triggers manually | AI generates planning PR from backlog + capacity |
| **Sprint Review** | 🖱️ SM triggers manually | Review document from closed issues |
| **Retrospective** | 🖱️ SM triggers manually | AI synthesises per-person retros into team themes |
| **Agent Mode** | ⏱️ Every 4 hours | Fully autonomous AI agents that implement tasks |

**Key:** ⏱️ Scheduled &nbsp;·&nbsp; ⚡ Triggered by a GitHub event &nbsp;·&nbsp; 🖱️ SM triggers from Actions tab

---

## Who is Scraut for?

- **Small to medium engineering teams** (2–20 developers) using GitHub
- Teams that want **Scrum ceremonies without ceremony overhead**
- Teams that dislike switching between GitHub and a separate PM tool
- Teams open to using an LLM as their "Scrum Master assistant"

---

## File zones

Scraut enforces a strict separation between human-written and bot-written content:

| Zone | Path | Who writes | Rule |
|------|------|-----------|------|
| Human input | `workspace/` | Team members | Never overwritten by bot |
| Agent input | `workspace/sprint/NN/standup/DATE/agent-*.md` | AI agents | Same format as humans |
| Bot-generated | `.scraut/` | GitHub Actions | `<!-- BOT-GENERATED -->` header |

This means **you can always trust what's in `workspace/`** — Scraut never modifies files a human has written.

---

## Ready to start?

Head to [Prerequisites →](./getting-started/prerequisites)
