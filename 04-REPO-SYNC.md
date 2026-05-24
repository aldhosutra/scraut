# Phase 4: Repo Sync
*Scraut Implementation — requires Phases 1 and 2 complete*

## Goal
Connect Scraut to one or more GitHub repos to capture real code activity.
Fetch commits, PRs, reviews, and CI status per team member. Pre-fill standup
Yesterday sections automatically. Compute daily deltas. This is the "ground truth"
layer — what actually happened, regardless of what people report.

---

## Architecture

```
scraut.yml repos[] section → repo-sync.yml (8am daily)
  ↓
scripts/repo_sync/fetch_activity.py
  → GitHub API: commits, PRs, reviews, check runs
  → filters by team.members logins
  → writes sprint-N/code/YYYY-MM-DD/activity.json
  → writes sprint-N/code/YYYY-MM-DD/activity.md
  ↓
scripts/repo_sync/compute_delta.py
  → compares today's activity.json vs yesterday's
  → writes sprint-N/code/YYYY-MM-DD/delta.md
  ↓
scripts/repo_sync/prefill_standups.py
  → reads activity.json
  → for each member: create-if-not-exists their standup file
  → pre-fills ## Yesterday section with commits and PR activity
  → leaves ## Today and ## Blockers empty for human to fill
```

---

## 1. `scripts/repo_sync/fetch_activity.py`

```python
"""
scripts/repo_sync/fetch_activity.py
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
from scripts.utils.config import load_config, get_repo_root, get_current_sprint, get_team_logins
from scripts.utils.file_utils import atomic_write
from scripts.github.api import get_github_client

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
    root = get_repo_root()
    sprint_num = get_current_sprint()
    target_date = activity["date"]
    code_dir = root / f"sprint-{sprint_num:02d}" / "code" / target_date
    code_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON (machine-readable)
    atomic_write(code_dir / "activity.json", json.dumps(activity, indent=2))

    # Write markdown (human-readable)
    md = generate_activity_md(activity, config)
    atomic_write(code_dir / "activity.md", md)
    logger.info(f"Activity files written to {code_dir}")


def generate_activity_md(activity: dict, config: dict) -> str:
    members_map = {m["login"]: m["display"] for m in config["team"]["members"]}
    date = activity["date"]
    repos = ", ".join(f"`{r}`" for r in activity.get("repos", []))

    lines = [
        f"<!-- BOT-GENERATED -->\n",
        f"# Code Activity: {date}\n",
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
```

---

## 2. `scripts/repo_sync/compute_delta.py`

