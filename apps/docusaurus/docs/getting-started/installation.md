---
sidebar_position: 2
---

# Installation

There are two ways to set up Scraut. Both produce identical results — choose the one that fits your workflow.

---

## Option A — `npx create-scraut` (recommended)

The interactive Node.js wizard handles everything: it clones the Scraut repository, asks 9 questions about your team, and scaffolds all configuration and workspace template files in one step.

### Quickstart

```bash
npx create-scraut my-team
cd my-team
```

That's it. The wizard clones [github.com/aldhosutra/scraut](https://github.com/aldhosutra/scraut) into `./my-team/`, then immediately starts the interactive prompts.

:::tip Running from an empty directory
If you prefer to clone yourself first:
```bash
mkdir my-team && cd my-team
npx create-scraut
```
When the current directory is empty, the wizard clones Scraut into it automatically.
:::

:::tip Already inside a cloned repo
If you ran `git clone https://github.com/aldhosutra/scraut.git my-team && cd my-team` manually, you can run the wizard from inside:
```bash
node apps/create-scraut/bin/create-scraut.js
```
The wizard detects it's already inside a Scraut repository and skips the clone step.
:::

### The wizard prompts

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
  Starting sprint number (1 for a brand-new team): 1
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
my-team/
├── .github/workflows/          ← 28 automation workflows
├── apps/
│   ├── automation/             ← Python automation layer
│   ├── create-scraut/          ← npm wizard
│   └── portal/                 ← visibility portal
├── workspace/
│   ├── scraut.yml              ← your configuration
│   ├── sprint/001/
│   │   ├── standup/TODAY/
│   │   │   ├── alice.md        ← standup template for Alice
│   │   │   ├── bob.md
│   │   │   └── charlie.md
│   │   ├── retrospective/
│   │   │   ├── alice.md        ← retro template for Alice
│   │   │   ├── bob.md
│   │   │   └── charlie.md
│   │   ├── meta.md             ← sprint metadata
│   │   └── grooming/backlog-ideas.md
│   ├── team/capacity.md        ← team availability template
│   ├── okr/okr.md              ← OKR template
│   ├── customer/feedback.md    ← customer feedback log
│   └── milestones/README.md    ← milestone format guide
└── .scraut/                    ← bot-generated output (empty until workflows run)
```

---

## Option B — `scraut init` (Python CLI)

If you prefer Python, clone the repo manually and run the Python wizard:

### Step 1: Clone

```bash
git clone https://github.com/aldhosutra/scraut.git my-team
cd my-team
```

### Step 2: Install Python dependencies

```bash
pip install -r apps/automation/requirements.txt
```

### Step 3: Run the wizard

```bash
scraut init
```

The prompts are identical to the npm wizard. Same output, same template files.

---

## After setup

Regardless of which option you used, you now have:
- `workspace/scraut.yml` — your configuration file
- Template workspace files so every team member sees the expected format
- `.github/workflows/` — 28 automation workflows ready to activate

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
