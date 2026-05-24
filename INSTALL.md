# Scraut — Quick Start

## Option A: Automated setup (recommended)

```bash
npx create-scraut
```

Answer 6 questions. Takes 5 minutes.

## Option B: Manual setup

1. Clone or fork this repository
2. Edit `scraut.yml` with your team details
3. Run: `pip install -r requirements.txt`
4. Run: `python scripts/setup/create_labels.py YOUR-ORG/YOUR-REPO`
5. Run: `python scripts/setup/setup_github_projects.py YOUR-ORG`
6. Run: `python scripts/sprint/create_sprint.py --sprint 1 --repo YOUR-ORG/YOUR-REPO`
7. Set GitHub Secrets (see below)
8. Enable GitHub Pages: Settings → Pages → Source: GitHub Actions
9. Push to main

## Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `SLACK_WEBHOOK` | Slack channel webhook URL |
| `SLACK_BOT_TOKEN` | Slack bot token (for personal DMs) |
| `SCRAUT_GITHUB_TOKEN` | PAT for reading connected repos |

## Daily usage

**Morning standup (developer):**
1. Receive Slack DM at 7:55am with link to your standup file
2. Click link → pencil icon is already focused
3. Fill in Today and Blockers (Yesterday is pre-filled from your commits)
4. Commit — done in 90 seconds

**Non-technical team member:**
1. Visit `https://your-org.github.io/scraut/form.html`
2. Fill in the form — no GitHub account needed
3. Click Submit

**View team status:**
```bash
scraut status        # from terminal
```
Or visit: `https://your-org.github.io/scraut/`

## CLI commands

```bash
scraut standup       # Open today's standup file in browser
scraut status        # Show sprint health and milestone status
scraut blocker "text"  # Add a blocker to your standup
scraut velocity      # Show sprint velocity data
```

## Agent mode (optional)

Agent mode is disabled by default. To enable AI agent coordination:

1. Set `agents.enabled: true` in `scraut.yml`
2. Enable individual agent roles under `agents.roles`
3. Set `ANTHROPIC_API_KEY` in GitHub Secrets
4. Trigger `.github/workflows/agent-orchestrator.yml` manually to test

See `07-AGENT-MODE.md` for full documentation.
