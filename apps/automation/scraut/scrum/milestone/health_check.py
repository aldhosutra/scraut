"""
scrum/milestone/health_check.py
After each sprint: compare planned roadmap vs actual delivery.
Calculate 4-dimension health score. Update forecast.md. Alert if at risk.
"""
import argparse
import json
import logging
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_scraut_root, format_sprint_num, get_folder_padding
from scraut.platform.utils.file_utils import atomic_write, read_file
from scraut.platform.github.api import get_github_client, get_issues, get_sp_from_issue
from scraut.scrum.sprint.calculate_velocity import calculate_rolling_velocity
from scraut.platform.llm.client import complete
from scraut.platform.llm.prompts import HEALTH_REPORT_NARRATIVE, SYSTEM_SCRUM_ASSISTANT
from scraut.platform.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def score_sprint(planned_sp: int, actual_sp: int,
                 planned_issues: list, completed_issues: list,
                 milestone_total_sp: int, milestone_delivered_sp: int,
                 sprint_num: int, total_planned_sprints: int,
                 unplanned_stories: int) -> dict:
    """
    Calculate 4-dimension sprint health score (0–100 each).
    Composite = velocity*0.3 + delivery*0.3 + milestone*0.3 + focus*0.1
    """
    # 1. Velocity score: actual vs planned SP
    velocity = min(actual_sp / planned_sp, 1.0) * 100 if planned_sp else 0

    # 2. Delivery score: correct stories closed (planned issues that were closed)
    planned_set = set(planned_issues)
    completed_set = set(completed_issues)
    delivery = (len(planned_set & completed_set) / len(planned_set) * 100
                if planned_set else 0)

    # 3. Milestone score: on pace for deadline?
    expected_progress = sprint_num / total_planned_sprints
    actual_progress = milestone_delivered_sp / milestone_total_sp if milestone_total_sp else 0
    milestone = min(actual_progress / expected_progress, 1.0) * 100 if expected_progress else 0

    # 4. Focus score: unplanned work discipline
    focus = max(0, 100 - (unplanned_stories / max(len(planned_issues), 1)) * 100)

    composite = (velocity * 0.30 + delivery * 0.30 + milestone * 0.30 + focus * 0.10)

    return {
        "velocity": round(velocity),
        "delivery": round(delivery),
        "milestone": round(milestone),
        "focus": round(focus),
        "composite": round(composite),
        "status": (
            "on-track" if composite >= 80
            else "watch" if composite >= 65
            else "at-risk"
        ),
    }


