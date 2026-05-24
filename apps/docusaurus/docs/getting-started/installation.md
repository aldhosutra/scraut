---
sidebar_position: 2
---

# Installation

There are two ways to set up Scraut. Both produce identical results — choose the one that fits your workflow.

---

## Option A — `npx create-scraut` (recommended for new projects)

The interactive Node.js wizard walks you through every question and writes all configuration in one step.

### Step 1: Clone the Scraut template

```bash
git clone https://github.com/aldhosutra/scraut.git my-team-scraut
cd my-team-scraut
```

### Step 2: Run the wizard

```bash
node apps/create-scraut/bin/create-scraut.js
```

Or if you install it globally via npm:

```bash
npx create-scraut
```

The wizard asks 9 questions:

```
  Scraut Setup Wizard

  GitHub repository (org/repo): myorg/my-repo
  Team member GitHub logins (comma-separated): alice,bob,charlie
  Product owner login: alice
  Scrum master login: bob
  Slack channel: #scraut-bot
  Sprint length:
  ❯ 2 weeks (14 days)
    1 week  (7 days)
    3 weeks (21 days)
  Timezone (IANA format, e.g. UTC, Asia/Jakarta): Asia/Jakarta
  LLM provider:
  ❯ anthropic
    openai
    gemini
    ollama
  Slack webhook URL (Enter to skip): https://hooks.slack.com/...
```

### What the wizard creates

After answering, you'll have:

```
workspace/
├── scraut.yml                          ← your configuration
├── sprint/01/
│   ├── standup/2026-05-24/
│   │   ├── alice.md                    ← standup template for Alice
│   │   ├── bob.md                      ← standup template for Bob
│   │   └── charlie.md
│   ├── retrospective/
│   │   ├── alice.md                    ← retro template for Alice
│   │   ├── bob.md
│   │   └── charlie.md
│   ├── meta.md                         ← sprint metadata
│   └── grooming/backlog-ideas.md
├── team/capacity.md                    ← team availability template
├── okr/okr.md                          ← OKR template
├── customer/feedback.md                ← customer feedback log
└── milestones/README.md                ← milestone format guide
.scraut/                                ← bot-generated output dirs
```

---

## Option B — `scraut init` (Python CLI)

If you prefer Python and already have the repo checked out:

### Step 1: Install Python dependencies

```bash
pip install -r apps/automation/requirements.txt
```

### Step 2: Run the wizard

```bash
python -m scraut.cli.cli init
# or, after pip install:
scraut init
```

The prompts are identical to the npm wizard. Same output, same template files.

---

## After setup

Regardless of which option you used, you now have:
- `workspace/scraut.yml` — your configuration file
- Template workspace files so every team member sees the expected format

**Next steps:**

1. [Configure `scraut.yml`](./configuration) — fill in `slack_id` and `email` for each team member
2. [Set up GitHub Secrets and Pages](./github-setup) — required for workflows to run
3. [Launch Sprint 1](./first-sprint) — kick off your first sprint

---

## Upgrading Scraut

Scraut is a cloned repository, so upgrading is a `git pull`:

```bash
git remote add upstream https://github.com/aldhosutra/scraut.git
git fetch upstream
git merge upstream/main
```

Your `workspace/` files are never touched by Scraut automation, so they survive upgrades safely.
