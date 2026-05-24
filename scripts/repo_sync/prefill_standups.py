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
    lines.append(f"<!-- Pre-filled by Scraut repo sync. Add context and edit freely. -->")

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
