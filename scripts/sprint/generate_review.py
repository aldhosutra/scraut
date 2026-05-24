"""
scripts/sprint/generate_review.py
Generate sprint review document: velocity stats + LLM narrative.
Writes sprint-N/review/sprint-review.md (bot-generated zone).
Posts to Slack.
"""
import argparse
import logging
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import atomic_write, read_file, extract_section
from scripts.llm.client import complete
from scripts.llm.prompts import SPRINT_REVIEW_NARRATIVE, SYSTEM_SCRUM_ASSISTANT
from scripts.sprint.calculate_velocity import calculate_sprint_velocity, calculate_rolling_velocity
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue
from scripts.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_review(sprint_num: int, repo_name: str, config: dict) -> None:
    root = get_repo_root()
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_label = f"sprint-{sprint_num:02d}"

    velocity = calculate_sprint_velocity(sprint_num, repo_name)
    meta = read_file(root / f"sprint-{sprint_num:02d}" / "meta.md")
    sprint_goal = extract_section(meta, "Goal") if meta else "Not specified"

    all_issues = get_issues(repo, labels=[sprint_label], state="all")
    closed = [i for i in all_issues if i.state == "closed"]
    open_issues = [i for i in all_issues if i.state == "open"]

    completed_list = "\n".join(
        f"- #{i.number}: {i.title} (sp:{get_sp_from_issue(i)})"
        for i in closed
    )
    deferred_list = "\n".join(
        f"- #{i.number}: {i.title} (sp:{get_sp_from_issue(i)}) — deferred"
        for i in open_issues
    )

    decisions_dir = root / f"sprint-{sprint_num:02d}" / "decisions"
    decisions_text = ""
    if decisions_dir.exists():
        for f in sorted(decisions_dir.glob("*.md")):
            decisions_text += read_file(f) + "\n"

    rolling = calculate_rolling_velocity(repo_name, num_sprints=3)

    narrative = complete(
        SPRINT_REVIEW_NARRATIVE.format(
            sprint_num=sprint_num,
            sprint_goal=sprint_goal,
            planned_sp=velocity["planned_sp"],
            planned_issues=len(all_issues),
            completed_sp=velocity["completed_sp"],
            completed_issues=len(closed),
            deferred_issues=len(open_issues),
            velocity=velocity["completed_sp"],
            avg_velocity=rolling.get("avg", 0),
            ci_status="✅ Check GitHub Actions",
            completed_list=completed_list or "None",
            deferred_list=deferred_list or "None",
            decisions=decisions_text[:500] or "No recorded decisions",
        ),
        system=SYSTEM_SCRUM_ASSISTANT,
    )

    review_content = (
        f"<!-- BOT-GENERATED -->\n"
        f"# Sprint {sprint_num:02d} Review\n"
        f"*Generated: {date.today().isoformat()}*\n\n"
        f"## Summary\n\n{narrative}\n\n"
        f"## Metrics\n\n"
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| Story points planned | {velocity['planned_sp']} |\n"
        f"| Story points completed | {velocity['completed_sp']} |\n"
        f"| Completion rate | {round(velocity['completion_rate']*100)}% |\n"
        f"| Issues completed | {len(closed)} of {len(all_issues)} |\n"
        f"| Issues deferred | {len(open_issues)} |\n\n"
        f"## Completed\n\n{completed_list or '_None_'}\n\n"
        f"## Deferred\n\n{deferred_list or '_None_'}\n"
    )

    review_dir = root / f"sprint-{sprint_num:02d}" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(review_dir / "sprint-review.md", review_content)

    webhook = config.get("notifications", {}).get("slack_webhook")
    if webhook:
        post_to_slack(
            webhook,
            f"✅ *Sprint {sprint_num:02d} Review*\n"
            f"{velocity['completed_sp']}/{velocity['planned_sp']} sp "
            f"({round(velocity['completion_rate']*100)}%) · "
            f"{len(closed)}/{len(all_issues)} issues\n\n"
            + (narrative[:500] if narrative else "")
        )

    logger.info(f"Sprint review generated for sprint {sprint_num}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    generate_review(args.sprint, args.repo, config)
