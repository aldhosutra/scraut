---
sidebar_position: 1
---

# Prerequisites

Before setting up Scraut, make sure you have the following ready.

---

## Required

### GitHub account and repository
Scraut lives inside a GitHub repository. You need:
- A GitHub account
- A new (or existing) repository where Scraut will run
- Permission to add **GitHub Secrets** and enable **GitHub Actions** in that repo

### Python 3.11+
The automation layer runs on Python.

```bash
python --version   # should print Python 3.11.x or 3.12.x
```

Install from [python.org](https://python.org) or via your package manager:
```bash
# macOS
brew install python@3.12

# Ubuntu/Debian
sudo apt install python3.12 python3.12-pip
```

### An LLM provider API key
Scraut calls an LLM for summarisation, planning, and synthesis tasks. You need at least one of:

| Provider | Env var | Where to get it |
|----------|---------|----------------|
| Anthropic (recommended) | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| OpenAI | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) |
| Google Gemini | `GOOGLE_API_KEY` | [aistudio.google.com](https://aistudio.google.com) |
| Ollama (local) | *(none)* | [ollama.ai](https://ollama.ai) |

You'll add this key as a **GitHub Secret** — it never touches your code.

---

## Recommended

### Slack workspace
Scraut posts standup summaries, sprint ceremony digests, and morning reminders to Slack. Without it, all output goes to `.scraut/` files only (still useful, just quieter).

You'll need:
- A Slack **incoming webhook** URL — create one at your Slack workspace's App settings
- Optionally a **Slack bot token** for personal DMs (morning standup reminders)

### Node.js 18+ (for `npx create-scraut`)
If you prefer the interactive npm wizard over the Python CLI:

```bash
node --version   # should print v18.x or higher
```

---

## Optional

### `scraut` CLI
The Python CLI gives you quick terminal shortcuts (`scraut standup`, `scraut status`, etc.). Install it after cloning:

```bash
pip install -r apps/automation/requirements.txt
```

---

## What you do NOT need

- A separate project management tool (Jira, Linear, etc.)
- A dedicated Scrum app
- Any database or server — Scraut is entirely file + API based

---

Next: [Installation →](./installation)
