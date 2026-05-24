"""
lib/setup/create_labels.py
Create all Scraut labels in the repository.
Run once during initial setup.
"""
import argparse
import logging
from scraut.platform.github.api import get_github_client, ensure_label_exists
from scraut.platform.utils.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LABELS = [
    # Story points
    ("sp:1",  "0075ca", "1 story point"),
    ("sp:2",  "0075ca", "2 story points"),
    ("sp:3",  "0075ca", "3 story points"),
    ("sp:5",  "0075ca", "5 story points"),
    ("sp:8",  "0075ca", "8 story points"),
    ("sp:13", "0075ca", "13 story points"),
    # Type
    ("story",  "bfd4f2", "User story"),
    ("bug",    "d73a4a", "Something isn't working"),
    ("task",   "e4e669", "Technical task"),
    ("spike",  "fbca04", "Research/investigation"),
    ("chore",  "fef2c0", "Maintenance"),
    # Status
    ("in-sprint",      "0052cc", "In current sprint"),
    ("in-review",      "5319e7", "Under review"),
    ("blocked",        "b60205", "Blocked by dependency"),
    ("escalate:human", "e11d48", "Needs human intervention"),
    # Priority
    ("p:high",   "b60205", "High priority"),
    ("p:medium", "e4e669", "Medium priority"),
    ("p:low",    "0e8a16", "Low priority"),
    # Ceremony
    ("standup",         "c5def5", "Daily standup"),
    ("retrospective",   "bfd4f2", "Sprint retrospective"),
    ("sprint-review",   "d4c5f9", "Sprint review"),
    ("sprint-planning", "f9d0c4", "Sprint planning"),
    # Agent
    ("agent-assigned", "f9ca24", "Assigned to AI agent"),
    ("agent-blocked",  "f0932b", "Agent is blocked"),
    # DoD
    ("dod:pending",  "ffeaa7", "Definition of Done check pending"),
    ("dod:approved", "00b894", "Definition of Done approved"),
    # Milestone-related
    ("milestone-risk", "d63031", "Milestone at risk"),
]


def main(repo_name: str, config_path: str = None, dry_run: bool = False):
    config = load_config(config_path)
    if dry_run:
        logger.info(f"[DRY RUN] Would create {len(LABELS)} labels in {repo_name}:")
        for name, color, description in LABELS:
            logger.info(f"  {name} (#{color}) — {description}")
        return

    g = get_github_client()
    repo = g.get_repo(repo_name)

    for name, color, description in LABELS:
        ensure_label_exists(repo, name, color, description)
        logger.info(f"✓ {name}")

    logger.info(f"Created {len(LABELS)} labels in {repo_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Scraut labels")
    parser.add_argument("--repo", required=True, help="org/repo format")
    parser.add_argument("--config", help="Path to scraut.yml")
    parser.add_argument("--dry-run", action="store_true", help="Print without creating")
    args = parser.parse_args()
    main(args.repo, args.config, args.dry_run)
