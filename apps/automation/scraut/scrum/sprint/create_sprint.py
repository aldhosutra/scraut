"""
scrum/sprint/create_sprint.py
Create a new sprint: folder structure, meta.md, GitHub milestone.
"""
import argparse
import logging
from datetime import date, timedelta
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_sprint_folder, get_sprint_output_folder
from scraut.platform.utils.file_utils import create_if_not_exists, atomic_write, today_str
from scraut.platform.utils.date_utils import get_sprint_dates
from scraut.platform.github.api import get_github_client, create_milestone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

META_TEMPLATE = """# Sprint {sprint_num}
- Period: {start_date} → {end_date} ({work_days} working days)
- Goal: [Set during sprint planning — see planning PR]
- Team: {team_names}
- Committed: TBD story points across TBD issues
- Milestone: https://github.com/{repo}/milestone/{milestone_number}
- Capacity note: [Check team/capacity.md for OOO]

## Issues in sprint
| Issue | Title | Epic | SP | Assignee |
|-------|-------|------|----|---------|
"""


def create_sprint(sprint_num: int, repo_name: str, config: dict,
                  dry_run: bool = False) -> None:
    root = get_workspace_root()
    sprint_folder = get_sprint_folder(sprint_num)
    sprint_output_folder = get_sprint_output_folder(sprint_num)

    subdirs = [
        "standup",
        "retrospective",
        "grooming",
        "decisions",
        "adr",
    ]
    output_subdirs = ["standup/summary", "review", "incidents", "code"]

    if dry_run:
        logger.info(f"[DRY RUN] Would create sprint/{sprint_num:02d}/ with subdirs: {subdirs}")
        logger.info(f"[DRY RUN] Would create .scraut/sprint/{sprint_num:02d}/ with subdirs: {output_subdirs}")
        logger.info(f"[DRY RUN] Would create GitHub milestone: Sprint {sprint_num:02d}")
        return

    for subdir in subdirs:
        (sprint_folder / subdir).mkdir(parents=True, exist_ok=True)

    for subdir in output_subdirs:
        (sprint_output_folder / subdir).mkdir(parents=True, exist_ok=True)

    start, end = get_sprint_dates(sprint_num, config)
    team_names = ", ".join(m["display"] for m in config["team"]["members"])

    g = get_github_client()
    repo = g.get_repo(repo_name)
    ms = create_milestone(repo, f"Sprint {sprint_num:02d}",
                          f"Sprint {sprint_num}: {start} → {end}")

    meta_content = META_TEMPLATE.format(
        sprint_num=sprint_num,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        work_days=10,
        team_names=team_names,
        repo=repo_name,
        milestone_number=ms.number,
    )
    meta_path = sprint_folder / "meta.md"
    create_if_not_exists(meta_path, meta_content)

    grooming_path = sprint_folder / "grooming" / "backlog-ideas.md"
    create_if_not_exists(grooming_path,
        "# Backlog Ideas\n<!-- Append new ideas below. Anyone can add. -->\n\n")

    logger.info(f"✓ Created sprint/{sprint_num:02d} input and output folder structure")
    logger.info(f"✓ Created GitHub milestone: Sprint {sprint_num:02d} (#{ms.number})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True, help="org/repo")
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    create_sprint(args.sprint, args.repo, config, args.dry_run)
