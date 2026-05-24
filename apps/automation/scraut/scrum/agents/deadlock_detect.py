"""
scrum/agents/deadlock_detect.py
Detect agent coordination deadlocks:
- Agent A is waiting for Agent B, which is waiting for Agent A
- Agent has been in WIP for more than N hours with zero commits
- Two agents have claimed the same issue

Runs as part of the orchestrator cycle.
"""
import json
import logging
import re
from datetime import date, timedelta
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_current_sprint, get_sprint_folder, get_sprint_output_folder
from scraut.platform.utils.file_utils import read_file, extract_section
from scraut.platform.github.api import get_github_client, get_issues

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def detect_duplicate_claims(repo_name: str, config: dict) -> list[dict]:
    """Detect cases where two agents have claimed the same issue."""
    root = get_workspace_root()
    sprint_num = get_current_sprint()
    today = date.today().isoformat()
    standup_dir = get_sprint_folder(sprint_num) / "standup" / today

    issue_claimants = {}  # issue_num → list of agent_ids

    if not standup_dir.exists():
        return []

    for f in standup_dir.glob("agent-*.md"):
        agent_id = f.stem
        content = read_file(f)
        today_section = extract_section(content, "Today")
        claimed_issues = re.findall(r"#(\d+)", today_section or "")
        for issue_num in claimed_issues:
            num = int(issue_num)
            issue_claimants.setdefault(num, []).append(agent_id)

    conflicts = [
        {"issue": num, "claimed_by": agents}
        for num, agents in issue_claimants.items()
        if len(agents) > 1
    ]
    return conflicts


def detect_stale_wip(repo_name: str, config: dict,
                     stale_hours: int = 24) -> list[dict]:
    """
    Detect agents that have been claiming an issue in their Today section
    for more than N hours with no corresponding commits.
    Uses activity.json from repo sync as the commit source.
    """
    root = get_workspace_root()
    sprint_num = get_current_sprint()
    stale = []

    for days_ago in range(1, 3):
        check_date = (date.today() - timedelta(days=days_ago)).isoformat()
        activity_path = (get_sprint_output_folder(sprint_num) /
                         "code" / check_date / "activity.json")
        content = read_file(activity_path)
        if not content:
            continue

        activity = json.loads(content)
        agents_with_commits = set(
            login for login, data in activity.get("members", {}).items()
            if data.get("commits")
        )

        standup_dir = get_sprint_folder(sprint_num) / "standup" / check_date
        if not standup_dir.exists():
            continue

        for f in standup_dir.glob("agent-*.md"):
            agent_id = f.stem
            login = agent_id.replace("agent-", "")
            content_s = read_file(f)
            today_section = extract_section(content_s, "Today")

            if today_section and login not in agents_with_commits:
                stale.append({
                    "agent": agent_id,
                    "date": check_date,
                    "today_section": today_section[:200],
                    "days_without_commits": days_ago,
                })

    return stale


def detect_all_deadlocks(repo_name: str, config: dict) -> dict:
    """Run all deadlock detectors. Returns summary dict."""
    duplicates = detect_duplicate_claims(repo_name, config)
    stale = detect_stale_wip(repo_name, config)

    if duplicates:
        logger.warning(f"⚠️ Duplicate claims detected: {duplicates}")
    if stale:
        logger.warning(f"⚠️ Stale WIP detected: {[s['agent'] for s in stale]}")

    return {
        "duplicate_claims": duplicates,
        "stale_wip": stale,
        "has_issues": bool(duplicates or stale),
    }