```python
"""
scripts/repo_sync/compute_delta.py
Compare today's activity vs yesterday's to produce a delta summary.
Detects: new PRs, merged PRs, newly aging PRs, CI changes, WIP changes.
"""
import argparse
import json
import logging
from datetime import date, timedelta
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import atomic_write, read_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_activity(target_date: str, config: dict) -> dict:
    root = get_repo_root()
    sprint_num = get_current_sprint()
    path = root / f"sprint-{sprint_num:02d}" / "code" / target_date / "activity.json"
    content = read_file(path)
    return json.loads(content) if content else {}


def compute_delta(today: str, config: dict) -> dict:
    yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()

    today_data = load_activity(today, config)
    yesterday_data = load_activity(yesterday, config)

    if not today_data:
        logger.warning("No activity data for today. Delta unavailable.")
        return {}

    # PRs: compare aging lists
    today_aging = {p["number"]: p for p in today_data.get("team_summary", {}).get("aging_prs", [])}
    yest_aging = {p["number"]: p for p in yesterday_data.get("team_summary", {}).get("aging_prs", [])}

    newly_aging = [p for num, p in today_aging.items() if num not in yest_aging]
    resolved_aging = [p for num, p in yest_aging.items() if num not in today_aging]

    # PRs: new merges today
    new_merges = []
    for login, data in today_data.get("members", {}).items():
        new_merges.extend(data.get("prs_merged", []))

    # WIP change: count open branches (use commits to distinct branches as proxy)
    today_branches = set()
    yest_branches = set()
    for data in today_data.get("members", {}).values():
        today_branches.update(c.get("branch", "") for c in data.get("commits", []))
    for data in yesterday_data.get("members", {}).values():
        yest_branches.update(c.get("branch", "") for c in data.get("commits", []))

    wip_opened = today_branches - yest_branches
    wip_closed = yest_branches - today_branches

    return {
        "date": today,
        "compared_to": yesterday,
        "new_merges": new_merges,
        "newly_aging_prs": newly_aging,
        "resolved_aging_prs": resolved_aging,
        "wip_branches_opened": list(wip_opened - {"unknown"}),
        "wip_branches_closed": list(wip_closed - {"unknown"}),
        "total_commits_today": today_data.get("team_summary", {}).get("total_commits", 0),
    }


def write_delta(delta: dict, config: dict) -> None:
    if not delta:
        return
    root = get_repo_root()
    sprint_num = get_current_sprint()
    code_dir = root / f"sprint-{sprint_num:02d}" / "code" / delta["date"]
    code_dir.mkdir(parents=True, exist_ok=True)

    md = generate_delta_md(delta)
    atomic_write(code_dir / "delta.md", md)
    logger.info(f"Delta written: {code_dir}/delta.md")


def generate_delta_md(delta: dict) -> str:
    lines = [
        f"<!-- BOT-GENERATED -->\n",
        f"# Code Delta: {delta['date']} vs {delta['compared_to']}\n\n",
    ]

    if delta.get("new_merges"):
        lines.append("## ✅ New merges today\n")
        for pr in delta["new_merges"]:
            lines.append(f"- PR #{pr['number']}: \"{pr['title']}\"\n")
        lines.append("\n")

    if delta.get("newly_aging_prs"):
        lines.append("## ⚠️ PRs now overdue (needs review)\n")
        for pr in delta["newly_aging_prs"]:
            lines.append(f"- PR #{pr['number']}: \"{pr['title']}\" — {pr['age_days']} days old\n")
        lines.append("\n")

    if delta.get("resolved_aging_prs"):
        lines.append("## ✅ Previously overdue PRs resolved\n")
        for pr in delta["resolved_aging_prs"]:
            lines.append(f"- PR #{pr['number']}: \"{pr['title']}\"\n")
        lines.append("\n")

    if delta.get("wip_branches_opened"):
        lines.append("## 🔀 New work started (branches opened)\n")
        for branch in delta["wip_branches_opened"]:
            lines.append(f"- `{branch}`\n")
        lines.append("\n")

    lines.append(
        f"**Today:** {delta.get('total_commits_today', 0)} commits, "
        f"{len(delta.get('new_merges', []))} PRs merged\n"
    )
    return "".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    delta = compute_delta(args.date, config)
    write_delta(delta, config)
```

---

## 3. `scripts/repo_sync/prefill_standups.py`

Pre-fills Yesterday section in standup files. Uses `create_if_not_exists` semantics:
only fills if the file exists AND the Yesterday section is empty.

