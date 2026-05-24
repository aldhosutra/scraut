"""
scripts/sprint/synthesise_retrospective.py
Synthesise individual retrospective entries into a team summary using LLM.
Writes to sprint-N/retrospective/summary.md (bot-generated).
"""
import argparse
import logging
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import atomic_write, read_file
from scripts.llm.client import complete
from scripts.llm.prompts import RETROSPECTIVE_SYNTHESIS, SYSTEM_SCRUM_ASSISTANT
from scripts.sprint.calculate_velocity import calculate_sprint_velocity
from scripts.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def synthesise_retrospective(sprint_num: int, repo_name: str, config: dict,
                              dry_run: bool = False) -> str:
    root = get_repo_root()
    retro_dir = root / f"sprint-{sprint_num:02d}" / "retrospective"

    retro_files = list(retro_dir.glob("*.md"))
    retro_files = [f for f in retro_files if f.name != "summary.md"]

    if not retro_files:
        logger.warning(f"No retrospective files found in {retro_dir}")
        return ""

    retro_contents = "\n\n---\n\n".join(
        f"### {f.stem}\n{read_file(f)}" for f in retro_files
    )

    velocity = calculate_sprint_velocity(sprint_num, repo_name)

    prompt = RETROSPECTIVE_SYNTHESIS.format(
        sprint_num=sprint_num,
        sprint_goal="(see sprint meta)",
        velocity=velocity["completed_sp"],
        planned_sp=velocity["planned_sp"],
        retro_contents=retro_contents,
    )

    logger.info(f"Synthesising retrospective for sprint {sprint_num}...")
    summary = complete(prompt, system=SYSTEM_SCRUM_ASSISTANT)

    if not summary:
        summary = f"# Sprint {sprint_num} Retrospective Summary\n\n*LLM unavailable.*\n"

    if not dry_run:
        retro_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(retro_dir / "summary.md",
                     f"<!-- BOT-GENERATED: do not edit manually -->\n\n{summary}")
        logger.info(f"Retrospective summary written to sprint-{sprint_num:02d}/retrospective/summary.md")

        slack_webhook = config.get("notifications", {}).get("slack_webhook")
        if slack_webhook:
            post_to_slack(webhook_url=slack_webhook,
                          text=f"*Sprint {sprint_num} Retrospective Summary*\n\n{summary[:2000]}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    synthesise_retrospective(args.sprint, args.repo, config, args.dry_run)
