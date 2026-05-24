"""
scrum/agents/checkpoint.py
Human checkpoint detection and management.
When triggered, pauses agent orchestration and notifies humans.
Creates a "checkpoint" GitHub Issue that must be resolved before agents resume.
"""
import logging
from datetime import date
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_current_sprint
from scraut.platform.utils.file_utils import read_file
from scraut.platform.github.api import get_github_client, create_issue
from scraut.platform.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHECKPOINT_ISSUE_TEMPLATE = """<!-- scraut-checkpoint -->
## 🛑 Human Checkpoint Required

**Trigger:** {trigger}
**Sprint:** {sprint_num}
**Date:** {date}
**Agent team paused:** yes

### What happened
{description}

### What needs human decision
{decision_needed}

### How to resume
1. Review the situation above
2. Take the appropriate action (described above)
3. Comment `/resume` to allow agents to continue
4. Comment `/pause` to keep agents paused until next checkpoint review

### Affected agents
{affected_agents}

---
*This issue was created automatically by Scraut. Do not close manually — use `/resume` or `/pause`.*
"""


def is_checkpoint_open(repo_name: str) -> bool:
    """Check if there is an open unresolved checkpoint issue."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    issues = list(repo.get_issues(state="open", labels=["scraut-checkpoint"]))
    return len(issues) > 0


def create_checkpoint(trigger: str, description: str, decision_needed: str,
                      affected_agents: list, repo_name: str, config: dict) -> None:
    """Create a human checkpoint issue and notify via Slack."""
    sprint_num = get_current_sprint()
    g = get_github_client()
    repo = g.get_repo(repo_name)

    issue_body = CHECKPOINT_ISSUE_TEMPLATE.format(
        trigger=trigger,
        sprint_num=sprint_num,
        date=date.today().isoformat(),
        description=description,
        decision_needed=decision_needed,
        affected_agents="\n".join(f"- {a}" for a in affected_agents) or "- All agents",
    )
    issue = create_issue(
        repo,
        title=f"🛑 Agent Checkpoint: {trigger}",
        body=issue_body,
        labels=["scraut-checkpoint"],
    )
    logger.info(f"Created checkpoint issue #{issue.number}: {trigger}")

    webhook = config.get("notifications", {}).get("slack_webhook")
    if webhook:
        post_to_slack(webhook,
            f"🛑 *Agent team paused — human input required*\n"
            f"Trigger: {trigger}\n"
            f"Issue #{issue.number}: {issue.html_url}"
        )


def check_human_checkpoint(agent_states: dict, config: dict,
                            repo_name: str) -> bool:
    """
    Check if any human checkpoint conditions are met.
    Returns True if agents should be paused.
    """
    checkpoint_config = config.get("agents", {}).get("human_checkpoints", [])
    checkpoint_events = {c["event"] for c in checkpoint_config}

    if is_checkpoint_open(repo_name):
        logger.info("Existing checkpoint open. Agents remain paused.")
        return True

    if "escalation_count" in checkpoint_events:
        escalated = [aid for aid, state in agent_states.items()
                     if state.get("escalation_needed")]
        max_escalations = 2
        if len(escalated) >= max_escalations:
            create_checkpoint(
                trigger="escalation_count",
                description=(
                    f"{len(escalated)} agents are blocked and require human intervention:\n"
                    + "\n".join(f"- {a}: {agent_states[a].get('blockers', 'unknown')[:100]}"
                                for a in escalated)
                ),
                decision_needed=(
                    "Review each agent's blocker. Resolve the underlying issue (missing secret, "
                    "ambiguous requirement, architectural decision) and comment `/resume` when done."
                ),
                affected_agents=escalated,
                repo_name=repo_name,
                config=config,
            )
            return True

    return False


def process_checkpoint_response(issue_number: int, comment_body: str,
                                 repo_name: str) -> None:
    """Process /resume or /pause commands on a checkpoint issue."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    labels = [l.name for l in issue.labels]

    if "scraut-checkpoint" not in labels:
        return

    if "/resume" in comment_body:
        issue.edit(state="closed")
        issue.create_comment(
            "✅ Checkpoint resolved. Agent team will resume on next orchestrator cycle."
        )
        logger.info(f"Checkpoint #{issue_number} resolved via /resume")
    elif "/pause" in comment_body:
        issue.create_comment(
            "⏸️ Agents remain paused. Comment `/resume` when ready to continue."
        )
        logger.info(f"Checkpoint #{issue_number} explicitly paused")
