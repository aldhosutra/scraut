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
