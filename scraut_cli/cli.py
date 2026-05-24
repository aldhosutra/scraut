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

        for forecast_path in (root / "milestones").glob("*/health/forecast.md"):
            content = read_file(forecast_path)
            if content:
                click.echo(f"\nMilestone: {forecast_path.parent.parent.name}")
                for line in content.split("\n"):
                    if line.startswith("**"):
                        clean = line.replace("**", "").strip()
                        if clean:
                            click.echo(f"  {clean}")

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
        from scripts.utils.config import load_config, get_current_sprint
        from scripts.sprint.calculate_velocity import (calculate_sprint_velocity,
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


def main():
    cli()


if __name__ == "__main__":
    main()
