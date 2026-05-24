"""
scripts/sprint/close_sprint.py
Close a sprint: mark all open issues as deferred, close the GitHub milestone,
write sprint close metadata, and calculate final velocity.
Full implementation in Phase 3.
"""
import argparse
import logging
from scripts.utils.config import load_config, get_repo_root
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue, close_milestone
from scripts.sprint.calculate_velocity import calculate_sprint_velocity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def close_sprint(sprint_num: int, repo_name: str, config: dict,
                 dry_run: bool = False) -> dict:
    """Close a sprint: defer open issues, close milestone, record velocity."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_label = f"sprint-{sprint_num:02d}"

    open_issues = get_issues(repo, labels=[sprint_label], state="open")
    deferred = []
    for issue in open_issues:
        logger.info(f"Deferring #{issue.number}: {issue.title}")
        if not dry_run:
            issue.add_to_labels("deferred")

    velocity = calculate_sprint_velocity(sprint_num, repo_name)
    logger.info(f"Sprint {sprint_num} velocity: {velocity['completed_sp']} sp")

    milestone_title = f"Sprint {sprint_num:02d}"
    if not dry_run:
        close_milestone(repo, milestone_title)
        logger.info(f"Closed milestone: {milestone_title}")

    return velocity


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    close_sprint(args.sprint, args.repo, config, args.dry_run)
