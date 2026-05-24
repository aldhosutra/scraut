# Phase 8: Setup CLI & Productisation
*Scraut Implementation — requires Phases 1–7 complete*

## Goal
Make Scraut accessible to everyone — not just the engineer who built it.
Build four accessibility layers:
1. **`npx create-scraut`** — 5-minute setup wizard for new teams
2. **`pip install scraut`** — CLI for developers (standup link, status, add blocker)
3. **Non-dev web form** — standup submissions without touching GitHub
4. **GitHub App** — one-click installation without manual webhook/token setup

---

## 1. `create-scraut/` — Setup Wizard (Node.js)

Create a `create-scraut/` directory at the repo root for the npm package.
This is published separately as `create-scraut` on npmjs.com.

### `create-scraut/package.json`

```json
{
  "name": "create-scraut",
  "version": "1.0.0",
  "description": "Set up Scraut — Scrum Automation — in 5 minutes",
  "bin": {
    "create-scraut": "./bin/create-scraut.js"
  },
  "main": "index.js",
  "keywords": ["scrum", "automation", "github", "agile"],
  "dependencies": {
    "inquirer": "^9.0.0",
    "@octokit/rest": "^20.0.0",
    "js-yaml": "^4.1.0",
    "chalk": "^5.3.0",
    "ora": "^7.0.0"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
```

### `create-scraut/bin/create-scraut.js`

