"""
scrum/repo_sync/fetch_activity.py
Fetch all code activity for team members from connected repos.
Writes activity.json (machine-readable) and activity.md (human-readable).

Fetched for each team member:
- Commits pushed (author matches team login)
- PRs opened, merged, reviewed
- CI/check run failures they caused
"""
import argparse
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from github import Github
from github.Repository import Repository
from scraut.platform.utils.config import load_config, get_workspace_root, get_current_sprint, get_team_logins, get_sprint_folder, get_sprint_output_folder
from scraut.platform.utils.file_utils import atomic_write
from scraut.platform.github.api import get_github_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Emoji indicators for activity types
ICONS = {
    "commit": "📝",
    "pr_merged": "✅",
    "pr_opened": "🔀",
    "pr_reviewed": "👀",
    "ci_failure": "🔴",
    "ci_fixed": "🔧",
    "pr_aging": "⚠️",
}


def fetch_activity_for_repo(
    repo: Repository, team_logins: list[str],
    since: datetime, pr_sla_hours: int = 48
) -> dict:
    """
    Fetch activity from a single GitHub repo.
    Returns per-member activity dict.
    """
    member_activity = {login: {
        "commits": [],
        "prs_opened": [],
        "prs_merged": [],
        "prs_reviewed": [],
        "ci_failures": [],
    } for login in team_logins}

    # Commits
    logger.info(f"Fetching commits since {since.date()} from {repo.full_name}")
    try:
        commits = repo.get_commits(since=since)
        for commit in commits:
            if not commit.author:
                continue
            login = commit.author.login
            if login not in team_logins:
                continue
            branch = _get_commit_branch(repo, commit.sha)
            member_activity[login]["commits"].append({
                "sha": commit.sha[:7],
                "message": commit.commit.message.split("\n")[0][:80],
                "branch": branch,
                "repo": repo.full_name,
                "timestamp": commit.commit.author.date.isoformat(),
            })
    except Exception as e:
        logger.warning(f"Failed to fetch commits: {e}")

    # Pull Requests (updated in last 48h to catch recent activity)
    logger.info(f"Fetching PRs from {repo.full_name}")
    try:
        for pr in repo.get_pulls(state="all", sort="updated", direction="desc"):
            if pr.updated_at.replace(tzinfo=timezone.utc) < since:
                break

            author = pr.user.login if pr.user else None
            if author in team_logins:
                pr_data = {
                    "number": pr.number,
                    "title": pr.title[:80],
                    "repo": repo.full_name,
                    "url": pr.html_url,
                    "closes_issues": _extract_closes(pr.body or ""),
                }

                if pr.created_at.replace(tzinfo=timezone.utc) >= since:
                    member_activity[author]["prs_opened"].append(pr_data)

                if pr.merged_at and pr.merged_at.replace(tzinfo=timezone.utc) >= since:
                    member_activity[author]["prs_merged"].append(pr_data)

            # Reviews
            try:
                reviews = pr.get_reviews()
                for review in reviews:
                    if not review.user:
                        continue
                    reviewer = review.user.login
                    if reviewer not in team_logins:
                        continue
                    if review.submitted_at.replace(tzinfo=timezone.utc) < since:
                        continue
                    member_activity[reviewer]["prs_reviewed"].append({
                        "number": pr.number,
                        "title": pr.title[:60],
                        "repo": repo.full_name,
                        "review_type": review.state.lower(),  # approved/changes_requested/commented
                    })
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Failed to fetch PRs: {e}")

    return member_activity


def _extract_closes(pr_body: str) -> list[int]:
    """Extract issue numbers from 'Closes #NNN' in PR body."""
    import re
    return [int(n) for n in re.findall(r"[Cc]loses?\s+#(\d+)", pr_body)]


def _get_commit_branch(repo: Repository, sha: str) -> str:
    """Try to determine which branch a commit is on."""
    try:
        branches = list(repo.get_commit(sha).get_pulls())
        if branches:
            return branches[0].head.ref
    except Exception:
        pass
    return "unknown"


def get_aging_prs(repo: Repository, team_logins: list[str],
                  sla_hours: int = 48) -> list[dict]:
    """Get PRs open longer than SLA without a review."""
    aging = []
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=sla_hours)
    try:
        for pr in repo.get_pulls(state="open"):
            if pr.created_at.replace(tzinfo=timezone.utc) > cutoff:
                continue
            if pr.user.login not in team_logins:
                continue
            age_days = (datetime.now(tz=timezone.utc) -
                        pr.created_at.replace(tzinfo=timezone.utc)).days
            aging.append({
                "number": pr.number,
                "title": pr.title[:60],
                "repo": repo.full_name,
                "age_days": age_days,
                "url": pr.html_url,
            })
    except Exception as e:
        logger.warning(f"Failed to fetch aging PRs: {e}")
    return aging