def update_milestone_health(milestone_dir: str, sprint_num: int,
                             repo_name: str, config: dict) -> None:
    milestone_path = Path(milestone_dir)
    roadmap_content = read_file(milestone_path / "roadmap.md")
    breakdown_content = read_file(milestone_path / "breakdown.json")

    if not breakdown_content:
        logger.warning("breakdown.json not found. Skipping health check.")
        return

    breakdown = json.loads(breakdown_content)
    milestone_total_sp = breakdown.get("total_sp_range", [0, 100])[1]

    # Get sprint delivery data from GitHub
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_label = f"sprint-{format_sprint_num(sprint_num, get_folder_padding())}"
    all_sprint_issues = get_issues(repo, labels=[sprint_label], state="all")
    closed = [i for i in all_sprint_issues if i.state == "closed"]
    planned_sp = sum(get_sp_from_issue(i) for i in all_sprint_issues)
    actual_sp = sum(get_sp_from_issue(i) for i in closed)

    # Calculate total delivered across all sprints
    all_milestone_issues = get_issues(repo, state="closed")
    # Filter by milestone issues (those linked to the milestone roadmap)
    milestone_delivered_sp = sum(
        get_sp_from_issue(i) for i in all_milestone_issues
        if any(l.name == sprint_label for l in i.labels)  # simplified
    )

    # Determine planned vs unplanned stories
    planned_issues = [i.number for i in all_sprint_issues]
    completed_issues = [i.number for i in closed]

    # Count unplanned (closed but not in original sprint plan)
    # Simplified: assume all in-sprint label were planned
    unplanned = 0

    total_planned_sprints = len(
        [line for line in roadmap_content.split("\n") if line.startswith("## Sprint")]
    )

    score = score_sprint(
        planned_sp=planned_sp,
        actual_sp=actual_sp,
        planned_issues=planned_issues,
        completed_issues=completed_issues,
        milestone_total_sp=milestone_total_sp,
        milestone_delivered_sp=milestone_delivered_sp,
        sprint_num=sprint_num,
        total_planned_sprints=total_planned_sprints,
        unplanned_stories=unplanned,
    )

    # Generate narrative
    velocity = calculate_rolling_velocity(repo_name)
    narrative = complete(
        HEALTH_REPORT_NARRATIVE.format(
            sprint_num=sprint_num,
            total_sprints=total_planned_sprints,
            milestone_title=milestone_path.name,
            sprint_delivered_sp=actual_sp,
            total_delivered_sp=milestone_delivered_sp,
            total_sp=milestone_total_sp,
            percent_done=round(milestone_delivered_sp / milestone_total_sp * 100)
            if milestone_total_sp else 0,
            expected_percent=round(sprint_num / total_planned_sprints * 100),
            board_state=f"Closed: {len(closed)}, Open: {len(all_sprint_issues)-len(closed)}",
            blockers="See standup files",
            agent_velocities="N/A",
        ),
        system=SYSTEM_SCRUM_ASSISTANT,
    )

    # Write health report for this sprint
    health_dir = milestone_path / "health"
    health_dir.mkdir(exist_ok=True)
    health_report = (
        f"<!-- BOT-GENERATED -->\n"
        f"# Milestone Health: Sprint {sprint_num}\n\n"
        f"## Scores\n"
        f"| Dimension | Score |\n"
        f"|-----------|-------|\n"
        f"| Velocity | {score['velocity']} |\n"
        f"| Delivery | {score['delivery']} |\n"
        f"| Milestone | {score['milestone']} |\n"
        f"| Focus | {score['focus']} |\n"
        f"| **Composite** | **{score['composite']}** — {score['status'].upper()} |\n\n"
        f"## Narrative\n\n{narrative}\n\n"
        f"## Raw Data\n```json\n{json.dumps(score, indent=2)}\n```\n"
    )
    atomic_write(health_dir / f"sprint-{format_sprint_num(sprint_num, get_folder_padding())}.md", health_report)

    # Update rolling forecast
    if actual_sp > 0 and milestone_total_sp > 0:
        remaining_sp = milestone_total_sp - milestone_delivered_sp
        avg_vel = velocity["avg"] or actual_sp
        new_eta = sprint_num + (remaining_sp / avg_vel)
    else:
        new_eta = total_planned_sprints

    forecast = (
        f"<!-- BOT-GENERATED: updated sprint {sprint_num} -->\n"
        f"# Milestone Forecast\n\n"
        f"**Status:** {score['status'].upper()}\n"
        f"**Sprint:** {sprint_num} of {total_planned_sprints} planned\n"
        f"**Points delivered:** {milestone_delivered_sp} of {milestone_total_sp} "
        f"({round(milestone_delivered_sp/milestone_total_sp*100) if milestone_total_sp else 0}%)\n"
        f"**Updated ETA:** {new_eta:.1f} sprints\n"
        f"**Composite health:** {score['composite']}/100\n"
    )
    atomic_write(health_dir / "forecast.md", forecast)

    # Alert if at risk
    if score["status"] == "at-risk":
        webhook = config.get("notifications", {}).get("slack_webhook")
        if webhook:
            post_to_slack(
                webhook,
                f"🔴 *Milestone at risk!* `{milestone_path.name}` — "
                f"Sprint {sprint_num} composite score: {score['composite']}/100\n"
                f"View: `{milestone_path}/health/sprint-{format_sprint_num(sprint_num, get_folder_padding())}.md`"
            )

    logger.info(f"Health check complete. Status: {score['status']} ({score['composite']}/100)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--milestone-dir", required=True)
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    update_milestone_health(args.milestone_dir, args.sprint, args.repo, config)
