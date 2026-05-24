"""
scripts/sprint/create_planning_pr.py
Create a sprint planning PR with LLM-suggested sprint goal and issue selection.
Team reviews and approves via PR comments. Full implementation in Phase 3.
"""
import argparse
import logging
from scripts.utils.config import load_config
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue
from scripts.llm.client import complete_json
from scripts.llm.prompts import SPRINT_GOAL_SUGGESTION, SYSTEM_SCRUM_ASSISTANT
from scripts.sprint.calculate_velocity import calculate_rolling_velocity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_planning_pr(sprint_num: int, repo_name: str, config: dict,
                       dry_run: bool = False) -> None:
    """Create a PR with sprint planning proposal for team review."""
    g = get_github_client()
    repo = g.get_repo(repo_name)

    backlog_issues = get_issues(repo, labels=["p:high"], state="open")
    velocity_data = calculate_rolling_velocity(repo_name)
    capacity = int(velocity_data.get("avg", 20) * config.get("sprint", {}).get("capacity_buffer", 0.85))

    backlog_items = "\n".join(
        f"- #{i.number}: {i.title} (sp:{get_sp_from_issue(i)})"
        for i in backlog_issues[:20]
    )

    prompt = SPRINT_GOAL_SUGGESTION.format(
        sprint_num=sprint_num,
        backlog_items=backlog_items,
        velocity=velocity_data.get("avg", 0),
        prev_goal="N/A",
        capacity=capacity,
    )

    suggestion = complete_json(prompt, system=SYSTEM_SCRUM_ASSISTANT)
    if not suggestion:
        logger.warning("LLM planning suggestion failed.")
        return

    logger.info(f"Suggested sprint goal: {suggestion.get('suggested_goal', '')}")
    logger.info(f"Proposed issues: {suggestion.get('proposed_issues', [])}")

    if not dry_run:
        logger.info("Planning PR creation requires branch setup — implement in Phase 3.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    create_planning_pr(args.sprint, args.repo, config, args.dry_run)