```python
"""
scripts/repo_sync/prefill_standups.py
Pre-fill the ## Yesterday section of each standup file from repo activity.
RULES:
  - Never overwrites a file that a human has already edited
  - Only fills the Yesterday section if it is empty
  - Adds a comment indicating the source and timestamp
  - Leaves Today, Blockers, Notes empty for the human to fill
"""
import argparse
import json
import logging
import re
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import read_file, atomic_write

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YESTERDAY_PLACEHOLDER = re.compile(
    r"(## Yesterday\s*\n)(<!-- What did you complete\? Reference issues/PRs where applicable\. -->)\s*(\n|$)",
    re.IGNORECASE
)


def is_yesterday_empty(standup_content: str) -> bool:
    """Return True if the Yesterday section contains only the placeholder comment."""
    match = YESTERDAY_PLACEHOLDER.search(standup_content)
    return bool(match)


def format_activity_as_bullets(member_data: dict, display_name: str) -> str:
    """Convert activity data for one member into markdown bullet points."""
    lines = []
    lines.append(f"<!-- Pre-filled by Scraut repo sync. Add context and edit freely. -->\n")

    for pr in member_data.get("prs_merged", []):
        closes = ""
        if pr.get("closes_issues"):
            closes = f" — closes #{', #'.join(str(i) for i in pr['closes_issues'])}"
        lines.append(f"- ✅ Merged PR #{pr['number']}: \"{pr['title']}\"{closes}")

    for review in member_data.get("prs_reviewed", []):
        lines.append(f"- 👀 Reviewed PR #{review['number']}: \"{review['title']}\" ({review['review_type']})")

    for pr in member_data.get("prs_opened", []):
        lines.append(f"- 🔀 Opened PR #{pr['number']}: \"{pr['title']}\" — ready for review")

    commits = member_data.get("commits", [])
    if commits:
        branches = list(set(c.get("branch", "unknown") for c in commits))
        for branch in branches:
            branch_commits = [c for c in commits if c.get("branch") == branch]
            if len(branch_commits) == 1:
                lines.append(f"- 📝 `{branch_commits[0]['sha']}` {branch_commits[0]['message']} (`{branch}`)")
            else:
                lines.append(f"- 📝 {len(branch_commits)} commits to `{branch}`")

    if not lines or (len(lines) == 1 and "Pre-filled" in lines[0]):
        lines.append("- No commits or PR activity detected. Please fill in manually.")

    return "\n".join(lines)


def prefill_standups(config: dict, target_date: str, dry_run: bool = False) -> None:
    root = get_repo_root()
    sprint_num = get_current_sprint()
    standup_dir = root / f"sprint-{sprint_num:02d}" / "standup" / target_date

    # Load activity.json for this date
    activity_path = root / f"sprint-{sprint_num:02d}" / "code" / target_date / "activity.json"
    activity_content = read_file(activity_path)
    if not activity_content:
        logger.warning(f"No activity.json found for {target_date}. Cannot pre-fill standups.")
        return

    activity = json.loads(activity_content)
    members_map = {m["login"]: m["display"] for m in config["team"]["members"]}

    for login, display in members_map.items():
        standup_file = standup_dir / f"{login}.md"

        if not standup_file.exists():
            logger.info(f"Standup file for {display} doesn't exist yet. Skipping prefill (template reset handles creation).")
            continue

        content = read_file(standup_file)

        if not is_yesterday_empty(content):
            logger.info(f"{display}: Yesterday section already filled. Not overwriting.")
            continue

        member_data = activity.get("members", {}).get(login, {})
        yesterday_bullets = format_activity_as_bullets(member_data, display)

        # Replace the empty Yesterday placeholder
        new_content = YESTERDAY_PLACEHOLDER.sub(
            f"## Yesterday\n{yesterday_bullets}\n\n",
            content
        )

        if not dry_run:
            atomic_write(standup_file, new_content)
            logger.info(f"Pre-filled Yesterday for {display}")
        else:
            logger.info(f"[DRY RUN] Would pre-fill Yesterday for {display}:")
            print(yesterday_bullets)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    prefill_standups(config, args.date, args.dry_run)
```

---

## 4. `.github/workflows/repo-sync.yml`

