"""
scrum/sprint/synthesise_retrospective.py
Read all individual retrospective files, synthesise with LLM,
write sprint/NN/retrospective/summary.md (bot-generated).
Also check if previous retro action items were followed up.
"""
import argparse
import logging
from datetime import date
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_sprint_folder, get_sprint_output_folder
from scraut.platform.utils.file_utils import atomic_write, read_file, extract_section
from scraut.platform.llm.client import complete
from scraut.platform.llm.prompts import RETROSPECTIVE_SYNTHESIS, SYSTEM_SCRUM_ASSISTANT
from scraut.scrum.sprint.calculate_velocity import calculate_sprint_velocity
from scraut.platform.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_previous_retro_followthrough(sprint_num: int, config: dict) -> str:
    """Check if previous sprint's retro action items were addressed."""
    root = get_workspace_root()
    if sprint_num <= 1:
        return ""

    prev_summary = read_file(get_sprint_output_folder(sprint_num - 1) / "retrospective" / "summary.md")
    if not prev_summary:
        return ""

    prev_actions = extract_section(prev_summary, "Action items")
    if not prev_actions:
        return ""

    current_meta = read_file(get_sprint_folder(sprint_num) / "meta.md") or ""
    action_items = [line.strip().lstrip("- ").strip()
                    for line in prev_actions.split("\n")
                    if line.strip().startswith("-")]

    not_addressed = []
    for action in action_items:
        if len(action) < 10:
            continue
        keywords = set(action.lower().split())
        keywords.discard("the")
        keywords.discard("a")
        if not any(kw in current_meta.lower() for kw in list(keywords)[:3]):
            not_addressed.append(action)

    if not_addressed:
        return (
            "\n\n## ⚠️ Unresolved action items from Sprint {}\n".format(sprint_num - 1)
            + "\n".join(f"- {a}" for a in not_addressed)
            + "\n\n*These items were not tracked in this sprint's planning. "
              "Consider adding them to the next sprint backlog.*\n"
        )
    return ""


def synthesise_retrospective(sprint_num: int, repo_name: str, config: dict) -> None:
    root = get_workspace_root()
    retro_dir = get_sprint_folder(sprint_num) / "retrospective"

    if not retro_dir.exists():
        logger.warning(f"No retrospective directory for sprint {sprint_num}")
        return

    member_retros = {}
    members_map = {m["login"]: m["display"] for m in config["team"]["members"]}
    for login, display in members_map.items():
        f = retro_dir / f"{login}.md"
        content = read_file(f)
        if content:
            member_retros[display] = content

    if not member_retros:
        logger.warning("No retrospective entries found.")
        return

    retro_contents = "\n\n---\n\n".join(
        f"### {name}\n{content}" for name, content in member_retros.items()
    )

    velocity = calculate_sprint_velocity(sprint_num, repo_name)
    meta = read_file(get_sprint_folder(sprint_num) / "meta.md") or ""
    sprint_goal = extract_section(meta, "Goal") or "Not specified"

    summary = complete(
        RETROSPECTIVE_SYNTHESIS.format(
            sprint_num=sprint_num,
            sprint_goal=sprint_goal,
            velocity=velocity["completed_sp"],
            planned_sp=velocity["planned_sp"],
            retro_contents=retro_contents,
        ),
        system=SYSTEM_SCRUM_ASSISTANT,
    )

    followthrough_note = check_previous_retro_followthrough(sprint_num, config)

    full_summary = (
        f"<!-- BOT-GENERATED -->\n"
        f"# Retrospective Summary — Sprint {sprint_num:02d}\n"
        f"*Generated: {date.today().isoformat()}*\n"
        f"*{len(member_retros)} of {len(members_map)} team members responded*\n\n"
        + (summary or "LLM synthesis unavailable. See individual entries.")
        + followthrough_note
    )

    output_dir = get_sprint_output_folder(sprint_num) / "retrospective"
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(output_dir / "summary.md", full_summary)

    webhook = config.get("notifications", {}).get("slack_webhook")
    if webhook:
        post_to_slack(webhook,
            f"🔄 *Sprint {sprint_num:02d} Retrospective complete*\n"
            f"{len(member_retros)} responses synthesised. "
            f"See `.scraut/sprint/{sprint_num:02d}/retrospective/summary.md`"
        )

    logger.info(f"Retrospective synthesised for sprint {sprint_num}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    synthesise_retrospective(args.sprint, args.repo, config)
