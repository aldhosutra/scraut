"""
scrum/milestone/decompose.py
Read milestone.md, use LLM to decompose into structured breakdown.
Writes breakdown.json (machine-readable) and breakdown.md (human-readable).
Opens the interactive Planning Session GitHub Issue.
"""
import argparse
import json
import logging
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_scraut_root
from scraut.platform.utils.file_utils import atomic_write, read_file
from scraut.platform.llm.client import complete_json
from scraut.platform.llm.prompts import MILESTONE_DECOMPOSITION, SYSTEM_SCRUM_ASSISTANT
from scraut.platform.github.api import get_github_client, create_issue, post_comment
from scraut.scrum.sprint.calculate_velocity import calculate_rolling_velocity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PLANNING_SESSION_TEMPLATE = """<!-- scraut-planning-session milestone:{milestone_id} -->
## 🎯 Milestone Planning Session: {title}

I've analysed your milestone. Here's what I found:

**Decomposition:**
{epic_summary}

**Total estimate:** {sp_min}–{sp_max} story points
**Suggested duration:** {suggested_sprints} sprints

---

I need **{question_count} answers** before I can generate your roadmap.
Reply using `/answer Q[N] [value]` in comments below.

**Q1: Target duration?**
`/answer Q1 {suggested_sprints} sprints` — or — `/answer Q1 YYYY-MM-DD` (target date)

**Q2: Teams working on this milestone?**
✅ Auto-fetched from scraut.yml: {team_display}
`/answer Q2 confirm` — or — `/answer Q2 backend:team-alpha frontend:team-beta`

**Q3: Story point capacity per sprint?**
✅ Auto-fetched from velocity history: avg {avg_velocity} sp/sprint (last {sprints_sampled} sprints, σ={std_dev})
`/answer Q3 confirm` — or — `/answer Q3 [number]` (if you want to be conservative)

**Q4: Any hard internal deadlines within the milestone?**
(e.g., "SSO must be done before sprint 3 for a marketing demo")
`/answer Q4 none` — or — `/answer Q4 feature:sprint-N`

**Q5: Priority order if time runs short?**
(List epic IDs in priority order, separated by commas)
Epic IDs: {epic_ids}
`/answer Q5 {epic_ids_default}`

---
*This issue is managed by Scraut. Do not close manually.*
*Progress: 0/{question_count} questions answered*
"""


def milestone_id_from_path(milestone_path: Path) -> str:
    """Extract milestone ID from path like workspace/milestones/m01-auth/milestone.md."""
    return milestone_path.parent.name  # e.g., "m01-auth-system"


def generate_epic_summary(breakdown: dict) -> str:
    lines = []
    for epic in breakdown.get("epics", []):
        sp_range = epic.get("estimated_sp_range", [0, 0])
        lines.append(
            f"**{epic['id']}. {epic['title']}** — est. {sp_range[0]}–{sp_range[1]} sp"
        )
        if epic.get("description"):
            lines.append(f"   _{epic['description']}_")
    return "\n".join(lines)


