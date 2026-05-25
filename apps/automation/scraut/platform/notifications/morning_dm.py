"""
lib/notifications/morning_dm.py
Send morning Slack DMs to each team member with their standup link for today.
"""
import argparse
import logging
import os
from datetime import date

from scraut.platform.notifications.slack_post import send_slack_dm
from scraut.platform.utils.config import get_current_sprint, load_config, format_sprint_num, get_folder_padding, get_scraut_root
from scraut.platform.utils.date_utils import is_working_day

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _standup_link(repo_name: str, sprint_num: int, today: str, login: str) -> str:
    path = f"workspace/sprint/{format_sprint_num(sprint_num, get_folder_padding())}/standup/{today}/{login}.md"
    return f"https://github.com/{repo_name}/edit/main/{path}"


def send_morning_dms(config: dict, dry_run: bool = False) -> None:
    today_date = date.today()
    if not is_working_day(today_date, config, get_scraut_root()):
        logger.info(f"Skipping morning DMs — {today_date.isoformat()} is a non-working day")
        return

    sprint_num = get_current_sprint()
    today = today_date.isoformat()
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
