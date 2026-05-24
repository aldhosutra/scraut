"""
scrum/repo_sync/compute_delta.py
Compare today's activity vs yesterday's to produce a delta summary.
Detects: new PRs, merged PRs, newly aging PRs, CI changes, WIP changes.
"""
import argparse
import json
import logging
from datetime import date, timedelta
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_current_sprint, get_sprint_folder, get_sprint_output_folder
from scraut.platform.utils.file_utils import atomic_write, read_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_activity(target_date: str, config: dict) -> dict:
    root = get_workspace_root()
    sprint_num = get_current_sprint()
    path = get_sprint_output_folder(sprint_num) / "code" / target_date / "activity.json"
    content = read_file(path)
    return json.loads(content) if content else {}


def compute_delta(today: str, config: dict) -> dict:
    yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()

    today_data = load_activity(today, config)
    yesterday_data = load_activity(yesterday, config)

    if not today_data:
        logger.warning("No activity data for today. Delta unavailable.")
        return {}

    # PRs: compare aging lists
    today_aging = {p["number"]: p for p in today_data.get("team_summary", {}).get("aging_prs", [])}
    yest_aging = {p["number"]: p for p in yesterday_data.get("team_summary", {}).get("aging_prs", [])}

    newly_aging = [p for num, p in today_aging.items() if num not in yest_aging]
    resolved_aging = [p for num, p in yest_aging.items() if num not in today_aging]

    # PRs: new merges today
    new_merges = []
    for login, data in today_data.get("members", {}).items():
        new_merges.extend(data.get("prs_merged", []))

    # WIP change: count open branches (use commits to distinct branches as proxy)
    today_branches = set()
    yest_branches = set()
    for data in today_data.get("members", {}).values():
        today_branches.update(c.get("branch", "") for c in data.get("commits", []))
    for data in yesterday_data.get("members", {}).values():
        yest_branches.update(c.get("branch", "") for c in data.get("commits", []))

    wip_opened = today_branches - yest_branches
    wip_closed = yest_branches - today_branches

    return {
        "date": today,
        "compared_to": yesterday,
        "new_merges": new_merges,
        "newly_aging_prs": newly_aging,
        "resolved_aging_prs": resolved_aging,
        "wip_branches_opened": list(wip_opened - {"unknown"}),
        "wip_branches_closed": list(wip_closed - {"unknown"}),
        "total_commits_today": today_data.get("team_summary", {}).get("total_commits", 0),
    }


def write_delta(delta: dict, config: dict) -> None:
    if not delta:
        return
    root = get_workspace_root()
    sprint_num = get_current_sprint()
    code_dir = get_sprint_output_folder(sprint_num) / "code" / delta["date"]
    code_dir.mkdir(parents=True, exist_ok=True)

    md = generate_delta_md(delta)
    atomic_write(code_dir / "delta.md", md)
    logger.info(f"Delta written: {code_dir}/delta.md")


def generate_delta_md(delta: dict) -> str:
    lines = [
        f"<!-- BOT-GENERATED -->\n",
        f"# Code Delta: {delta['date']} vs {delta['compared_to']}\n\n",
    ]

    if delta.get("new_merges"):
        lines.append("## ✅ New merges today\n")
        for pr in delta["new_merges"]:
            lines.append(f"- PR #{pr['number']}: \"{pr['title']}\"\n")
        lines.append("\n")

    if delta.get("newly_aging_prs"):
        lines.append("## ⚠️ PRs now overdue (needs review)\n")
        for pr in delta["newly_aging_prs"]:
            lines.append(f"- PR #{pr['number']}: \"{pr['title']}\" — {pr['age_days']} days old\n")
        lines.append("\n")

    if delta.get("resolved_aging_prs"):
        lines.append("## ✅ Previously overdue PRs resolved\n")
        for pr in delta["resolved_aging_prs"]:
            lines.append(f"- PR #{pr['number']}: \"{pr['title']}\"\n")
        lines.append("\n")

    if delta.get("wip_branches_opened"):
        lines.append("## 🔀 New work started (branches opened)\n")
        for branch in delta["wip_branches_opened"]:
            lines.append(f"- `{branch}`\n")
        lines.append("\n")

    lines.append(
        f"**Today:** {delta.get('total_commits_today', 0)} commits, "
        f"{len(delta.get('new_merges', []))} PRs merged\n"
    )
    return "".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    delta = compute_delta(args.date, config)
    write_delta(delta, config)