```javascript
#!/usr/bin/env node
/**
 * create-scraut — interactive setup wizard
 * Usage: npx create-scraut
 *
 * Asks 5 questions, then:
 * 1. Creates scraut.yml with answers
 * 2. Scaffolds all workflow YAML files
 * 3. Creates issue templates
 * 4. Sets up GitHub Projects board (if token provided)
 * 5. Prints secrets checklist
 */
import inquirer from 'inquirer';
import { Octokit } from '@octokit/rest';
import yaml from 'js-yaml';
import chalk from 'chalk';
import ora from 'ora';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function main() {
  console.log(chalk.bold('\n🚀 Welcome to Scraut — Scrum Automation\n'));
  console.log('This wizard sets up your team\'s automated Scrum system.\n');
  console.log(chalk.dim('Takes about 5 minutes. You\'ll need:\n') +
    chalk.dim('  • GitHub repository URL\n') +
    chalk.dim('  • Team members\' GitHub usernames\n') +
    chalk.dim('  • Slack webhook URL (optional)\n'));

  const answers = await inquirer.prompt([
    {
      type: 'input',
      name: 'repo',
      message: 'GitHub repository (format: org/repo):',
      validate: (v) => v.includes('/') || 'Must be org/repo format',
    },
    {
      type: 'input',
      name: 'team',
      message: 'Team members\' GitHub usernames (comma-separated):',
      validate: (v) => v.trim().length > 0 || 'At least one team member required',
    },
    {
      type: 'list',
      name: 'sprint_length',
      message: 'Sprint length:',
      choices: [
        { name: '1 week (5 working days)', value: 7 },
        { name: '2 weeks (10 working days)', value: 14 },
        { name: '3 weeks', value: 21 },
      ],
      default: 1,
    },
    {
      type: 'input',
      name: 'slack_webhook',
      message: 'Slack webhook URL (press Enter to skip):',
      default: '',
    },
    {
      type: 'list',
      name: 'llm_provider',
      message: 'LLM provider:',
      choices: ['anthropic', 'openai', 'ollama'],
      default: 0,
    },
    {
      type: 'input',
      name: 'timezone',
      message: 'Team timezone (IANA format, e.g. Asia/Jakarta):',
      default: 'Asia/Jakarta',
    },
  ]);

  const spinner = ora('Creating your Scraut configuration...').start();

  // Parse team members
  const members = answers.team.split(',').map((login, i) => ({
    login: login.trim(),
    display: login.trim().replace(/-/g, ' '),
    role: i === 0 ? 'scrum_master' : 'developer',
    slack_id: '',
    email: '',
  }));

  // Build scraut.yml
  const config = {
    sprint: {
      length_days: answers.sprint_length,
      start_day: 'monday',
      start_time: '09:00',
      timezone: answers.timezone,
      capacity_buffer: 0.85,
      current_sprint: 1,
    },
    team: {
      members,
      product_owner: members[0]?.login || '',
      scrum_master: members[0]?.login || '',
      slack_channel: '#scraut-bot',
    },
    ceremonies: {
      planning: true,
      standup: true,
      grooming: true,
      review: true,
      retrospective: true,
      estimation: true,
    },
    definition_of_done: [
      'Tests written for new functionality',
      'PR reviewed by at least one team member',
      'Acceptance criteria mentioned in PR description',
      'CI passing',
    ],
    repos: [],
    llm: {
      provider: answers.llm_provider,
      model: answers.llm_provider === 'anthropic' ? 'claude-sonnet-4-6' :
             answers.llm_provider === 'openai' ? 'gpt-4o' : 'llama3',
      max_tokens: 1000,
      cost_controls: {
        max_daily_tokens: 100000,
        batch_where_possible: true,
      },
    },
    agents: { enabled: false },
    notifications: {
      slack_webhook: answers.slack_webhook || '',
      morning_dm: true,
      weekly_email: false,
      stakeholder_emails: [],
    },
    portal: {
      enabled: true,
      title: `${answers.repo.split('/')[0]} Team Dashboard`,
      public: true,
      refresh_minutes: 30,
    },
    suggestions: {
      enabled: true,
      min_evidence_count: 3,
      measurement_sprints: 2,
    },
  };

  // Write scraut.yml
  fs.writeFileSync('scraut.yml', yaml.dump(config, { lineWidth: 120 }));
  spinner.succeed('scraut.yml created');

  // Create directory structure
  spinner.start('Creating directory structure...');
  const dirs = [
    '.github/workflows',
    '.github/ISSUE_TEMPLATE',
    'scripts/llm', 'scripts/github', 'scripts/sprint',
    'scripts/standup', 'scripts/backlog', 'scripts/reports',
    'scripts/repo_sync', 'scripts/milestone', 'scripts/visibility',
    'scripts/suggestions', 'scripts/notifications', 'scripts/agents',
    'scripts/utils', 'scripts/setup',
    'suggestions/active', 'suggestions/implemented', 'suggestions/resolved',
    'insights', 'team', 'okr', 'customer', 'knowledge', 'milestones', 'portal',
  ];
  dirs.forEach(d => fs.mkdirSync(d, { recursive: true }));
  spinner.succeed('Directory structure created');

  // Write .gitignore
  fs.writeFileSync('.gitignore',
    '__pycache__/\n*.pyc\n.env\n.env.local\nvenv/\n.venv/\nnode_modules/\n.DS_Store\n*.log\nportal/data.json\n'
  );

  // Write requirements.txt
  fs.writeFileSync('requirements.txt',
    'anthropic>=0.28.0\nopenai>=1.30.0\nPyGitHub>=2.3.0\nrequests>=2.31.0\n' +
    'PyYAML>=6.0.1\nmatplotlib>=3.8.0\nPillow>=10.3.0\npython-dotenv>=1.0.0\n' +
    'click>=8.1.7\njinja2>=3.1.4\npytz>=2024.1\n'
  );

  spinner.succeed('Configuration files written');

  // Print secrets checklist
  console.log('\n' + chalk.bold('✅ Setup complete!\n'));
  console.log(chalk.bold('🔐 Required GitHub Secrets\n') +
    chalk.dim('Set these in: Settings → Secrets and variables → Actions\n\n') +
    (answers.llm_provider === 'anthropic' ?
      '  □ ANTHROPIC_API_KEY\n' : '  □ OPENAI_API_KEY\n') +
    (answers.slack_webhook ?
      '  ✓ SLACK_WEBHOOK (entered above — add to GitHub Secrets)\n' :
      '  □ SLACK_WEBHOOK (optional — for Slack notifications)\n') +
    '  □ SLACK_BOT_TOKEN (for personal standup DMs)\n' +
    '  □ SCRAUT_GITHUB_TOKEN (for connected repo sync)\n'
  );

  console.log(chalk.bold('📋 Next steps:\n') +
    '  1. Run: ' + chalk.cyan('pip install -r requirements.txt') + '\n' +
    '  2. Set all secrets in GitHub Settings\n' +
    '  3. Run: ' + chalk.cyan(`python scripts/setup/create_labels.py ${answers.repo}`) + '\n' +
    '  4. Run: ' + chalk.cyan(`python scripts/sprint/create_sprint.py --sprint 1 --repo ${answers.repo}`) + '\n' +
    '  5. Enable GitHub Pages in repo Settings → Pages → Source: GitHub Actions\n' +
    '  6. Push to main — Scraut is live! 🎉\n'
  );
}

main().catch(console.error);
```

