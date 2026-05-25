"""
scrum/sprint/close_sprint.py
Close a sprint: close GitHub milestone, label deferred issues,
calculate velocity, write sprint summary stats, increment current_sprint in scraut.yml.
"""
import argparse
import logging
import re
from pathlib import Path
from scraut.platform.utils.config import load_config, get_repo_root, format_sprint_num, get_folder_padding
from scraut.platform.utils.file_utils import read_file, atomic_write
from scraut.platform.github.api import (get_github_client, get_issues, get_sp_from_issue,
                                  add_label_to_issue, remove_label_from_issue,
                                  ensure_label_exists)
from scraut.scrum.sprint.calculate_velocity import calculate_sprint_velocity
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def close_sprint(sprint_num: int, repo_name: str, config: dict) -> dict:
    """
    Close a sprint:
    1. Close the GitHub milestone
    2. Move open issues back to backlog (remove sprint label, keep in-sprint label for tracking)
    3. Calculate and return velocity stats
    4. Increment current_sprint in scraut.yml
    """
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_label = f"sprint-{format_sprint_num(sprint_num, get_folder_padding())}"

    # Close the GitHub milestone
    for ms in repo.get_milestones(state="open"):
        if ms.title == f"Sprint {format_sprint_num(sprint_num, get_folder_padding())}":
            ms.edit(state="closed")
            logger.info(f"Closed milestone: {ms.title}")
            break

    # Get all sprint issues
    all_issues = get_issues(repo, labels=[sprint_label], state="all")
    closed = [i for i in all_issues if i.state == "closed"]
    open_issues = [i for i in all_issues if i.state == "open"]

    # Label deferred issues for tracking
    ensure_label_exists(repo, "deferred", color="e4e669", description="Deferred from sprint")
    for issue in open_issues:
        add_label_to_issue(issue, "deferred")
        remove_label_from_issue(issue, "in-sprint")
        logger.info(f"Deferred: #{issue.number} — {issue.title[:50]}")

    # Calculate velocity
    velocity = calculate_sprint_velocity(sprint_num, repo_name)

    # Increment current_sprint in scraut.yml
    root = get_repo_root()
    scraut_yml_path = root / "scraut.yml"
    content = read_file(scraut_yml_path)
    new_content = re.sub(
        r"(current_sprint:\s*)\d+",
        f"\\g<1>{sprint_num + 1}",
        content
    )
    atomic_write(scraut_yml_path, new_content)
    logger.info(f"Incremented current_sprint to {sprint_num + 1}")

    logger.info(
        f"Sprint {sprint_num} closed: "
        f"{velocity['completed_sp']}/{velocity['planned_sp']} sp "
        f"({len(closed)}/{len(all_issues)} issues completed)"
    )
    return velocity


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    close_sprint(args.sprint, args.repo, config)
