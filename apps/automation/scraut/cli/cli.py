"""
cli/cli.py
The `scraut` CLI tool. Install with: pip install scraut
Provides developer-friendly commands for daily Scraut interactions.
"""
import os
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
        from scraut.platform.utils.config import load_config, get_current_sprint
        from scraut.platform.github.api import get_github_client
        import subprocess
        import re

        config = load_config()
        sprint_num = get_current_sprint()
        today = date.today().isoformat()

        g = get_github_client()
        me = g.get_user()
        login = me.login

        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True
        )
        remote = result.stdout.strip()
        repo_match = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", remote)
        if not repo_match:
            click.echo("Could not determine repository from git remote")
            return

        repo_name = repo_match.group(1)
        branch = "main"
        file_path = f"workspace/sprint/{sprint_num:02d}/standup/{today}/{login}.md"
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
        from scraut.platform.utils.config import load_config, get_workspace_root, get_current_sprint, get_sprint_folder, get_scraut_root
        from scraut.platform.utils.file_utils import read_file

        config = load_config()
        root = get_workspace_root()
        scraut_root = get_scraut_root()
        sprint_num = get_current_sprint()

        click.echo(f"\n{'='*50}")
        click.echo(f"Sprint {sprint_num:02d} Status")
        click.echo(f"{'='*50}")

        meta = read_file(get_sprint_folder(sprint_num) / "meta.md")
        if meta:
            for line in meta.split("\n")[:8]:
                if line.startswith("- ") or line.startswith("# "):
                    click.echo(line)

        for forecast_path in (scraut_root / "milestones").glob("*/health/forecast.md"):
            content = read_file(forecast_path)
            if content:
                click.echo(f"\nMilestone: {forecast_path.parent.parent.name}")
                for line in content.split("\n"):
                    if line.startswith("**"):
                        clean = line.replace("**", "").strip()
                        if clean:
                            click.echo(f"  {clean}")

        active_suggestions = list((scraut_root / "suggestions" / "active").glob("s*.md"))
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
        from scraut.platform.utils.config import load_config, get_workspace_root, get_current_sprint, get_sprint_folder
        from scraut.platform.utils.file_utils import read_file, atomic_write
        from scraut.platform.github.api import get_github_client

        config = load_config()
        root = get_workspace_root()
        sprint_num = get_current_sprint()
        today = date.today().isoformat()

        g = get_github_client()
        me = g.get_user()
        login = me.login

        standup_path = get_sprint_folder(sprint_num) / "standup" / today / f"{login}.md"
        if not standup_path.exists():
            click.echo(f"Standup file not found: {standup_path}")
            click.echo("Run 'scraut standup' first to open today's file.")
            return

        content = read_file(standup_path)

        blocker_line = f"- {text}"
        if "## Blockers" in content:
            content = content.replace(
                "## Blockers\nNone",
                f"## Blockers\n{blocker_line}"
            )
            if blocker_line not in content:
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
        from scraut.platform.utils.config import load_config, get_current_sprint
        from scraut.scrum.sprint.calculate_velocity import (calculate_sprint_velocity,
                                                        calculate_rolling_velocity)
        import subprocess
        import re

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


_STANDUP_TEMPLATE = """\
# Standup — {display_name}
<!--
  Sprint: sprint-{sprint_num:02d}
  Date: {date}
  Author: {login}

  ─── NAVIGATION ──────────────────────────────────────────
  📁 Sprint folder:   sprint-{sprint_num:02d}/
  📋 Sprint meta:     sprint-{sprint_num:02d}/meta.md
  📝 Your standup:    sprint-{sprint_num:02d}/standup/{date}/{login}.md
  💬 Retro (when due): sprint-{sprint_num:02d}/retrospective/{login}.md
  🗒️  Backlog ideas:   sprint-{sprint_num:02d}/grooming/backlog-ideas.md
  🏁 Board:           [GitHub Projects - see scraut.yml portal.project_number]
  ─────────────────────────────────────────────────────────
-->

## Yesterday
<!-- What did you complete? Reference issues/PRs where applicable. -->

## Today
<!-- What will you work on today? Reference issues if possible. -->

## Blockers
<!-- Anything blocking your progress? Scraut tracks these automatically. -->
<!-- Write "None" if no blockers. -->
None

## Notes
<!-- Optional: OOO, reduced availability, context for the team -->
"""

