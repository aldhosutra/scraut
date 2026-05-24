"""
scripts/sprint/generate_review.py
Generate sprint review narrative using LLM from sprint velocity and issue data.
Writes to sprint-N/review/sprint-review.md (bot-generated).
"""
import argparse
import logging
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import atomic_write
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue
from scripts.llm.client import complete
from scripts.llm.prompts import SPRINT_REVIEW_NARRATIVE, SYSTEM_SCRUM_ASSISTANT
from scripts.sprint.calculate_velocity import calculate_sprint_velocity, calculate_rolling_velocity
from scripts.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_review(sprint_num: int, repo_name: str, config: dict,
                    dry_run: bool = False) -> str:
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_label = f"sprint-{sprint_num:02d}"

    all_issues = get_issues(repo, labels=[sprint_label], state="all")
    closed = [i for i in all_issues if i.state == "closed"]
    open_issues = [i for i in all_issues if i.state == "open"]

    velocity = calculate_sprint_velocity(sprint_num, repo_name)
    rolling = calculate_rolling_velocity(repo_name)

    completed_list = "\n".join(f"- #{i.number}: {i.title}" for i in closed)
    deferred_list = "\n".join(f"- #{i.number}: {i.title}" for i in open_issues)

    prompt = SPRINT_REVIEW_NARRATIVE.format(
        sprint_num=sprint_num,
        sprint_goal="(see sprint meta)",
        planned_sp=velocity["planned_sp"],
        planned_issues=len(all_issues),
        completed_sp=velocity["completed_sp"],
        completed_issues=len(closed),
        deferred_issues=len(open_issues),
        velocity=velocity["completed_sp"],
        avg_velocity=rolling.get("avg", 0),
        ci_status="unknown",
        completed_list=completed_list or "None",
        deferred_list=deferred_list or "None",
        decisions="(see sprint decisions folder)",
    )

    logger.info(f"Generating sprint {sprint_num} review narrative...")
    narrative = complete(prompt, system=SYSTEM_SCRUM_ASSISTANT)

    if not narrative:
        narrative = f"# Sprint {sprint_num} Review\n\n*LLM unavailable.*\n"

    if not dry_run:
        root = get_repo_root()
        review_dir = root / f"sprint-{sprint_num:02d}" / "review"
        review_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(review_dir / "sprint-review.md",
                     f"<!-- BOT-GENERATED: do not edit manually -->\n\n{narrative}")
        logger.info(f"Sprint review written to sprint-{sprint_num:02d}/review/sprint-review.md")

        slack_webhook = config.get("notifications", {}).get("slack_webhook")
        if slack_webhook:
            post_to_slack(webhook_url=slack_webhook,
                          text=f"*Sprint {sprint_num} Review*\n\n{narrative[:2000]}")

    return narrative


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    generate_review(args.sprint, args.repo, config, args.dry_run)
