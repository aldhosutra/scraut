"""
scripts/sprint/check_scope_creep.py
Detect mid-sprint scope creep: new issues added after sprint planning
that push total SP over team capacity.
Alerts Slack with the specific overage and suggests what to defer.
"""
import argparse
import logging
from scripts.utils.config import load_config, get_current_sprint
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue
from scripts.sprint.calculate_velocity import calculate_rolling_velocity
from scripts.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_scope_creep(repo_name: str, config: dict) -> None:
    """Detect if sprint SP exceeds capacity; alert if so."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_num = get_current_sprint()
    sprint_label = f"sprint-{sprint_num:02d}"

    all_issues = get_issues(repo, labels=[sprint_label], state="all")
    open_issues = [i for i in all_issues if i.state == "open"]
    closed_issues = [i for i in all_issues if i.state == "closed"]

    total_sp = sum(get_sp_from_issue(i) for i in all_issues)
    completed_sp = sum(get_sp_from_issue(i) for i in closed_issues)
    remaining_sp = sum(get_sp_from_issue(i) for i in open_issues)

    velocity = calculate_rolling_velocity(repo_name)
    capacity = round(velocity.get("avg", 26) * config["sprint"].get("capacity_buffer", 0.85))

    if total_sp <= capacity:
        logger.info(f"Sprint {sprint_num}: {total_sp}/{capacity} sp — no scope creep")
        return

    overage = total_sp - capacity
    webhook = config.get("notifications", {}).get("slack_webhook")

    if webhook:
        deferral_candidates = []
        for issue in open_issues:
            labels = [l.name for l in issue.labels]
            if "in-review" not in labels and "in-sprint" in labels:
                sp = get_sp_from_issue(issue)
                priority = next((l for l in labels if l.startswith("p:")), "p:low")
                deferral_candidates.append((issue, sp, priority))

        deferral_candidates.sort(key=lambda x: (
            {"p:high": 0, "p:medium": 1, "p:low": 2}.get(x[2], 3), -x[1]
        ))

        defer_suggestion = ""
        if deferral_candidates:
            to_defer = []
            freed_sp = 0
            for issue, sp, priority in reversed(deferral_candidates):
                to_defer.append(f"• #{issue.number} \"{issue.title[:50]}\" ({sp} sp, {priority})")
                freed_sp += sp
                if total_sp - freed_sp <= capacity:
                    break
            if to_defer:
                defer_suggestion = (
                    "\n\n*To get back under capacity, consider deferring:*\n"
                    + "\n".join(to_defer)
                )

        post_to_slack(
            webhook,
            f"⚠️ *Sprint {sprint_num:02d} is over capacity!*\n"
            f"Total: *{total_sp} sp* vs capacity: *{capacity} sp* "
            f"(overflow: {overage} sp)\n"
            f"Completed: {completed_sp} sp · Remaining: {remaining_sp} sp"
            + defer_suggestion
        )

    logger.info(f"Scope creep detected: {total_sp} sp vs {capacity} sp capacity")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    check_scope_creep(args.repo, config)