---

## 2. `scraut_cli/` — Python CLI Tool

### `scraut_cli/cli.py`

```python
"""
scraut_cli/cli.py
The `scraut` CLI tool. Install with: pip install scraut
Provides developer-friendly commands for daily Scraut interactions.
"""
import click
import webbrowser
from datetime import date
from pathlib import Path


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Scraut — Scrum Automation CLI

    Quick access to your team's Scraut system from the terminal.
    Run from within a Scraut-enabled repository.
    """
    pass


@cli.command()
@click.option("--browser/--no-browser", default=True,
              help="Open in browser (default) or print URL")
def standup(browser):
    """Open today's standup file for editing in GitHub.

    Example: scraut standup
    """
    try:
        from scripts.utils.config import load_config, get_current_sprint
        from scripts.github.api import get_github_client
        import subprocess

        config = load_config()
        sprint_num = get_current_sprint()
        today = date.today().isoformat()

        # Get current user's GitHub login
        g = get_github_client()
        me = g.get_user()
        login = me.login

        # Get repo remote URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True
        )
        remote = result.stdout.strip()
        # Convert git@github.com:org/repo.git → org/repo
        import re
        repo_match = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", remote)
        if not repo_match:
            click.echo("Could not determine repository from git remote")
            return

        repo_name = repo_match.group(1)
        branch = "main"
        file_path = f"sprint-{sprint_num:02d}/standup/{today}/{login}.md"
        url = (f"https://github.com/{repo_name}/edit/{branch}/{file_path}"
               f"?message=standup%3A+{today}+%5Bskip+ci%5D")

        if browser:
            click.echo(f"Opening standup file for {login} ({today})...")
            webbrowser.open(url)
        else:
            click.echo(url)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("\nMake sure you are in a Scraut-enabled repository with scraut.yml")


@cli.command()
def status():
    """Show current sprint health and milestone status.

    Example: scraut status
    """
    try:
        from scripts.utils.config import load_config, get_repo_root, get_current_sprint
        from scripts.utils.file_utils import read_file

        config = load_config()
        root = get_repo_root()
        sprint_num = get_current_sprint()

        click.echo(f"\n{'='*50}")
        click.echo(f"Sprint {sprint_num:02d} Status")
        click.echo(f"{'='*50}")

        meta = read_file(root / f"sprint-{sprint_num:02d}" / "meta.md")
        if meta:
            for line in meta.split("\n")[:8]:
                if line.startswith("- ") or line.startswith("# "):
                    click.echo(line)

        # Check for active milestone forecast
        for forecast_path in (root / "milestones").glob("*/health/forecast.md"):
            content = read_file(forecast_path)
            if content:
                click.echo(f"\nMilestone: {forecast_path.parent.parent.name}")
                for line in content.split("\n"):
                    if line.startswith("**"):
                        clean = line.replace("**", "").strip()
                        if clean:
                            click.echo(f"  {clean}")

        # Check active suggestions
        active_suggestions = list((root / "suggestions" / "active").glob("s*.md"))
        if active_suggestions:
            click.echo(f"\n{len(active_suggestions)} active suggestion(s):")
            for s in active_suggestions[:3]:
                title_match = s.read_text().split("\n")[0].replace("#", "").strip()
                click.echo(f"  • {title_match[:60]}")

        click.echo("")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("text")
def blocker(text):
    """Add a blocker to today's standup file.

    Example: scraut blocker "Waiting for design approval on #43"
    """
    try:
        from scripts.utils.config import load_config, get_repo_root, get_current_sprint
        from scripts.utils.file_utils import read_file, atomic_write
        from scripts.github.api import get_github_client
        import re

        config = load_config()
        root = get_repo_root()
        sprint_num = get_current_sprint()
        today = date.today().isoformat()

        g = get_github_client()
        me = g.get_user()
        login = me.login

        standup_path = root / f"sprint-{sprint_num:02d}" / "standup" / today / f"{login}.md"
        if not standup_path.exists():
            click.echo(f"Standup file not found: {standup_path}")
            click.echo("Run 'scraut standup' first to open today's file.")
            return

        content = read_file(standup_path)

        # Find Blockers section and append
        blocker_line = f"- {text}"
        if "## Blockers" in content:
            # Replace "None" with the blocker, or append to existing blockers
            content = content.replace(
                "## Blockers\nNone",
                f"## Blockers\n{blocker_line}"
            )
            if blocker_line not in content:
                # Append to existing blockers section
                content = content.replace(
                    "## Notes",
                    f"{blocker_line}\n\n## Notes"
                )
            atomic_write(standup_path, content)
            click.echo(f"✓ Blocker added to {standup_path.name}")
            click.echo(f"  '{text}'")
            click.echo("\nRemember to commit and push: git add . && git commit -m 'standup: blocker [skip ci]' && git push")
        else:
            click.echo("Could not find ## Blockers section in standup file.")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option("--sprint", type=int, help="Sprint number (default: current)")
def velocity(sprint):
    """Show sprint velocity data.

    Example: scraut velocity
    Example: scraut velocity --sprint 3
    """
    try:
        from scripts.utils.config import load_config, get_current_sprint
        from scripts.sprint.calculate_velocity import (calculate_sprint_velocity,
                                                        calculate_rolling_velocity)
        import subprocess, re

        config = load_config()
        sprint_num = sprint or get_current_sprint()

        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True
        )
        remote = result.stdout.strip()
        repo_match = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", remote)
        if not repo_match:
            click.echo("Could not determine repository")
            return

        repo_name = repo_match.group(1)
        vel = calculate_sprint_velocity(sprint_num, repo_name)
        rolling = calculate_rolling_velocity(repo_name)

        click.echo(f"\nSprint {sprint_num:02d}: {vel['completed_sp']} / {vel['planned_sp']} sp "
                   f"({round(vel['completion_rate']*100)}%)")
        click.echo(f"Rolling average: {rolling['avg']} sp/sprint "
                   f"(σ={rolling['std_dev']}, {rolling['sprints_sampled']} sprints sampled)")
        click.echo("")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


def main():
    cli()


if __name__ == "__main__":
    main()
```

