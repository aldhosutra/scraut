"""
scrum/standup/generate_summary.py
Read all standup files for today and generate a team digest using the LLM.
Posts to Slack and writes to sprint/NN/standup/summary/YYYY-MM-DD.md (bot-generated).
"""
import argparse
import logging
from datetime import date
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_current_sprint, get_sprint_folder, get_sprint_output_folder
from scraut.platform.utils.file_utils import atomic_write, read_file
from scraut.platform.llm.client import complete
from scraut.platform.llm.prompts import STANDUP_SUMMARY, SYSTEM_SCRUM_ASSISTANT
from scraut.platform.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def collect_standup_files(config: dict, target_date: str) -> dict:
    """Collect all standup files for the given date. Returns {display_name: content}."""
    root = get_workspace_root()
    sprint_num = get_current_sprint()
    standup_dir = get_sprint_folder(sprint_num) / "standup" / target_date
    members = {m["login"]: m["display"] for m in config["team"]["members"]}

    result = {}
    for login, display in members.items():
        file_path = standup_dir / f"{login}.md"
        content = read_file(file_path)
        if content:
            result[display] = content
        else:
            result[display] = f"# Standup — {display}\n\n*No update submitted today.*\n"

    if standup_dir.exists():
        for f in standup_dir.glob("agent-*.md"):
            content = read_file(f)
            agent_name = f.stem
            result[agent_name] = content

    return result


def generate_summary(config: dict, target_date: str, dry_run: bool = False) -> str:
    sprint_num = get_current_sprint()
    members = collect_standup_files(config, target_date)
    team_names = ", ".join(m["display"] for m in config["team"]["members"])

    standup_contents = "\n\n---\n\n".join(
        f"### {name}\n{content}" for name, content in members.items()
    )

    prompt = STANDUP_SUMMARY.format(
        date=target_date,
        sprint_num=sprint_num,
        team_names=team_names,
        standup_contents=standup_contents,
    )

    logger.info(f"Generating standup summary for {target_date}...")
    summary = complete(prompt, system=SYSTEM_SCRUM_ASSISTANT)

    if not summary:
        summary = f"# Standup Digest — {target_date}\n\n*LLM unavailable. See individual standup files.*\n"

    if not dry_run:
        root = get_workspace_root()
        summary_dir = get_sprint_output_folder(sprint_num) / "standup" / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(summary_dir / f"{target_date}.md",
                     f"<!-- BOT-GENERATED: do not edit manually -->\n\n{summary}")

        slack_webhook = config.get("notifications", {}).get("slack_webhook")
        if slack_webhook:
            post_to_slack(
                webhook_url=slack_webhook,
                text=f"*Daily Standup Digest — {target_date}*",
                blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": summary[:3000]}}]
            )
            logger.info("Posted to Slack")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    result = generate_summary(config, args.date, args.dry_run)
    if args.dry_run:
        print(result)
