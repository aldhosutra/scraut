# Scraut — Scrum Automation

> **Text files in. Automation out.**

Scraut is a fully automated Scrum system built entirely on GitHub infrastructure. Your team edits Markdown files. GitHub Actions + an LLM handle everything else — standup summaries, sprint planning, retro synthesis, velocity tracking, milestone health, and stakeholder reporting.

No separate PM tool. No synchronous stand-up calls. No manual status updates.

---

## How it works

```
workspace/sprint/01/standup/2026-05-24/alice.md   ← Alice edits this
                                    │
                                    │ git push
                                    ▼
                          GitHub Actions fires
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
             LLM summarises   Updates board   Posts to Slack
             all standups     from text files  #scraut-bot
                    │
                    ▼
      .scraut/sprint/01/standup/summary/2026-05-24.md
```

Every ceremony — planning, grooming, review, retro, estimation — follows the same pattern: **humans edit text files, automation does the rest.**

---

## Quickstart

### Option A — npm wizard (recommended)

```bash
npx create-scraut my-team
cd my-team
```

The wizard clones Scraut, asks 9 questions, and writes all config and workspace templates in one step.

### Option B — Python CLI

```bash
git clone https://github.com/aldhosutra/scraut.git my-team
cd my-team
pip install -r apps/automation/requirements.txt
scraut init
```

Both wizards ask 9 questions and produce:

```
workspace/
├── scraut.yml                 ← your config
├── sprint/01/
│   ├── standup/today/         ← standup templates, one per member
│   ├── retrospective/         ← retro templates, one per member
│   ├── grooming/backlog-ideas.md
│   └── meta.md
├── team/capacity.md
├── okr/okr.md
├── customer/feedback.md
└── milestones/README.md
```

