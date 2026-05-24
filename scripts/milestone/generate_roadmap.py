"""
scripts/milestone/generate_roadmap.py
Generate sprint-by-sprint roadmap from breakdown.json and constraints.
Creates roadmap.md and a draft PR for team approval.
"""
import argparse
import json
import logging
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import atomic_write, read_file
from scripts.llm.client import complete_json
from scripts.llm.prompts import ROADMAP_GENERATION, SYSTEM_SCRUM_ASSISTANT
from scripts.github.api import get_github_client, create_issue, post_comment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_roadmap(breakdown_path: str, milestone_dir: str, constraints: dict,
                     repo_name: str, config: dict, planning_issue=None) -> None:
    breakdown = json.loads(read_file(Path(breakdown_path)))
    milestone_dir = Path(milestone_dir)

    # Build roadmap via LLM
    prompt = ROADMAP_GENERATION.format(
        breakdown=json.dumps(breakdown, indent=2),
        total_sprints=constraints.get("duration", "6 sprints").split()[0],
        capacity_per_sprint=constraints.get("capacity_per_sprint", 26),
        priority_order=constraints.get("priority_order", ""),
        hard_deadlines=constraints.get("hard_deadlines", "none"),
        team_composition=json.dumps(constraints.get("team_composition", [])),
    )

    logger.info("Generating sprint roadmap...")
    roadmap_data = complete_json(prompt, system=SYSTEM_SCRUM_ASSISTANT)

    if not roadmap_data:
        logger.error("LLM roadmap generation failed")
        return

    # Write roadmap.md
    roadmap_md = format_roadmap_md(milestone_dir.name, roadmap_data, breakdown)
    atomic_write(milestone_dir / "roadmap.md", roadmap_md)

    # Initialise health/ directory
    health_dir = milestone_dir / "health"
    health_dir.mkdir(exist_ok=True)
    atomic_write(health_dir / "forecast.md", generate_initial_forecast(roadmap_data))

    logger.info(f"Roadmap written to {milestone_dir / 'roadmap.md'}")

    # Post roadmap summary to the planning issue
    if planning_issue:
        sprints = roadmap_data.get("sprints", [])
        confidence = roadmap_data.get("confidence_interval", {})
        summary = (
            f"## ✅ Roadmap Generated!\n\n"
            f"**{len(sprints)} sprints** planned · "
            f"**{roadmap_data.get('milestone_sp_total', '?')} total story points**\n\n"
            f"**Confidence:** P50={confidence.get('p50', '?')} sprints, "
            f"P90={confidence.get('p90', '?')} sprints\n\n"
            f"**Next step:** Review `{milestone_dir.name}/roadmap.md` and create"
            f" GitHub Issues for each story. Then run:\n"
            f"`python scripts/milestone/create_sprint_issues.py "
            f"--milestone {milestone_dir.name} --repo {repo_name}`\n\n"
            f"{roadmap_data.get('risk_assessment', '')}"
        )
        post_comment(planning_issue, summary)


def format_roadmap_md(milestone_id: str, roadmap: dict, breakdown: dict) -> str:
    milestone_title = milestone_id.replace("-", " ").title()
    confidence = roadmap.get("confidence_interval", {})
    lines = [
        f"<!-- BOT-GENERATED: last updated by Scraut -->\n",
        f"# Roadmap: {milestone_title}\n",
        f"**Total:** {roadmap.get('milestone_sp_total', '?')} story points\n",
        f"**Confidence:** P50={confidence.get('p50', '?')} sprints, "
        f"P90={confidence.get('p90', '?')} sprints\n\n",
        f"---\n\n",
    ]
    for sprint in roadmap.get("sprints", []):
        lines.append(
            f"## Sprint {sprint['sprint_number']} — {sprint.get('theme', '')} "
            f"({sprint['total_sp']} sp + {sprint.get('buffer_sp', 0)} sp buffer)\n"
        )
        lines.append("| Story | Epic | SP | Assignee type |\n")
        lines.append("|-------|------|----|---------------|\n")
        for story in sprint.get("stories", []):
            lines.append(
                f"| {story['title'][:60]} | {story.get('epic', '?')} "
                f"| {story.get('sp', '?')} | {story.get('assignee_type', 'any')} |\n"
            )
        if sprint.get("notes"):
            lines.append(f"\n_{sprint['notes']}_\n")
        lines.append("\n")

    lines.append(f"## Risk Assessment\n\n{roadmap.get('risk_assessment', 'No risks identified.')}\n")
    return "".join(lines)


def generate_initial_forecast(roadmap: dict) -> str:
    confidence = roadmap.get("confidence_interval", {})
    return (
        f"<!-- BOT-GENERATED: updated after each sprint -->\n"
        f"# Milestone Forecast\n\n"
        f"**Status:** Not started\n"
        f"**Sprint:** 0 of {len(roadmap.get('sprints', []))} planned\n"
        f"**Points delivered:** 0 of {roadmap.get('milestone_sp_total', '?')}\n"
        f"**ETA:** P50={confidence.get('p50', '?')} sprints, P90={confidence.get('p90', '?')} sprints\n"
        f"**Confidence:** Initial estimate\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--breakdown", required=True, help="Path to breakdown.json")
    parser.add_argument("--milestone-dir", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    constraints = {"capacity_per_sprint": 26}  # fallback defaults
    generate_roadmap(args.breakdown, args.milestone_dir, constraints, args.repo, config)
