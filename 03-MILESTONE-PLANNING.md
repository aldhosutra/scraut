# Phase 3: Milestone Planning
*Scraut Implementation — requires Phases 1 and 2 complete*

## Goal
Build the complete milestone planning system: a human writes `milestone.md`,
Scraut decomposes it with LLM, runs an interactive GitHub Issue Q&A to collect
constraints (auto-fetching what it already knows), generates a sprint-by-sprint
roadmap, and runs a post-sprint health check that re-forecasts the ETA.

---

## How Milestone Planning Works (end-to-end)

```
Human commits milestones/m01-name/milestone.md
  ↓
milestone-planning.yml triggers
  ↓
scripts/milestone/decompose.py
  → LLM breaks milestone into epics/stories/tasks with SP estimates
  → writes breakdown.json + breakdown.md
  → opens "Planning Session" GitHub Issue with structured Q&A
  ↓
Team answers in Issue comments using /answer Q1 [value]
milestone-respond.yml triggers on each comment
  ↓
scripts/milestone/planning_session.py
  → parses /answer commands
  → auto-fetches velocity from insights/velocity-trends.md
  → auto-fetches team from scraut.yml
  → once all answers collected → triggers roadmap generation
  ↓
scripts/milestone/generate_roadmap.py
  → LLM generates sprint-by-sprint plan respecting constraints
  → writes roadmap.md + constraints.md
  → opens draft PR for team to review and approve
  ↓
Team merges the PR (= team commitment to the plan)
  ↓
After each sprint: suggestion-detect.yml triggers health_check.py
  → compares planned vs actual
  → updates forecast.md
  → alerts if at risk
```

---

## 1. `scripts/milestone/decompose.py`

```python
"""
scripts/milestone/decompose.py
Read milestone.md, use LLM to decompose into structured breakdown.
Writes breakdown.json (machine-readable) and breakdown.md (human-readable).
Opens the interactive Planning Session GitHub Issue.
"""
import argparse
import json
import logging
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import atomic_write, read_file
from scripts.llm.client import complete_json
from scripts.llm.prompts import MILESTONE_DECOMPOSITION, SYSTEM_SCRUM_ASSISTANT
from scripts.github.api import get_github_client, create_issue, post_comment
from scripts.sprint.calculate_velocity import calculate_rolling_velocity

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
    """Extract milestone ID from path like milestones/m01-auth/milestone.md."""
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
    milestone_content = read_file(milestone_file)

    if not milestone_content:
        logger.error(f"Milestone file not found or empty: {milestone_file}")
        return

    # Parse milestone sections
    from scripts.utils.file_utils import extract_section
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
    breakdown_json_path = milestone_dir / "breakdown.json"
    atomic_write(breakdown_json_path, json.dumps(breakdown, indent=2))

    # Write breakdown.md (human-readable)
    breakdown_md = generate_breakdown_md(title, breakdown)
    atomic_write(milestone_dir / "breakdown.md", breakdown_md)

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
        milestone_dir / "planning-session.md",
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
```

---

## 2. `scripts/milestone/planning_session.py`

Parses `/answer Q[N] [value]` commands from issue comments.