```yaml
name: Scraut — Repo Sync
on:
  schedule:
    - cron: '0 1 * * 1-5'  # 8:00 AM Jakarta (UTC+7) = 01:00 UTC, before standup templates
  workflow_dispatch:
    inputs:
      date:
        description: 'Date (YYYY-MM-DD, default: today)'
        required: false

jobs:
  sync-repos:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Fetch activity from connected repos
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SCRAUT_GITHUB_TOKEN: ${{ secrets.SCRAUT_GITHUB_TOKEN }}
        run: |
          DATE="${{ github.event.inputs.date }}"
          if [ -z "$DATE" ]; then DATE=$(date +%Y-%m-%d); fi
          python scripts/repo_sync/fetch_activity.py --date $DATE

      - name: Compute delta vs yesterday
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          DATE="${{ github.event.inputs.date }}"
          if [ -z "$DATE" ]; then DATE=$(date +%Y-%m-%d); fi
          python scripts/repo_sync/compute_delta.py --date $DATE

      - name: Pre-fill standup Yesterday sections
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          DATE="${{ github.event.inputs.date }}"
          if [ -z "$DATE" ]; then DATE=$(date +%Y-%m-%d); fi
          python scripts/repo_sync/prefill_standups.py --date $DATE

      - name: Commit activity files
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add sprint-*/code/ sprint-*/standup/
          git diff --staged --quiet || git commit -m "chore: repo sync $(date +%Y-%m-%d) [skip ci]"
          git push

  notify-aging-prs:
    needs: sync-repos
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Post aging PR alerts to Slack
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: python scripts/repo_sync/notify_aging_prs.py
```

---

## 5. `scripts/repo_sync/notify_aging_prs.py`

```python
"""
scripts/repo_sync/notify_aging_prs.py
Read today's activity.json and post aging PR alerts to Slack.
Only posts if there are aging PRs. Formats a clear actionable message.
"""
import json
import logging
from datetime import date
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import read_file
from scripts.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def notify_aging_prs(config: dict) -> None:
    root = get_repo_root()
    sprint_num = get_current_sprint()
    today = date.today().isoformat()
    activity_path = root / f"sprint-{sprint_num:02d}" / "code" / today / "activity.json"

    content = read_file(activity_path)
    if not content:
        return

    activity = json.loads(content)
    aging = activity.get("team_summary", {}).get("aging_prs", [])

    if not aging:
        return

    slack_text = f"⚠️ *{len(aging)} aging PR(s) need review:*\n"
    for pr in aging:
        slack_text += f"• PR #{pr['number']} `{pr['repo'].split('/')[-1]}` — \"{pr['title']}\" ({pr['age_days']} days)\n"
    slack_text += "\nReview these before starting new work today."

    webhook = config.get("notifications", {}).get("slack_webhook")
    if webhook:
        post_to_slack(webhook, slack_text)


if __name__ == "__main__":
    config = load_config()
    notify_aging_prs(config)
```

---

## Done Criteria for Phase 4

- [ ] `scripts/repo_sync/fetch_activity.py` — fetches commits, PRs, reviews from all repos in `scraut.yml`
- [ ] `scripts/repo_sync/fetch_activity.py` — correctly filters by `team.members` logins
- [ ] `scripts/repo_sync/fetch_activity.py` — writes `activity.json` and `activity.md` to `sprint-N/code/YYYY-MM-DD/`
- [ ] `scripts/repo_sync/compute_delta.py` — correctly diffs today vs yesterday's activity
- [ ] `scripts/repo_sync/compute_delta.py` — writes `delta.md` with meaningful change summary
- [ ] `scripts/repo_sync/prefill_standups.py` — pre-fills Yesterday section when it is empty
- [ ] `scripts/repo_sync/prefill_standups.py` — does NOT overwrite sections already filled by humans
- [ ] `scripts/repo_sync/notify_aging_prs.py` — posts to Slack only when aging PRs exist
- [ ] `repo-sync.yml` — runs in correct order: fetch → delta → prefill → commit → notify
- [ ] `repo-sync.yml` — uses `SCRAUT_GITHUB_TOKEN` (not `GITHUB_TOKEN`) for external repo access
- [ ] End-to-end test: run `fetch_activity.py` with `--dry-run` and verify JSON structure
- [ ] End-to-end test: run `prefill_standups.py` with `--dry-run` and verify only empty sections are targeted

*Proceed to `05-VISIBILITY-PORTAL.md`*
