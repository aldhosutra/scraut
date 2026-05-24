"""
lib/notifications/weekly_digest.py
Generate and send the weekly stakeholder digest via Slack and/or email.
"""
import argparse
import logging
import os
import re
from datetime import date, timedelta

from scraut.platform.llm.client import complete
from scraut.platform.llm.prompts import WEEKLY_DIGEST_NARRATIVE
from scraut.platform.notifications.send_email import send_email
from scraut.platform.notifications.slack_post import post_to_slack
from scraut.platform.utils.config import get_current_sprint, get_workspace_root, load_config, get_sprint_folder, get_sprint_output_folder, get_scraut_root
from scraut.platform.utils.file_utils import read_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_sprint_review(sprint_num: int) -> str:
    return read_file(get_sprint_output_folder(sprint_num) / "review" / "sprint-review.md")


def _load_velocity_insights() -> str:
    return read_file(get_scraut_root() / "insights" / "velocity-trends.md")


def _load_blocker_insights() -> str:
    return read_file(get_scraut_root() / "insights" / "blocker-patterns.md")


def _load_standup_summaries(sprint_num: int, days_back: int = 5) -> list[str]:
    root = get_workspace_root()
    today = date.today()
    summaries = []
    for i in range(days_back):
        d = (today - timedelta(days=i)).isoformat()
        content = read_file(get_sprint_output_folder(sprint_num) / "standup" / "summary" / f"{d}.md")
        if content:
            summaries.append(content)
    return summaries


def generate_digest_markdown(config: dict) -> str:
    sprint_num = get_current_sprint()
    sprint_review = _load_sprint_review(sprint_num)
    velocity = _load_velocity_insights()
    blockers = _load_blocker_insights()
    summaries = _load_standup_summaries(sprint_num)

    combined_summaries = "\n\n---\n\n".join(summaries) if summaries else "No standup summaries yet this week."

    prompt = WEEKLY_DIGEST_NARRATIVE.format(
        sprint_num=sprint_num,
        sprint_review=sprint_review or "Not yet available.",
        standup_summaries=combined_summaries,
        velocity_trends=velocity or "Not yet available.",
        blocker_patterns=blockers or "Not yet available.",
        week_ending=date.today().isoformat(),
    )
    narrative = complete(prompt)
    if not narrative:
        narrative = f"Sprint {sprint_num} is in progress. See the team portal for live status."

    return f"<!-- BOT-GENERATED -->\n# Weekly Digest — Week ending {date.today().isoformat()}\n\n{narrative}"


def _markdown_to_html(markdown: str) -> str:
    """Convert markdown digest to a simple HTML email body."""
    clean = re.sub(r"<!--.*?-->", "", markdown, flags=re.DOTALL).strip()
    lines = []
    for line in clean.split("\n"):
        if line.startswith("# "):
            lines.append(f"<h1 style='color:#0969da'>{line[2:]}</h1>")
        elif line.startswith("## "):
            lines.append(f"<h2 style='color:#333;border-bottom:1px solid #eee;padding-bottom:4px'>{line[3:]}</h2>")
        elif line.startswith("- "):
            lines.append(f"<li>{line[2:]}</li>")
        elif line.strip() == "---":
            lines.append("<hr>")
        elif line.strip():
            lines.append(f"<p>{line}</p>")
    body = "\n".join(lines)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
max-width:680px;margin:2rem auto;color:#24292f;line-height:1.6}}
li{{margin-left:1.5rem;margin-bottom:4px}}
p{{margin-bottom:8px}}
</style></head>
<body>{body}
<hr><p style='color:#57606a;font-size:12px'>Sent by Scraut · auto-generated</p>
</body></html>"""


def send_weekly_digest(config: dict, dry_run: bool = False) -> None:
    markdown = generate_digest_markdown(config)
    notifications = config.get("notifications", {})
    slack_webhook = os.environ.get("SLACK_WEBHOOK") or notifications.get("slack_webhook", "")
    stakeholder_emails = notifications.get("stakeholder_emails", [])
    send_email_enabled = notifications.get("weekly_email", False)

    if dry_run:
        logger.info("[DRY-RUN] Weekly digest preview (first 400 chars):")
        logger.info(markdown[:400])
        return

    if slack_webhook:
        channel = config.get("team", {}).get("slack_channel", "#scraut-bot")
        post_to_slack(slack_webhook, markdown[:3000])
        logger.info(f"Weekly digest posted to Slack {channel}")

    if send_email_enabled and stakeholder_emails:
        html = _markdown_to_html(markdown)
        sprint_num = get_current_sprint()
        send_email(
            stakeholder_emails,
            f"Weekly Team Digest — Sprint {sprint_num} ({date.today().isoformat()})",
            html,
            markdown,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    send_weekly_digest(config, dry_run=args.dry_run)