```python
"""
scripts/milestone/planning_session.py
Parse /answer commands from GitHub Issue comments.
Accumulates answers in planning-session.md.
When all 5 answers are collected, triggers roadmap generation.
"""
import argparse
import json
import logging
import re
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import read_file, atomic_write
from scripts.github.api import get_github_client, post_comment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANSWER_PATTERN = re.compile(r"/answer\s+Q(\d)\s+(.+)", re.IGNORECASE)
TOTAL_QUESTIONS = 5


def parse_answers_from_comment(comment_body: str) -> dict[int, str]:
    """Extract /answer Q[N] [value] commands from a comment."""
    answers = {}
    for match in ANSWER_PATTERN.finditer(comment_body):
        q_num = int(match.group(1))
        value = match.group(2).strip()
        answers[q_num] = value
    return answers


def find_milestone_dir(issue_body: str, repo_root: Path) -> Path | None:
    """Extract milestone ID from planning session issue body."""
    match = re.search(r"milestone:(\S+)", issue_body)
    if match:
        milestone_id = match.group(1)
        candidate = repo_root / "milestones" / milestone_id
        if candidate.exists():
            return candidate
    return None


def load_existing_answers(planning_session_path: Path) -> dict[int, str]:
    """Load already-answered questions from planning-session.md."""
    content = read_file(planning_session_path)
    answers = {}
    for match in re.finditer(r"Q(\d):\s*(.+)", content):
        answers[int(match.group(1))] = match.group(2).strip()
    return answers


def process_comment(issue_number: int, comment_body: str,
                    repo_name: str, config: dict) -> None:
    g = get_github_client()
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    root = get_repo_root()

    # Find the milestone directory from the issue body
    milestone_dir = find_milestone_dir(issue.body, root)
    if not milestone_dir:
        logger.warning("Could not find milestone directory from issue body")
        return

    planning_path = milestone_dir / "planning-session.md"

    # Parse new answers from this comment
    new_answers = parse_answers_from_comment(comment_body)
    if not new_answers:
        return  # Not an answer comment

    # Load existing answers and merge
    existing_answers = load_existing_answers(planning_path)
    all_answers = {**existing_answers, **new_answers}

    # Update planning-session.md
    answers_section = "\n".join(
        f"Q{q}: {v}" for q, v in sorted(all_answers.items())
    )
    content = read_file(planning_path)
    # Replace Q&A Log section
    q_section_start = content.find("## Q&A Log")
    if q_section_start >= 0:
        content = content[:q_section_start] + f"## Q&A Log\n\n{answers_section}\n"
    atomic_write(planning_path, content)

    answered_count = len(all_answers)
    remaining = TOTAL_QUESTIONS - answered_count

    # Acknowledge receipt
    ack_msg = (
        f"✅ Recorded {len(new_answers)} answer(s). "
        f"Progress: **{answered_count}/{TOTAL_QUESTIONS}** questions answered."
    )
    if remaining > 0:
        ack_msg += f" {remaining} more needed before I generate the roadmap."
    post_comment(issue, ack_msg)

    # If all answered, trigger roadmap generation
    if answered_count >= TOTAL_QUESTIONS:
        logger.info("All questions answered. Generating roadmap...")
        constraints = build_constraints(all_answers, config)
        atomic_write(milestone_dir / "constraints.md", format_constraints(constraints))

        # Import and run roadmap generation
        from scripts.milestone.generate_roadmap import generate_roadmap
        breakdown_path = milestone_dir / "breakdown.json"
        generate_roadmap(
            breakdown_path=str(breakdown_path),
            milestone_dir=str(milestone_dir),
            constraints=constraints,
            repo_name=repo_name,
            config=config,
            planning_issue=issue,
        )


def build_constraints(answers: dict[int, str], config: dict) -> dict:
    """Convert raw Q&A answers to a structured constraints dict."""
    from scripts.sprint.calculate_velocity import calculate_rolling_velocity
    velocity = calculate_rolling_velocity(config.get("_repo_name", ""))

    constraints = {
        "duration": answers.get(1, f"{velocity['avg'] * 4:.0f} days"),
        "teams": answers.get(2, "confirm"),
        "capacity_per_sprint": (
            velocity["avg"] if answers.get(3, "confirm").lower() == "confirm"
            else int(answers.get(3, velocity["avg"]))
        ),
        "hard_deadlines": answers.get(4, "none"),
        "priority_order": answers.get(5, ""),
        "team_composition": config["team"]["members"],
    }
    return constraints


def format_constraints(constraints: dict) -> str:
    return (
        "<!-- BOT-GENERATED -->\n"
        "# Milestone Constraints\n\n"
        f"- **Duration:** {constraints['duration']}\n"
        f"- **Teams:** {constraints['teams']}\n"
        f"- **Capacity per sprint:** {constraints['capacity_per_sprint']} sp\n"
        f"- **Hard deadlines:** {constraints['hard_deadlines']}\n"
        f"- **Priority order:** {constraints['priority_order']}\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--comment-body", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    config["_repo_name"] = args.repo
    process_comment(args.issue, args.comment_body, args.repo, config)
```

---

## 3. `scripts/milestone/generate_roadmap.py`

```python
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
```

---

## 4. `scripts/milestone/health_check.py`

Sprint health scoring and milestone forecast update.