Then [set your GitHub Secrets](#github-secrets) and trigger **sprint-planning** from the Actions tab.

---

## Day-to-day for team members

**Every morning:**

```bash
scraut standup         # opens your standup file in GitHub
# fill in Yesterday / Today / Blockers
git add workspace/sprint/ && git commit -m "standup: $(date +%F) [skip ci]" && git push
```

**When blocked:**

```bash
scraut blocker "Waiting on API credentials from infra team — blocked on #28"
git add workspace/sprint/ && git commit -m "standup: blocker [skip ci]" && git push
```

**Sprint health:**

```bash
scraut status          # sprint progress, milestone health, active suggestions
scraut velocity        # story point velocity and rolling average
```

---

## What gets automated

| Ceremony           | Trigger                  | What Scraut does                                   |
| ------------------ | ------------------------ | -------------------------------------------------- |
| Morning reminder   | 7:55 AM weekdays         | Slack DM to each member with standup link          |
| Daily standup      | Push to standup files    | LLM summarises all standups → Slack + `.scraut/`   |
| Backlog grooming   | Every Wednesday          | Labels unlabelled issues, checks scope creep       |
| Sprint planning    | SM clicks "Run workflow" | Reads backlog + capacity → creates planning PR     |
| Sprint review      | SM clicks "Run workflow" | Generates review doc from closed issues            |
| Retrospective      | SM clicks "Run workflow" | Synthesises per-member retros into team themes     |
| Velocity           | After sprint review      | Calculates completed sp, updates rolling average   |
| Milestone health   | Push to milestone files  | Forecasts completion date, flags risks             |
| Visibility portal  | Every 30 min / push      | Syncs GitHub Projects board, updates dashboard     |
| Suggestions        | After sprint review      | Detects recurring patterns → proposes improvements |
| Weekly digest      | Monday 8:00 AM           | Stakeholder summary → Slack + email                |
| Issue triage       | New issue opened         | Labels type and priority with LLM                  |
| PR enrichment      | PR opened                | Pulls AC from linked issue, fills PR description   |
| DoD check          | Issue closed             | Verifies Definition of Done criteria met           |
| Incident → backlog | Push action-items.md     | Creates GitHub issues from incident action items   |

---

## Repository layout

```
scraut/
├── .github/workflows/        ← 28 automation workflows
├── apps/
│   ├── automation/           ← Python automation layer (scraut CLI + scripts)
│   ├── create-scraut/        ← npm setup wizard (npx create-scraut)
│   ├── docusaurus/           ← Documentation source
│   ├── github-app/           ← GitHub App webhook handler (optional)
│   └── portal/               ← Visibility portal web app
├── docs/                     ← Built documentation (GitHub Pages)
├── workspace/                ← Human-editable source of truth ← edit here
└── .scraut/                  ← Bot-generated output ← never edit manually
```

**Rule:** `workspace/` is for humans. `.scraut/` is for bots. The board is a derived view — text files are the source of truth.

---

## GitHub Secrets

Set these in **Settings → Secrets and variables → Actions**:

| Secret                | Required?                       | What it's for                  |
| --------------------- | ------------------------------- | ------------------------------ |
| `ANTHROPIC_API_KEY`   | Required (or use OpenAI/Gemini) | All LLM-powered workflows      |
| `OPENAI_API_KEY`      | Alternative to Anthropic        | If using OpenAI provider       |
| `GOOGLE_API_KEY`      | Alternative to Anthropic        | If using Gemini provider       |
| `SLACK_WEBHOOK`       | Recommended                     | All Slack channel posts        |
| `SLACK_BOT_TOKEN`     | Optional                        | Personal morning standup DMs   |
| `SCRAUT_GITHUB_TOKEN` | Optional                        | Repo sync from connected repos |
| `SMTP_*`              | Optional                        | Weekly email digest            |

`GITHUB_TOKEN` is provided automatically — you don't need to add it.

---

## LLM providers

Scraut works with Anthropic, OpenAI, Gemini, Ollama, and any OpenAI-compatible endpoint (Groq, DeepSeek, LM Studio). Configure in `workspace/scraut.yml`:

```yaml
llm:
  provider: anthropic # anthropic | openai | gemini | ollama
  model: claude-sonnet-4-6
  base_url: "" # optional: custom endpoint
```

---

## Agent mode (optional)

Enable AI agents that participate as team members — claiming issues, writing code, opening PRs, and submitting standups:

```yaml
# workspace/scraut.yml
agents:
  enabled: true
  autonomy_level: supervised # supervised | semi-auto | full-auto
  roles:
    - id: agent-backend
      type: specialist
      specialty: backend
      enabled: true
```

Agents run on a 4-hour cycle, escalate when blocked, and participate in the same standup format as humans. Human checkpoints pause agents at sprint boundaries and escalations.

---

## Documentation

Full docs at **[aldhosutra.github.io/scraut](https://aldhosutra.github.io/scraut/)** — covers installation, every feature with worked scenarios, CLI reference, and configuration schema.

To run docs locally:

```bash
cd apps/docusaurus
npm install
npm start
```

---

## CLI reference

```bash
scraut init           # first-time setup wizard
scraut standup        # open today's standup file in GitHub
scraut status         # sprint health: progress, milestones, suggestions
scraut velocity       # story point velocity and rolling average
scraut blocker "..."  # add a blocker to today's standup
```

---

## Tech stack

| Layer           | Technology                           |
| --------------- | ------------------------------------ |
| Automation      | Python 3.11, GitHub Actions          |
| LLM             | Anthropic / OpenAI / Gemini / Ollama |
| CLI             | Click                                |
| npm wizard      | Node.js, Inquirer, Octokit           |
| Documentation   | Docusaurus                           |
| Portal          | GitHub Pages                         |
| Source of truth | Markdown files in `workspace/`       |

---

## Contributing

1. Fork and clone
2. `pip install -r apps/automation/requirements.txt`
3. `cd apps/automation && python -m pytest`

All scripts accept `--dry-run` and `--config` flags. See [CLAUDE.md](./CLAUDE.md) for architecture rules.

---

## License

MIT