_RETRO_TEMPLATE = """\
# Retro — {display_name} — Sprint {sprint_num:02d}

## Went well
<!-- What went well this sprint? Be specific. -->

## Could improve
<!-- What would you change? Focus on process, not people. -->

## Action items I'll own
<!-- Personal commitments for next sprint. -->
"""

_META_TEMPLATE = """\
# Sprint 1
- Period: [Set when sprint starts]
- Goal: [Set during sprint planning]
- Team: {team_names}
- Committed: TBD story points across TBD issues
- Capacity note: [Check team/capacity.md for OOO]

## Issues in sprint
| Issue | Title | Epic | SP | Assignee |
|-------|-------|------|----|---------|
"""

_CAPACITY_TEMPLATE = """\
# Team Capacity — Sprint 1

<!-- Record OOO days, part-time availability, or any capacity reductions.
     Scraut uses this to adjust sprint planning recommendations. -->

| Login | Available Days | Notes |
|-------|---------------|-------|
{capacity_rows}
"""

_OKR_TEMPLATE = """\
# Objectives & Key Results

<!-- Define team OKRs here. Scraut references these during sprint planning
     to ensure sprint goals align with strategic objectives. -->

## Objective 1
[Describe what you want to achieve]

### Key Result 1.1
- Target: [Measurable outcome]
- Current: [Current value]

### Key Result 1.2
- Target: [Measurable outcome]
- Current: [Current value]

## Objective 2
[Describe what you want to achieve]

### Key Result 2.1
- Target: [Measurable outcome]
- Current: [Current value]
"""

_CUSTOMER_FEEDBACK_TEMPLATE = """\
# Customer Feedback

<!-- Record customer feedback, support tickets, user research findings.
     Scraut's backlog grooming agent uses this to suggest story priorities. -->

## Feedback Log

| Date | Source | Summary | Priority | Linked Issue |
|------|--------|---------|----------|-------------|
| {today} | [Channel/user] | [Summary] | medium | — |

## Themes
<!-- Recurring patterns the team has identified -->

- [Theme 1]: [Description]
"""

_MILESTONES_README_TEMPLATE = """\
# Milestones

<!-- Each milestone gets its own file: milestones/<name>.md
     Scraut's milestone agent reads these to track health and generate forecasts. -->

## Milestone file format

Create `milestones/v1.0.md` (or any name) with:

```markdown
# Milestone: v1.0
- Due: YYYY-MM-DD
- Goal: [What this release delivers]
- GitHub milestone: https://github.com/{repo}/milestone/1

## Epics
- [ ] Epic: [Name] — [linked issue or description]

## Risks
- [Risk description] — Mitigation: [how you're handling it]

## Definition of Done
- [ ] All committed issues closed
- [ ] Release notes drafted
- [ ] Stakeholders notified
```
"""


