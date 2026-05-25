# create-scraut

> Set up [Scraut](https://github.com/aldhosutra/scraut) — fully automated Scrum on GitHub — in one command.

```bash
npx create-scraut my-team
```

That's it. The wizard clones the Scraut repository, asks 9 questions about your team, and scaffolds everything.

---

## What is Scraut?

Scraut is a text-file-first Scrum system built entirely on GitHub infrastructure. Your team edits Markdown files. GitHub Actions + an LLM handle everything else — standup summaries, sprint planning, retro synthesis, velocity tracking, milestone health, and stakeholder reporting.

No separate PM tool. No synchronous stand-up calls. No manual status updates.

---

## Usage

### Create a new project directory

```bash
npx create-scraut my-team
cd my-team
```

### Set up in the current directory (must be empty)

```bash
mkdir my-team && cd my-team
npx create-scraut
```

### Already cloned the repo manually?

```bash
git clone https://github.com/aldhosutra/scraut.git my-team
cd my-team
node apps/create-scraut/bin/create-scraut.js
```

---

## What the wizard asks

```
  GitHub repository (org/repo):              myorg/my-repo
  Team member GitHub logins (comma-sep):     alice,bob,charlie
  Product owner login:                       alice
  Scrum master login:                        bob
  Slack channel:                             #scraut-bot
  Sprint length:                             2 weeks (14 days)
  Timezone:                                  Asia/Jakarta
  LLM provider:                              anthropic
  Slack webhook URL (Enter to skip):
```

---

## What you get

```
my-team/
├── .github/workflows/          ← 28 automation workflows
├── apps/automation/            ← Python scripts (scraut CLI)
├── workspace/
│   ├── scraut.yml              ← your configuration
│   ├── sprint/01/
│   │   ├── standup/TODAY/
│   │   │   ├── alice.md        ← standup template, one per member
│   │   │   └── bob.md
│   │   ├── retrospective/
│   │   │   ├── alice.md        ← retro template, one per member
│   │   │   └── bob.md
│   │   ├── meta.md
│   │   └── grooming/backlog-ideas.md
│   ├── team/capacity.md
│   ├── okr/okr.md
│   ├── customer/feedback.md
│   └── milestones/README.md
└── .scraut/                    ← bot-generated output (filled by workflows)
```

---

## What gets automated

| Ceremony           | Trigger                  | What Scraut does                                 |
| ------------------ | ------------------------ | ------------------------------------------------ |
| Morning reminder   | 7:55 AM weekdays         | Slack DM to each member with standup link        |
| Daily standup      | Push to standup files    | LLM summarises all standups → Slack + `.scraut/` |
| Backlog grooming   | Every Wednesday          | Labels issues, checks scope creep                |
| Sprint planning    | Manual trigger           | Reads backlog + capacity → creates planning PR   |
| Sprint review      | Manual trigger           | Generates review doc from closed issues          |
| Retrospective      | Manual trigger           | Synthesises per-member retros into team themes   |
| Velocity           | After sprint review      | Calculates story points, updates rolling average |
| Milestone health   | Push to milestone files  | Forecasts completion date, flags risks           |
| Issue triage       | New issue opened         | Labels type and priority with LLM                |
| PR enrichment      | PR opened                | Pulls AC from linked issue, fills PR description |

---

## After setup

1. Fill in `slack_id` and `email` for each member in `workspace/scraut.yml`
2. Set GitHub Secrets: `ANTHROPIC_API_KEY` (or OpenAI/Gemini), `SLACK_WEBHOOK`
3. Enable GitHub Actions: Settings → Actions → General → Allow all actions
4. Enable GitHub Pages: Settings → Pages → Branch: main, Folder: `/docs`
5. Push: `git add . && git commit -m "chore: scraut setup [skip ci]" && git push`
6. Trigger **sprint-planning** from the Actions tab

---

## Requirements

- Node.js 18+
- Git (for cloning)
- A GitHub repository

---

## Documentation

Full docs at **[aldhosutra.github.io/scraut](https://aldhosutra.github.io/scraut/)**

## License

MIT