def fetch_all_repos(config: dict, target_date: Optional[str] = None) -> dict:
    """Fetch activity from all configured repos."""
    if target_date is None:
        target_date = date.today().isoformat()

    since_dt = datetime.fromisoformat(target_date + "T00:00:00").replace(tzinfo=timezone.utc)
    team_logins = get_team_logins()

    # Use SCRAUT_GITHUB_TOKEN for external repo access
    import os
    token = os.environ.get("SCRAUT_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    g = Github(token)

    all_activity = {login: {
        "commits": [],
        "prs_opened": [],
        "prs_merged": [],
        "prs_reviewed": [],
        "ci_failures": [],
    } for login in team_logins}

    repos_config = config.get("repos", [])
    aging_prs = []

    for repo_cfg in repos_config:
        if not repo_cfg.get("enabled", True):
            continue
        try:
            repo = g.get_repo(repo_cfg["url"])
            logger.info(f"Syncing {repo.full_name}")
            member_data = fetch_activity_for_repo(repo, team_logins, since_dt)
            aging = get_aging_prs(repo, team_logins)
            aging_prs.extend(aging)

            # Merge into all_activity
            for login in team_logins:
                for key in member_data[login]:
                    all_activity[login][key].extend(member_data[login][key])

        except Exception as e:
            logger.error(f"Failed to sync {repo_cfg['url']}: {e}")

    # Calculate team summary
    team_summary = {
        "prs_opened": sum(len(all_activity[l]["prs_opened"]) for l in team_logins),
        "prs_merged": sum(len(all_activity[l]["prs_merged"]) for l in team_logins),
        "prs_reviewed": sum(len(all_activity[l]["prs_reviewed"]) for l in team_logins),
        "total_commits": sum(len(all_activity[l]["commits"]) for l in team_logins),
        "aging_prs": aging_prs,
    }

    return {
        "date": target_date,
        "repos": [r["url"] for r in repos_config if r.get("enabled", True)],
        "team_filter": team_logins,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "members": all_activity,
        "team_summary": team_summary,
    }


def write_activity_files(activity: dict, config: dict) -> None:
    """Write activity.json and activity.md to the sprint's code folder."""
    root = get_workspace_root()
    sprint_num = get_current_sprint()
    target_date = activity["date"]
    code_dir = get_sprint_output_folder(sprint_num) / "code" / target_date
    code_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON (machine-readable)
    atomic_write(code_dir / "activity.json", json.dumps(activity, indent=2))

    # Write markdown (human-readable)
    md = generate_activity_md(activity, config)
    atomic_write(code_dir / "activity.md", md)
    logger.info(f"Activity files written to {code_dir}")


def generate_activity_md(activity: dict, config: dict) -> str:
    members_map = {m["login"]: m["display"] for m in config["team"]["members"]}
    date_str = activity["date"]
    repos = ", ".join(f"`{r}`" for r in activity.get("repos", []))

    lines = [
        f"<!-- BOT-GENERATED -->\n",
        f"# Code Activity: {date_str}\n",
        f"*Sources: {repos}*\n\n",
    ]

    for login, data in activity.get("members", {}).items():
        display = members_map.get(login, login)
        has_activity = any([data["commits"], data["prs_opened"],
                            data["prs_merged"], data["prs_reviewed"]])

        lines.append(f"## {display}\n")
        if not has_activity:
            lines.append("_No activity detected today._\n\n")
            continue

        if data["prs_merged"]:
            for pr in data["prs_merged"]:
                lines.append(f"- {ICONS['pr_merged']} Merged PR #{pr['number']}: \"{pr['title']}\" "
                             f"(`{pr['repo'].split('/')[-1]}`)\n")

        if data["prs_opened"]:
            for pr in data["prs_opened"]:
                lines.append(f"- {ICONS['pr_opened']} Opened PR #{pr['number']}: \"{pr['title']}\" "
                             f"(`{pr['repo'].split('/')[-1]}`)\n")

        if data["prs_reviewed"]:
            for review in data["prs_reviewed"]:
                lines.append(f"- {ICONS['pr_reviewed']} Reviewed PR #{review['number']}: "
                             f"\"{review['title']}\" ({review['review_type']})\n")

        if data["commits"]:
            for commit in data["commits"][:5]:  # Cap at 5 commits per person per day
                lines.append(f"- {ICONS['commit']} `{commit['sha']}` {commit['message']} "
                             f"({commit['branch']})\n")
            if len(data["commits"]) > 5:
                lines.append(f"- _{len(data['commits']) - 5} more commits_\n")

        lines.append("\n")

    # Aging PRs
    aging = activity.get("team_summary", {}).get("aging_prs", [])
    if aging:
        lines.append("## ⚠️ Aging PRs (need attention)\n")
        for pr in aging:
            lines.append(f"- PR #{pr['number']} \"{pr['title']}\" — "
                        f"{pr['age_days']} days old (`{pr['repo'].split('/')[-1]}`)\n")
        lines.append("\n")

    summary = activity.get("team_summary", {})
    lines.append(
        f"## Team Summary\n"
        f"- PRs opened: {summary.get('prs_opened', 0)} · "
        f"merged: {summary.get('prs_merged', 0)} · "
        f"reviewed: {summary.get('prs_reviewed', 0)}\n"
        f"- Total commits: {summary.get('total_commits', 0)}\n"
        f"- Aging PRs: {len(aging)}\n"
    )
    return "".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    activity = fetch_all_repos(config, args.date)
    if args.dry_run:
        print(json.dumps(activity, indent=2))
    else:
        write_activity_files(activity, config)