@cli.command()
def init():
    """Interactive first-time setup wizard. Run once after cloning Scraut.

    Creates workspace/scraut.yml, the full directory skeleton, scaffold
    template files so team members see the expected format, and optionally
    creates GitHub labels if GITHUB_TOKEN is set.

    Example: scraut init
    """
    import yaml
    from datetime import date as _date

    click.echo("\n" + "=" * 52)
    click.echo("  Scraut Setup Wizard")
    click.echo("=" * 52)
    click.echo("Answers populate workspace/scraut.yml.")
    click.echo("Press Enter to accept defaults.\n")

    repo = click.prompt("GitHub repository (org/repo)", default="your-org/your-repo")
    raw_team = click.prompt("Team member GitHub logins (comma-separated)")
    logins = [l.strip() for l in raw_team.split(",") if l.strip()]
    po = click.prompt("Product owner login", default=logins[0] if logins else "")
    sm = click.prompt("Scrum master login", default=logins[0] if logins else "")
    channel = click.prompt("Slack channel", default="#scraut-bot")
    sprint_days = click.prompt("Sprint length in days", default=14, type=int)
    timezone = click.prompt("Timezone (IANA format, e.g. UTC, Asia/Jakarta)", default="UTC")
    provider = click.prompt(
        "LLM provider",
        type=click.Choice(["anthropic", "openai", "gemini", "ollama"]),
        default="anthropic",
    )
    slack_webhook = click.prompt("Slack webhook URL (optional, Enter to skip)", default="")

    _model = {
        "anthropic": "claude-sonnet-4-6", "openai": "gpt-4o",
        "gemini": "gemini-1.5-pro", "ollama": "llama3",
    }[provider]
    _key = {
        "anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
        "gemini": "GOOGLE_API_KEY", "ollama": "(no key needed)",
    }[provider]

    members = [
        {
            "login": l,
            "display": l.replace("-", " ").title(),
            "role": "developer",
            "slack_id": "",
            "email": "",
        }
        for l in logins
    ]

    config = {
        "sprint": {
            "length_days": sprint_days,
            "start_day": "monday",
            "start_time": "09:00",
            "timezone": timezone,
            "capacity_buffer": 0.85,
            "current_sprint": 1,
        },
        "team": {
            "members": members,
            "product_owner": po,
            "scrum_master": sm,
            "slack_channel": channel,
        },
        "ceremonies": {
            "planning": True, "standup": True, "grooming": True,
            "review": True, "retrospective": True, "estimation": True,
        },
        "definition_of_done": [
            "Tests written for new functionality",
            "PR reviewed by at least one team member",
            "Acceptance criteria mentioned in PR description",
            "No open review comments",
            "CI passing",
        ],
        "repos": [],
        "llm": {
            "provider": provider,
            "model": _model,
            "base_url": "",
            "max_tokens": 1000,
            "cost_controls": {"max_daily_tokens": 100000, "batch_where_possible": True},
        },
        "agents": {"enabled": False},
        "notifications": {
            "slack_webhook": slack_webhook,
            "morning_dm": True,
            "weekly_email": False,
            "stakeholder_emails": [],
        },
        "portal": {
            "enabled": True,
            "title": f"{repo.split('/')[0]} Dashboard",
            "public": True,
            "refresh_minutes": 30,
        },
        "suggestions": {"enabled": True, "min_evidence_count": 3, "measurement_sprints": 2},
        "paths": {"workspace": "workspace", "scraut": ".scraut", "portal": "apps/portal"},
    }

    # Write workspace/scraut.yml
    workspace = Path("workspace")
    workspace.mkdir(exist_ok=True)
    config_file = workspace / "scraut.yml"
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    click.echo(f"\n  created  workspace/scraut.yml")

    # Workspace directories
    for d in [
        "team", "okr", "customer", "knowledge", "milestones",
        "sprint/01/standup", "sprint/01/retrospective",
        "sprint/01/grooming", "sprint/01/decisions", "sprint/01/adr",
    ]:
        p = workspace / d
        p.mkdir(parents=True, exist_ok=True)

    # .scraut directories (bot-generated output)
    scraut_root = Path(".scraut")
    for d in [
        "sprint/01/standup/summary", "sprint/01/review",
        "sprint/01/code", "sprint/01/incidents",
        "insights", "milestones",
        "suggestions/active", "suggestions/implemented", "suggestions/resolved",
    ]:
        p = scraut_root / d
        p.mkdir(parents=True, exist_ok=True)
        (p / ".gitkeep").touch()

    click.echo("  created  workspace/ and .scraut/ directory structure")

    # Scaffold template files so team members see the expected format
    today = _date.today().isoformat()
    team_names = ", ".join(m["display"] for m in members)
    capacity_rows = "\n".join(
        f"| {m['login']} | 10 | |" for m in members
    )

    for member in members:
        login = member["login"]
        display = member["display"]

        standup_dir = workspace / "sprint" / "01" / "standup" / today
        standup_dir.mkdir(parents=True, exist_ok=True)
        standup_file = standup_dir / f"{login}.md"
        if not standup_file.exists():
            standup_file.write_text(_STANDUP_TEMPLATE.format(
                display_name=display, sprint_num=1, date=today, login=login,
            ))

        retro_dir = workspace / "sprint" / "01" / "retrospective"
        retro_file = retro_dir / f"{login}.md"
        if not retro_file.exists():
            retro_file.write_text(_RETRO_TEMPLATE.format(
                display_name=display, sprint_num=1,
            ))

    meta_file = workspace / "sprint" / "01" / "meta.md"
    if not meta_file.exists():
        meta_file.write_text(_META_TEMPLATE.format(team_names=team_names))

    grooming_file = workspace / "sprint" / "01" / "grooming" / "backlog-ideas.md"
    if not grooming_file.exists():
        grooming_file.write_text(
            "# Backlog Ideas\n<!-- Append new ideas below. Anyone can add. -->\n\n"
        )

    capacity_file = workspace / "team" / "capacity.md"
    if not capacity_file.exists():
        capacity_file.write_text(_CAPACITY_TEMPLATE.format(capacity_rows=capacity_rows))

    okr_file = workspace / "okr" / "okr.md"
    if not okr_file.exists():
        okr_file.write_text(_OKR_TEMPLATE)

    customer_file = workspace / "customer" / "feedback.md"
    if not customer_file.exists():
        customer_file.write_text(_CUSTOMER_FEEDBACK_TEMPLATE.format(today=today))

    milestones_file = workspace / "milestones" / "README.md"
    if not milestones_file.exists():
        milestones_file.write_text(_MILESTONES_README_TEMPLATE.format(repo=repo))

    click.echo("  scaffolded  workspace template files for Sprint 1")

    # GitHub labels (requires GITHUB_TOKEN)
    if repo != "your-org/your-repo" and os.environ.get("GITHUB_TOKEN"):
        click.echo("\n  Creating GitHub labels...")
        try:
            from scraut.platform.setup.create_labels import main as create_labels
            create_labels(repo, str(config_file))
            click.echo("  GitHub labels created")
        except Exception as e:
            click.echo(f"  Warning: {e}")
            click.echo(f"  Run later: python apps/automation/scraut/platform/setup/create_labels.py --repo {repo}")
    else:
        msg = "GITHUB_TOKEN not set" if repo != "your-org/your-repo" else "placeholder repo — skipping"
        click.echo(f"\n  Skipping label creation ({msg})")
        if repo != "your-org/your-repo":
            click.echo(f"  Run later: python apps/automation/scraut/platform/setup/create_labels.py --repo {repo}")

    click.echo("\n" + "=" * 52)
    click.echo("  Done! Next steps:\n")
    click.echo(f"  1. Edit workspace/scraut.yml")
    click.echo(f"       Fill in slack_id and email for each team member.")
    click.echo(f"\n  2. Fill in today's standup")
    click.echo(f"       workspace/sprint/01/standup/{today}/<login>.md")
    click.echo(f"\n  3. Set GitHub Secrets  (Settings → Secrets → Actions)")
    click.echo(f"       [ ] {_key}")
    click.echo(f"       [ ] SLACK_WEBHOOK")
    click.echo(f"       [ ] SLACK_BOT_TOKEN")
    click.echo(f"\n  4. Create Sprint 1")
    click.echo(f"       python apps/automation/scraut/scrum/sprint/create_sprint.py \\")
    click.echo(f"              --sprint 1 --repo {repo}")
    click.echo(f"\n  5. Commit and push")
    click.echo(f"       git add . && git commit -m 'chore: scraut setup [skip ci]' && git push")
    click.echo(f"\n  6. Trigger sprint-planning from GitHub Actions UI")
    click.echo("")


def main():
    cli()


if __name__ == "__main__":
    main()
