"""
scrum/.scraut/suggestions/measure.py
Run 2 sprints after a suggestion is implemented.
Re-runs the original detector. Compares before/after.
Marks suggestion resolved (improved) or re-opens if no improvement.
"""
import json
import logging
import re
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_scraut_root
from scraut.platform.utils.file_utils import read_file, atomic_write
from scraut.platform.github.api import get_github_client, post_comment
from scraut.platform.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def measure_suggestion(suggestion_file: str, repo_name: str, config: dict) -> None:
    path = Path(suggestion_file)
    content = read_file(path)

    # Extract baseline metrics and detector name
    detector_match = re.search(r"\*\*Detector:\*\*\s+(\w+)", content)
    baseline_match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
    issue_match = re.search(r"Issue #(\d+)", content)

    if not detector_match or not baseline_match:
        logger.warning(f"Could not parse suggestion file: {suggestion_file}")
        return

    detector_name = detector_match.group(1)
    baseline = json.loads(baseline_match.group(1))
    issue_num = int(issue_match.group(1)) if issue_match else None

    # Re-run the appropriate detector
    from scraut.scrum.suggestions.detectors import (
        blocker_frequency_detector, velocity_drop_detector,
        pr_review_lag_detector, capacity_imbalance_detector,
        retro_followthrough_detector, sentiment_trend_detector,
    )
    detector_map = {
        "BlockerFrequencyDetector": lambda: blocker_frequency_detector(config),
        "VelocityDropDetector": lambda: velocity_drop_detector(repo_name, config),
        "PRReviewLagDetector": lambda: pr_review_lag_detector(repo_name, config),
        "CapacityImbalanceDetector": lambda: capacity_imbalance_detector(repo_name, config),
        "RetroFollowthroughDetector": lambda: retro_followthrough_detector(config),
        "SentimentTrendDetector": lambda: sentiment_trend_detector(config),
    }

    run_detector = detector_map.get(detector_name)
    if not run_detector:
        logger.error(f"Unknown detector: {detector_name}")
        return

    current_evidence = run_detector()
    improved = current_evidence is None  # Pattern no longer detected = improvement

    if not improved and current_evidence:
        # Check if metrics improved (even if pattern still present)
        current_count = len(current_evidence.instances)
        baseline_count = baseline.get("blocker_mentions",
                          baseline.get("prs_over_sla",
                          baseline.get("missed_action_items", 999)))
        improved = current_count < baseline_count * 0.6  # 40%+ improvement

    root = get_workspace_root()
    scraut_root = get_scraut_root()
    suggestion_id = re.search(r"(s\d+)", path.stem).group(1)

    if improved:
        # Move to resolved/
        resolved_dir = scraut_root / "suggestions" / "resolved"
        resolved_dir.mkdir(exist_ok=True)
        result_note = (
            f"\n\n---\n## ✅ Measurement Result (Sprint +2)\n"
            f"Pattern no longer detected or significantly reduced.\n"
            f"**Outcome:** Improved\n"
            f"**Baseline:** {json.dumps(baseline, indent=2)}\n"
        )
        atomic_write(resolved_dir / path.name, content + result_note)
        path.unlink()
        outcome = "✅ improved"
    else:
        # Re-open as active
        active_dir = scraut_root / "suggestions" / "active"
        result_note = (
            f"\n\n---\n## ❌ Measurement Result (Sprint +2)\n"
            f"Pattern still present. Suggestion may need a different approach.\n"
            f"**Outcome:** No significant improvement\n"
        )
        current_content = content.replace("**Status:** implemented",
                                           "**Status:** proposed (re-opened)")
        atomic_write(active_dir / path.name, current_content + result_note)
        path.unlink()
        outcome = "❌ no improvement — re-opened"

    # Post result to GitHub Issue
    if issue_num:
        g = get_github_client()
        repo = g.get_repo(repo_name)
        issue = repo.get_issue(issue_num)
        post_comment(issue,
            f"## 📊 Measurement complete\n\n"
            f"**2-sprint post-implementation check:** {outcome}\n\n"
            f"Suggestion moved to `.scraut/suggestions/{'resolved' if improved else 'active'}/`"
        )

    # Post to Slack
    webhook = config.get("notifications", {}).get("slack_webhook")
    if webhook:
        post_to_slack(webhook,
            f"📊 Suggestion {suggestion_id} measurement: {outcome}"
        )

    logger.info(f"Measurement complete for {suggestion_id}: {outcome}")
