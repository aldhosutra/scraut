"""
scrum/visibility/sync_board.py
Sync GitHub Projects v2 board columns from text-file derived state.
Reads artifacts → derives state → updates board via GraphQL.
Text files are ALWAYS the source of truth — never reads the board to make decisions.
"""
import argparse
import logging
import os
from typing import Optional

from scraut.platform.github.api import get_github_client, get_issues
from scraut.platform.github.projects import (
    get_field_ids, get_project_id, get_project_items,
    update_item_status, update_item_text_field,
)
from scraut.platform.utils.config import get_current_sprint, load_config, format_sprint_num, get_folder_padding
from scraut.scrum.visibility.derive_state import IssueState, StateDeriver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_repo_name() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise ValueError("GITHUB_REPOSITORY env var not set")
    return repo


def _get_project_number(config: dict) -> Optional[int]:
    return config.get("portal", {}).get("project_number")


def _board_sync_enabled(config: dict) -> bool:
    # Default True — board sync is on unless explicitly disabled
    return config.get("portal", {}).get("sync_board", True)


def sync_board(config: dict, dry_run: bool = False) -> dict[int, str]:
    """
    Derive state for all in-sprint issues and update the GitHub Projects board.
    Returns mapping of issue_number → new_state string.
    """
    if not _board_sync_enabled(config):
        logger.info("portal.sync_board is false — skipping board sync")
        return {}

    repo_name = _get_repo_name()
    project_number = _get_project_number(config)
    if not project_number:
        logger.warning(
            "portal.sync_board is true but portal.project_number is not set — skipping board sync. "
            "Add `project_number: <N>` to the portal section of workspace/scraut.yml "
            "(find N in your GitHub Projects URL: github.com/orgs/your-org/projects/N)"
        )
        return {}

    gh = get_github_client()
    repo = gh.get_repo(repo_name)
    sprint_num = get_current_sprint()
    sprint_label = f"sprint-{format_sprint_num(sprint_num, get_folder_padding())}"

    issues = get_issues(repo, labels=[sprint_label], state="all")
    logger.info(f"Found {len(issues)} issues with label {sprint_label}")

    deriver = StateDeriver(sprint_num=sprint_num)
    issue_dicts = [
        {"number": i.number, "title": i.title, "state": i.state}
        for i in issues
    ]
    state_map = deriver.derive_batch(issue_dicts, use_llm=True)

    if dry_run:
        for num, state in sorted(state_map.items()):
            logger.info(f"[DRY-RUN] Issue #{num} → {state.value}")
        return {num: s.value for num, s in state_map.items()}

    owner = repo_name.split("/")[0]
    project_id = get_project_id(owner, project_number)
    fields = get_field_ids(project_id)

    status_field = fields.get("Status", {})
    status_field_id = status_field.get("id")
    status_options = status_field.get("options", {})

    health_field = fields.get("Health", {})
    health_field_id = health_field.get("id")
    health_options = health_field.get("options", {})

    items = get_project_items(project_id)
    issue_to_item: dict[int, str] = {}
    for item in items:
        content = item.get("content") or {}
        num = content.get("number")
        if num:
            issue_to_item[num] = item["id"]

    for issue_num, state in state_map.items():
        item_id = issue_to_item.get(issue_num)
        if not item_id:
            logger.warning(f"Issue #{issue_num} not in project — skipping")
            continue

        # Blocked maps to "In Progress" on the Status column; Health → "blocked"
        status_name = "In Progress" if state == IssueState.BLOCKED else state.value
        option_id = status_options.get(status_name)
        if option_id and status_field_id:
            update_item_status(project_id, item_id, status_field_id, option_id)
            logger.info(f"Issue #{issue_num} → {status_name}")

        if health_field_id:
            health_val = "blocked" if state == IssueState.BLOCKED else "on-track"
            health_option = health_options.get(health_val)
            if health_option:
                update_item_status(project_id, item_id, health_field_id, health_option)

    return {num: s.value for num, s in state_map.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    result = sync_board(config, dry_run=args.dry_run)
    logger.info(f"Processed {len(result)} issues")