def decompose_milestone(milestone_path: str, repo_name: str, config: dict) -> None:
    milestone_file = Path(milestone_path)
    milestone_dir = milestone_file.parent
    milestone_output_dir = get_scraut_root() / "milestones" / milestone_id_from_path(milestone_file)
    milestone_output_dir.mkdir(parents=True, exist_ok=True)
    milestone_content = read_file(milestone_file)

    if not milestone_content:
        logger.error(f"Milestone file not found or empty: {milestone_file}")
        return

    # Parse milestone sections
    from scraut.platform.utils.file_utils import extract_section
    goal = extract_section(milestone_content, "Goal")
    success_criteria = extract_section(milestone_content, "Success criteria")
    out_of_scope = extract_section(milestone_content, "Out of scope")
    known_risks = extract_section(milestone_content, "Known risks")
    title_line = [l for l in milestone_content.split("\n") if l.startswith("# ")]
    title = title_line[0].replace("# Milestone:", "").replace("# ", "").strip() if title_line else "Milestone"

    # Decompose with LLM
    logger.info(f"Decomposing milestone: {title}")
    prompt = MILESTONE_DECOMPOSITION.format(
        title=title,
        goal=goal,
        success_criteria=success_criteria,
        out_of_scope=out_of_scope or "None specified",
        known_risks=known_risks or "None specified",
    )
    breakdown = complete_json(prompt, system=SYSTEM_SCRUM_ASSISTANT)

    if not breakdown:
        logger.error("LLM decomposition failed")
        return

    # Write breakdown.json
    breakdown_json_path = milestone_output_dir / "breakdown.json"
    atomic_write(breakdown_json_path, json.dumps(breakdown, indent=2))

    # Write breakdown.md (human-readable)
    breakdown_md = generate_breakdown_md(title, breakdown)
    atomic_write(milestone_output_dir / "breakdown.md", breakdown_md)

    # Fetch velocity for auto-filling
    velocity = calculate_rolling_velocity(repo_name)
    sp_min = breakdown.get("total_sp_range", [0, 0])[0]
    sp_max = breakdown.get("total_sp_range", [0, 0])[1]
    suggested_sprints = breakdown.get("suggested_sprint_count", 4)
    epic_ids = ", ".join(e["id"] for e in breakdown.get("epics", []))
    team_display = ", ".join(m["display"] for m in config["team"]["members"])

    # Create planning session issue
    issue_body = PLANNING_SESSION_TEMPLATE.format(
        milestone_id=milestone_id_from_path(milestone_file),
        title=title,
        epic_summary=generate_epic_summary(breakdown),
        sp_min=sp_min,
        sp_max=sp_max,
        suggested_sprints=suggested_sprints,
        question_count=5,
        team_display=team_display,
        avg_velocity=velocity["avg"],
        sprints_sampled=velocity["sprints_sampled"],
        std_dev=velocity["std_dev"],
        epic_ids=epic_ids,
        epic_ids_default=epic_ids,
    )

    g = get_github_client()
    repo = g.get_repo(repo_name)
    issue = create_issue(
        repo,
        title=f"🎯 Milestone Planning: {title}",
        body=issue_body,
        labels=["sprint-planning"],
    )
    logger.info(f"Created planning session issue #{issue.number}")

    # Write the issue number to planning-session.md
    atomic_write(
        milestone_output_dir / "planning-session.md",
        f"# Planning Session: {title}\n\n"
        f"GitHub Issue: #{issue.number}\n"
        f"Status: awaiting answers\n"
        f"Answers received: 0/5\n\n"
        f"## Q&A Log\n\n"
    )


def generate_breakdown_md(title: str, breakdown: dict) -> str:
    lines = [
        f"<!-- BOT-GENERATED: do not edit manually -->\n",
        f"# Breakdown: {title}\n",
        f"**Total estimate:** {breakdown.get('total_sp_range', [0, 0])[0]}–"
        f"{breakdown.get('total_sp_range', [0, 0])[1]} story points\n",
        f"**Suggested sprints:** {breakdown.get('suggested_sprint_count', '?')}\n",
        f"**Confidence:** {breakdown.get('confidence', '?')}\n\n",
    ]
    for epic in breakdown.get("epics", []):
        sp_range = epic.get("estimated_sp_range", [0, 0])
        lines.append(f"## {epic['id']}: {epic['title']} ({sp_range[0]}–{sp_range[1]} sp)\n")
        lines.append(f"{epic.get('description', '')}\n\n")
        lines.append("| Story | Type | SP | Depends on |\n")
        lines.append("|-------|------|----|------------|\n")
        for story in epic.get("stories", []):
            deps = ", ".join(story.get("depends_on", [])) or "—"
            lines.append(
                f"| {story['title'][:60]} | {story.get('type', 'story')} "
                f"| {story.get('estimated_sp', '?')} | {deps} |\n"
            )
        lines.append("\n")
    return "".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--milestone", required=True, help="Path to milestone.md")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    decompose_milestone(args.milestone, args.repo, config)
