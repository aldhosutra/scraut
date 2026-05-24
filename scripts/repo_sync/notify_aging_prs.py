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