```python
"""
scripts/milestone/health_check.py
After each sprint: compare planned roadmap vs actual delivery.
Calculate 4-dimension health score. Update forecast.md. Alert if at risk.
"""
import argparse
import json
import logging
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import atomic_write, read_file
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue
from scripts.sprint.calculate_velocity import calculate_rolling_velocity
from scripts.llm.client import complete
from scripts.llm.prompts import HEALTH_REPORT_NARRATIVE, SYSTEM_SCRUM_ASSISTANT
from scripts.notifications.slack_post import post_to_slack

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
    sprint_label = f"sprint-{sprint_num:02d}"
    all_sprint_issues = get_issues(repo, labels=[sprint_label], state="all")
    closed = [i for i in all_sprint_issues if i.state == "closed"]
    planned_sp = sum(get_sp_from_issue(i) for i in all_sprint_issues)
    actual_sp = sum(get_sp_from_issue(i) for i in closed)

    # Calculate total delivered across all sprints
    milestone_label = milestone_path.name  # e.g., m01-auth-system
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
    atomic_write(health_dir / f"sprint-{sprint_num:02d}.md", health_report)

    # Update rolling forecast
    sprints_remaining = total_planned_sprints - sprint_num
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
                f"View: `{milestone_path}/health/sprint-{sprint_num:02d}.md`"
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
```

---

## 5. GitHub Actions Workflows

### `.github/workflows/milestone-planning.yml`

```yaml
name: Scraut — Milestone Planning
on:
  push:
    paths:
      - 'milestones/*/milestone.md'

jobs:
  decompose-milestone:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Detect changed milestone file
        id: detect
        run: |
          CHANGED=$(git diff --name-only HEAD~1 HEAD | grep 'milestones/.*/milestone.md' | head -1)
          echo "milestone_file=$CHANGED" >> $GITHUB_OUTPUT

      - name: Decompose milestone
        if: steps.detect.outputs.milestone_file != ''
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python scripts/milestone/decompose.py \
            --milestone ${{ steps.detect.outputs.milestone_file }} \
            --repo ${{ github.repository }}

      - name: Commit breakdown files
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add milestones/
          git diff --staged --quiet || git commit -m "chore: milestone breakdown [skip ci]"
          git push
```

---

### `.github/workflows/milestone-respond.yml`

```yaml
name: Scraut — Milestone Planning Response
on:
  issue_comment:
    types: [created]

jobs:
  process-answer:
    # Only process comments on planning session issues
    if: contains(github.event.comment.body, '/answer')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Process planning answer
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          python scripts/milestone/planning_session.py \
            --issue ${{ github.event.issue.number }} \
            --comment-body "${{ github.event.comment.body }}" \
            --repo ${{ github.repository }}

      - name: Commit updated planning session
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add milestones/
          git diff --staged --quiet || git commit -m "chore: planning session update [skip ci]"
          git push
```

---

## Done Criteria for Phase 3

- [ ] `scripts/milestone/decompose.py` — reads `milestone.md`, calls LLM, writes `breakdown.json` + `breakdown.md`
- [ ] `scripts/milestone/decompose.py` — creates GitHub Issue with correct Q&A template including auto-fetched velocity
- [ ] `scripts/milestone/planning_session.py` — parses `/answer Q1 value` from comment body correctly
- [ ] `scripts/milestone/planning_session.py` — loads existing answers and merges (idempotent)
- [ ] `scripts/milestone/planning_session.py` — triggers roadmap generation when all 5 answers received
- [ ] `scripts/milestone/generate_roadmap.py` — generates `roadmap.md` with sprint-by-sprint plan respecting capacity
- [ ] `scripts/milestone/generate_roadmap.py` — writes initial `health/forecast.md`
- [ ] `scripts/milestone/health_check.py` — calculates 4-dimension score correctly
- [ ] `scripts/milestone/health_check.py` — updates `forecast.md` with new ETA after each sprint
- [ ] `scripts/milestone/health_check.py` — posts Slack alert when status = "at-risk"
- [ ] `milestone-planning.yml` — triggers on push to `milestones/*/milestone.md`
- [ ] `milestone-respond.yml` — triggers on comments containing `/answer`
- [ ] End-to-end test: write a test `milestone.md`, push it, verify planning session Issue is created with correct Q&A template and auto-fetched data

*Proceed to `04-REPO-SYNC.md`*