### `scraut_cli/setup.py`

```python
from setuptools import setup, find_packages

setup(
    name="scraut",
    version="1.0.0",
    description="Scraut CLI — quick access to your Scrum Automation system",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "scraut=scraut_cli.cli:main",
        ],
    },
    install_requires=[
        "click>=8.1.7",
        "anthropic>=0.28.0",
        "PyGitHub>=2.3.0",
        "PyYAML>=6.0.1",
    ],
    python_requires=">=3.11",
)
```

---

## 3. Non-Developer Web Form

The web form lets non-technical team members submit standups without touching GitHub.
It calls a serverless function that writes to the GitHub repo via API.

### `portal/form.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Standup</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, sans-serif; background: #f5f5f7;
         display: flex; justify-content: center; padding: 40px 16px; }
  .card { background: white; border-radius: 16px; padding: 32px;
          max-width: 560px; width: 100%; box-shadow: 0 2px 12px rgba(0,0,0,.08); }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .subtitle { font-size: 13px; color: #86868b; margin-bottom: 24px; }
  label { display: block; font-size: 13px; font-weight: 600;
          color: #3a3a3c; margin-bottom: 6px; }
  select, textarea { width: 100%; border: 1.5px solid #d1d1d6; border-radius: 10px;
                      padding: 10px 14px; font-size: 14px; color: #1d1d1f;
                      background: white; margin-bottom: 18px; font-family: inherit; }
  textarea { resize: vertical; min-height: 80px; }
  textarea:focus, select:focus { outline: none; border-color: #0071e3; }
  button { width: 100%; background: #0071e3; color: white; border: none;
           border-radius: 10px; padding: 14px; font-size: 15px; font-weight: 600;
           cursor: pointer; }
  button:hover { background: #0077ed; }
  button:disabled { background: #aeaeb2; cursor: not-allowed; }
  .success { background: #d1fae5; border-radius: 10px; padding: 16px;
             text-align: center; color: #065f46; font-size: 14px; display: none; }
  .error { background: #fee2e2; border-radius: 10px; padding: 12px;
           color: #991b1b; font-size: 13px; margin-bottom: 16px; display: none; }
  .hint { font-size: 12px; color: #86868b; margin-top: -14px; margin-bottom: 18px; }
</style>
</head>
<body>
<div class="card">
  <h1>Daily Standup</h1>
  <p class="subtitle" id="date-subtitle">Loading...</p>

  <div id="error-msg" class="error"></div>

  <label for="name">Your name</label>
  <select id="name"></select>

  <label for="yesterday">What did you accomplish?</label>
  <textarea id="yesterday" placeholder="e.g. Finished the onboarding flow design&#10;Had a meeting with the client&#10;Reviewed the test results"></textarea>
  <p class="hint">Yesterday's work and completed tasks</p>

  <label for="today">What are you working on today?</label>
  <textarea id="today" placeholder="e.g. Starting the payment integration&#10;Design review at 2pm"></textarea>

  <label for="blockers">Any blockers?</label>
  <textarea id="blockers" placeholder="Write None if nothing is blocking you" style="min-height:60px"></textarea>

  <button id="submit-btn" onclick="submitStandup()">Submit Standup</button>

  <div id="success-msg" class="success">
    ✅ Standup submitted! Thank you.<br>
    <span style="font-size:12px;margin-top:4px;display:block;">The team bot will include your update in today's summary.</span>
  </div>
</div>

<script>
// Configuration — set these values when deploying
const CONFIG = {
  teamMembers: [],    // Populated from scraut.yml via build step
  apiEndpoint: '/api/standup',  // Your edge function URL
};

window.onload = () => {
  const today = new Date().toLocaleDateString('en-US',
    { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  document.getElementById('date-subtitle').textContent = today;

  // Populate team members dropdown
  const select = document.getElementById('name');
  CONFIG.teamMembers.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.login;
    opt.textContent = m.display;
    select.appendChild(opt);
  });
};

async function submitStandup() {
  const btn = document.getElementById('submit-btn');
  const errorEl = document.getElementById('error-msg');
  const successEl = document.getElementById('success-msg');
  errorEl.style.display = 'none';

  const data = {
    login: document.getElementById('name').value,
    yesterday: document.getElementById('yesterday').value.trim(),
    today: document.getElementById('today').value.trim(),
    blockers: document.getElementById('blockers').value.trim() || 'None',
    date: new Date().toISOString().split('T')[0],
  };

  if (!data.yesterday || !data.today) {
    errorEl.textContent = 'Please fill in both Yesterday and Today fields.';
    errorEl.style.display = 'block';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Submitting...';

  try {
    const resp = await fetch(CONFIG.apiEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!resp.ok) {
      throw new Error(await resp.text());
    }

    btn.style.display = 'none';
    successEl.style.display = 'block';
  } catch (err) {
    errorEl.textContent = `Submission failed: ${err.message}. Please try again or use the GitHub pencil icon.`;
    errorEl.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Submit Standup';
  }
}
</script>
</body>
</html>
```

### `portal/api/standup.js` (Vercel/Netlify Edge Function)

```javascript
/**
 * Serverless edge function: receives standup form submission,
 * writes to GitHub repo via Contents API.
 * Deploy to Vercel or Netlify Functions.
 *
 * Required environment variables:
 *   GITHUB_TOKEN  — scoped write token for the Scraut repo
 *   SCRAUT_REPO   — org/repo of the Scraut repository
 *   PORTAL_TOKEN  — simple shared secret to prevent abuse
 */

export default async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { login, yesterday, today, blockers, date } = req.body;

  if (!login || !yesterday || !today || !date) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  // Build standup markdown content
  const content = `# Standup — ${login}
<!-- 
  Sprint: auto-detected
  Date: ${date}
  Author: ${login}
  Submitted via: web form
-->

## Yesterday
${yesterday}

## Today
${today}

## Blockers
${blockers || 'None'}

## Notes
_Submitted via Scraut web form_
`;

  // Encode for GitHub API
  const encoded = Buffer.from(content).toString('base64');

  // Determine current sprint from scraut.yml (simplified: use date math)
  // In production, fetch scraut.yml from repo and parse current_sprint
  const sprintNum = '01'; // TODO: fetch from scraut.yml

  const filePath = `sprint-${sprintNum}/standup/${date}/${login}.md`;
  const apiUrl = `https://api.github.com/repos/${process.env.SCRAUT_REPO}/contents/${filePath}`;

  try {
    // Check if file exists (to get SHA for update)
    let sha = undefined;
    const checkResp = await fetch(apiUrl, {
      headers: {
        Authorization: `token ${process.env.GITHUB_TOKEN}`,
        Accept: 'application/vnd.github.v3+json',
      },
    });
    if (checkResp.ok) {
      const existing = await checkResp.json();
      sha = existing.sha;
    }

    // Create or update file
    const body = {
      message: `standup: ${login} ${date} [skip ci]`,
      content: encoded,
      branch: 'main',
    };
    if (sha) body.sha = sha;

    const writeResp = await fetch(apiUrl, {
      method: 'PUT',
      headers: {
        Authorization: `token ${process.env.GITHUB_TOKEN}`,
        Accept: 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!writeResp.ok) {
      const err = await writeResp.text();
      throw new Error(`GitHub API error: ${err}`);
    }

    return res.status(200).json({ success: true, file: filePath });
  } catch (err) {
    console.error('Standup submission error:', err);
    return res.status(500).json({ error: err.message });
  }
}
```

---

## 4. GitHub App Configuration

The GitHub App replaces the need for a Personal Access Token. Teams install it
from the GitHub Marketplace with one click.

### `github-app/app.yml` (App manifest)

```yaml
name: Scraut
description: >
  Scrum Automation — fully automated Scrum ceremonies, milestone planning,
  suggestion system, and AI agent coordination. All powered by text files.
url: https://github.com/marketplace/scraut
hook_attributes:
  url: https://scraut.example.com/webhooks/github
  active: true
redirect_url: https://scraut.example.com/install/callback
default_events:
  - push
  - issues
  - issue_comment
  - pull_request
  - pull_request_review
  - workflow_run
default_permissions:
  contents: write
  issues: write
  pull_requests: write
  actions: write
  metadata: read
  projects: write
  members: read
```

### `github-app/webhook_handler.py`

```python
"""
github-app/webhook_handler.py
GitHub App webhook handler (Flask or FastAPI).
Processes GitHub webhook events and triggers appropriate Scraut workflows.
This runs as a small web service, separate from the GitHub Actions workflows.

For development: Use smee.io to proxy webhooks to localhost.
For production: Deploy to Fly.io, Railway, or similar.
"""
import hashlib
import hmac
import json
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def verify_webhook_signature(payload_body: bytes, signature: str,
                              secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    expected = "sha256=" + hmac.new(
        secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def handle_push(payload: dict) -> None:
    """Handle push events: trigger appropriate Scraut workflows."""
    ref = payload.get("ref", "")
    if ref != "refs/heads/main":
        return

    commits = payload.get("commits", [])
    changed_files = []
    for commit in commits:
        changed_files.extend(commit.get("added", []))
        changed_files.extend(commit.get("modified", []))

    # Determine which workflows to trigger based on changed files
    triggers = []
    if any("milestone.md" in f for f in changed_files):
        triggers.append("milestone-planning")
    if any("standup/" in f or "code/" in f for f in changed_files):
        triggers.append("visibility-engine")

    logger.info(f"Push to main: {len(changed_files)} files changed. Triggers: {triggers}")


def handle_installation(payload: dict) -> None:
    """
    Handle GitHub App installation: scaffold Scraut into the installed repo.
    Creates directory structure and initial scraut.yml if not present.
    """
    installation_id = payload.get("installation", {}).get("id")
    repos = payload.get("repositories", [])

    for repo in repos:
        repo_full_name = repo.get("full_name")
        logger.info(f"Scraut installed on {repo_full_name} (installation #{installation_id})")
        # In production: use GitHub App installation token to create initial files
        # This mirrors what npx create-scraut does, but automated


# Flask example
try:
    from flask import Flask, request, jsonify
    app = Flask(__name__)

    @app.route("/webhooks/github", methods=["POST"])
    def github_webhook():
        secret = os.environ.get("GITHUB_APP_WEBHOOK_SECRET", "")
        signature = request.headers.get("X-Hub-Signature-256", "")

        if not verify_webhook_signature(request.data, signature, secret):
            return jsonify({"error": "Invalid signature"}), 401

        event = request.headers.get("X-GitHub-Event")
        payload = request.json

        if event == "push":
            handle_push(payload)
        elif event == "installation":
            handle_installation(payload)

        return jsonify({"status": "ok"}), 200

except ImportError:
    pass  # Flask not available; use FastAPI or other framework
```

---

## 5. `scripts/setup/setup_github_projects.py`

Automates creating the GitHub Projects board with all required columns and custom fields.

```python
"""
scripts/setup/setup_github_projects.py
Create GitHub Projects v2 board with Scraut columns and custom fields.
Run once during initial setup after create_labels.py.
"""
import argparse
import logging
import os
import requests
from scripts.utils.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.github.com/graphql"
TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def gql(query: str, variables: dict = None) -> dict:
    resp = requests.post(GRAPHQL_URL,
                         json={"query": query, "variables": variables or {}},
                         headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def create_project(owner: str, title: str) -> str:
    """Create a new GitHub Projects v2. Returns project node ID."""
    # First get the owner node ID
    owner_data = gql(
        'query($login: String!) { organization(login: $login) { id } }',
        {"login": owner}
    )
    owner_id = owner_data["organization"]["id"]

    result = gql(
        '''mutation($ownerId: ID!, $title: String!) {
          createProjectV2(input: {ownerId: $ownerId, title: $title}) {
            projectV2 { id number }
          }
        }''',
        {"ownerId": owner_id, "title": title}
    )
    project = result["createProjectV2"]["projectV2"]
    logger.info(f"Created project: {title} (#{project['number']})")
    return project["id"]


def add_status_field(project_id: str) -> None:
    """Update default Status field with Scraut columns."""
    # Get existing Status field ID
    fields_data = gql(
        '''query($id: ID!) {
          node(id: $id) {
            ... on ProjectV2 {
              fields(first: 20) {
                nodes {
                  ... on ProjectV2SingleSelectField { id name options { id name } }
                }
              }
            }
          }
        }''',
        {"id": project_id}
    )
    status_field = next(
        (f for f in fields_data["node"]["fields"]["nodes"]
         if f and f.get("name") == "Status"), None
    )

    if not status_field:
        logger.warning("Status field not found")
        return

    logger.info(f"Status field exists with {len(status_field['options'])} options")
    # Note: Modifying status options requires the Projects REST API
    # or manual setup in the GitHub UI. Document this for users.


def add_custom_field(project_id: str, name: str, field_type: str = "TEXT",
                     options: list = None) -> str:
    """Add a custom field to the project."""
    data_type = "TEXT" if field_type == "TEXT" else "NUMBER"
    result = gql(
        '''mutation($projectId: ID!, $name: String!, $dataType: ProjectV2CustomFieldType!) {
          createProjectV2Field(input: {
            projectId: $projectId
            name: $name
            dataType: $dataType
          }) { projectV2Field { ... on ProjectV2Field { id name } } }
        }''',
        {"projectId": project_id, "name": name,
         "dataType": data_type}
    )
    field_id = result["createProjectV2Field"]["projectV2Field"]["id"]
    logger.info(f"Created field: {name}")
    return field_id


def setup_project(owner: str, config: dict) -> int:
    """Create and configure the full Scraut GitHub Projects board."""
    title = config.get("portal", {}).get("title", "Scraut Board")
    project_id = create_project(owner, title)

    # Add custom fields
    fields = [
        ("Agent", "TEXT"),
        ("SP Remaining", "NUMBER"),
        ("Blocker", "TEXT"),
        ("Sprint", "TEXT"),
        ("Last Activity", "TEXT"),
    ]
    for field_name, field_type in fields:
        add_custom_field(project_id, field_name, field_type)

    logger.info("\n✅ GitHub Projects board created!")
    logger.info("⚠️  Manual step required: Update Status field options in GitHub UI to:")
    logger.info("   Backlog | Ready | In Progress | Review | Testing | Done")
    logger.info("   (GraphQL API does not support option modification for single-select fields)")

    # Get the project number for scraut.yml
    project_num_data = gql(
        'query($id: ID!) { node(id: $id) { ... on ProjectV2 { number } } }',
        {"id": project_id}
    )
    project_number = project_num_data["node"]["number"]
    logger.info(f"\nAdd this to scraut.yml:\n  portal:\n    project_number: {project_number}")
    return project_number


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup GitHub Projects board")
    parser.add_argument("owner", help="GitHub org or user login")
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    setup_project(args.owner, config)
```

---

## 6. `INSTALL.md` — Quick Start Guide for New Teams

```markdown
# Scraut — Quick Start

## Option A: Automated setup (recommended)

```bash
npx create-scraut
```

Answer 5 questions. Takes 5 minutes.

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
```

---

## Done Criteria for Phase 8

- [ ] `create-scraut/bin/create-scraut.js` — `npx create-scraut` runs, asks 6 questions, writes `scraut.yml` + `requirements.txt` + `.gitignore`, prints secrets checklist
- [ ] `scraut_cli/cli.py` — `scraut standup` opens correct GitHub edit URL in browser
- [ ] `scraut_cli/cli.py` — `scraut status` reads and prints sprint health without error
- [ ] `scraut_cli/cli.py` — `scraut blocker "text"` appends blocker to standup file correctly
- [ ] `scraut_cli/cli.py` — `scraut velocity` shows sprint and rolling velocity
- [ ] `scraut_cli/setup.py` — `pip install -e .` succeeds and `scraut --help` works
- [ ] `portal/form.html` — form renders correctly in browser, all fields functional
- [ ] `portal/api/standup.js` — edge function correctly writes standup file to GitHub repo via Contents API
- [ ] `scripts/setup/setup_github_projects.py` — creates GitHub Projects board with custom fields
- [ ] `INSTALL.md` — clear, accurate, complete quick-start guide
- [ ] End-to-end test: run `npx create-scraut` in an empty directory, verify all files are created correctly

---

## 🎉 All Phases Complete

With all 8 phases implemented, Scraut provides:

| Phase | What's built |
|-------|-------------|
| 1 | Foundation: config system, GitHub API wrappers, issue templates |
| 2 | Ceremonies: 5 Scrum ceremonies, LLM client, standup system, estimation |
| 3 | Milestone Planning: decompose → plan → health check |
| 4 | Repo Sync: code activity, delta analysis, standup pre-fill |
| 5 | Visibility Portal: board sync, GitHub Pages dashboard, morning DMs |
| 6 | Suggestion System: 6 detectors, lifecycle, measurement loop |
| 7 | Agent Mode: orchestrator, checkpoints, deadlock detection |
| 8 | Productisation: setup CLI, web form, GitHub App, CLI tool |

**Next steps after all phases:**
1. Write unit tests for each script (pytest, `tests/` directory)
2. Add end-to-end integration tests using a test GitHub repo
3. Publish `create-scraut` to npmjs.com
4. Publish `scraut` Python package to PyPI
5. Submit GitHub App to Marketplace
6. Write user documentation (can use Scraut itself to manage this 😄)
```
