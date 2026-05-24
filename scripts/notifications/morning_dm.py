"""
scripts/notifications/morning_dm.py
Send morning Slack DMs to each team member with their standup link for today.
"""
import argparse
import logging
import os
from datetime import date

from scripts.notifications.slack_post import send_slack_dm
from scripts.utils.config import get_current_sprint, load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _standup_link(repo_name: str, sprint_num: int, today: str, login: str) -> str:
    path = f"sprint-{sprint_num:02d}/standup/{today}/{login}.md"
    return f"https://github.com/{repo_name}/edit/main/{path}"


def send_morning_dms(config: dict, dry_run: bool = False) -> None:
    sprint_num = get_current_sprint()
    today = date.today().isoformat()
    repo_name = os.environ.get("GITHUB_REPOSITORY", "your-org/scraut")
    members = config.get("team", {}).get("members", [])

    sent = 0
    for member in members:
        login = member.get("login", "")
        slack_id = member.get("slack_id", "")
        display = member.get("display", login)

        if not slack_id:
            logger.warning(f"No Slack ID configured for {login} — skipping DM")
            continue

        link = _standup_link(repo_name, sprint_num, today, login)
        message = (
            f"Good morning, {display}! :sunrise:\n\n"
            f"It's time for your *Sprint {sprint_num}* standup.\n"
            f"Please update your standup file for today ({today}):\n"
            f"{link}\n\n"
            f"Fill in: *Yesterday*, *Today*, and *Blockers*. Takes ~2 minutes."
        )

        if dry_run:
            logger.info(f"[DRY-RUN] Would DM {display} ({slack_id})")
            continue

        ok = send_slack_dm(slack_id, message)
        if ok:
            logger.info(f"DM sent to {display} ({login})")
            sent += 1
        else:
            logger.error(f"Failed to DM {display} ({login})")

    if not dry_run:
        logger.info(f"Morning DMs sent: {sent}/{len(members)} members")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    send_morning_dms(config, dry_run=args.dry_run)
