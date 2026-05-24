"""
lib/setup/init_project.py
Run after cloning: sets up labels, creates first sprint folder structure,
validates config, and prints a checklist of secrets to set.
"""
import argparse
import logging
import os
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_scraut_root
from scraut.platform.utils.file_utils import atomic_write, today_str

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REQUIRED_SECRETS = [
    "ANTHROPIC_API_KEY (or OPENAI_API_KEY)",
    "SLACK_WEBHOOK (for channel posts)",
    "SLACK_BOT_TOKEN (for personal DMs)",
    "SCRAUT_GITHUB_TOKEN (for repo sync)",
]

INITIAL_TEAM_CAPACITY = """# Team Capacity
<!-- Update this file when team members are OOO or have reduced availability -->
<!-- Format: name: description of availability -->

# Current sprint availability
<!-- Example: Alice: OOO May 27-29 -->
"""

INITIAL_FEEDBACK = """# Customer Feedback
<!-- Weekly digest from support/sales. Append new entries at the bottom. -->
<!-- Format: YYYY-MM-DD: [feedback item] -->
"""


def main(repo_name: str, config_path: str = None, dry_run: bool = False):
    config = load_config(config_path)
    root = get_workspace_root()
    scraut_root = get_scraut_root()

    logger.info("=== Scraut Initial Setup ===")

    # Create essential directories
    workspace_dirs = [
        "team",
        "okr",
        "customer",
        "knowledge",
        "milestones",
    ]
    scraut_dirs = [
        "suggestions/active",
        "suggestions/implemented",
        "suggestions/resolved",
        "insights",
    ]
    for d in workspace_dirs:
        if dry_run:
            logger.info(f"[DRY RUN] Would create directory: {d}")
        else:
            (root / d).mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Created directory: {d}")
    for d in scraut_dirs:
        if dry_run:
            logger.info(f"[DRY RUN] Would create directory: .scraut/{d}")
        else:
            (scraut_root / d).mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Created directory: .scraut/{d}")

    if not dry_run:
        # Create initial files
        team_cap = root / "team" / "capacity.md"
        if not team_cap.exists():
            atomic_write(team_cap, INITIAL_TEAM_CAPACITY)

        feedback = root / "customer" / "feedback.md"
        if not feedback.exists():
            atomic_write(feedback, INITIAL_FEEDBACK)

    # Print secrets checklist
    logger.info("\n=== Required GitHub Secrets ===")
    logger.info("Set these in: Settings → Secrets → Actions")
    for secret in REQUIRED_SECRETS:
        logger.info(f"  □ {secret}")

    logger.info("\n=== Next Steps ===")
    logger.info("1. Set all required secrets in GitHub")
    logger.info("2. Run: python apps/automation/scraut/platform/setup/create_labels.py --repo [org/repo]")
    logger.info("3. Create first sprint: python apps/automation/scraut/scrum/sprint/create_sprint.py --sprint 1 --repo [org/repo]")
    logger.info("4. Proceed to Phase 2: 02-CEREMONIES.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="org/repo format")
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(args.repo, args.config, args.dry_run)
