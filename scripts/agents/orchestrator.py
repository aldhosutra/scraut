"""
scripts/agents/orchestrator.py
Orchestrator Agent: reads milestone roadmap and sprint meta,
assigns available tasks to specialist agents by writing to GitHub Issues,
monitors agent standup files for blockers and completion,
and requests human checkpoints when needed.

The Orchestrator writes its decisions to:
  sprint-N/standup/YYYY-MM-DD/agent-orchestrator.md
"""
import json
import logging
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import read_file, atomic_write, extract_section
from scripts.github.api import (get_github_client, get_issues, get_sp_from_issue,
                                 add_label_to_issue, post_comment, create_issue)
from scripts.llm.client import complete_json
from scripts.llm.prompts import SYSTEM_SCRUM_ASSISTANT
from scripts.notifications.slack_post import post_to_slack
from scripts.agents.checkpoint import check_human_checkpoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ORCHESTRATOR_STANDUP_TEMPLATE = """# Standup — agent-orchestrator
<!--
  Sprint: sprint-{sprint_num:02d}
  Date: {date}
  Author: agent-orchestrator
  Auto-generated: yes
-->

## Yesterday
{yesterday_summary}

## Today
{today_summary}

## Blockers
{blockers_summary}

## Agent State
- Role: orchestrator
- Tasks assigned this cycle: {tasks_assigned}
- Agents active: {agents_active}
- Agents blocked: {agents_blocked}
- Human checkpoint needed: {checkpoint_needed}
- Last cycle: {date}
"""

ASSIGN_TASK_PROMPT = """
You are the orchestrator for an AI agent team.

## Available tasks (from sprint roadmap):
{available_tasks}

## Available agents and their capabilities:
{agents}

## Current agent states (from standup files):
{agent_states}

## Assignment rules:
1. Each agent should have at most 1-2 tasks in-progress at a time
2. Respect task dependencies (don't assign a task until its dependencies are Done)
3. Match task type to agent specialty (backend → backend tasks, frontend → UI tasks)
4. Flag any tasks that cannot be assigned (dependencies not met, no suitable agent)

Reply with ONLY JSON:
{{
  "assignments": [
    {{
      "task_issue_number": N,
      "task_title": "...",
      "assigned_to": "agent-id",
      "reason": "one sentence",
      "priority": "high|medium|low"
    }}
  ],
  "unassignable": [
    {{"issue": N, "reason": "..."}}
  ],
  "orchestrator_notes": "summary of this cycle"
}}
"""


def read_agent_standup_states(config: dict, target_date: str) -> dict[str, dict]:
    """Read all agent standup files for today and extract their state."""
    root = get_repo_root()
    sprint_num = get_current_sprint()
    standup_dir = root / f"sprint-{sprint_num:02d}" / "standup" / target_date
    agent_states = {}

    if not standup_dir.exists():
        return agent_states

    for f in standup_dir.glob("agent-*.md"):
        agent_id = f.stem
        content = read_file(f)
        if not content:
            continue

        today_section = extract_section(content, "Today")
        blockers_section = extract_section(content, "Blockers")
        agent_state_section = extract_section(content, "Agent State")
        escalation_needed = "yes" in (agent_state_section or "").lower() and "escalation" in (agent_state_section or "").lower()

        agent_states[agent_id] = {
            "today": today_section,
            "blockers": blockers_section,
            "escalation_needed": escalation_needed,
            "raw": content,
        }

    return agent_states


def get_available_tasks(repo_name: str, config: dict) -> list[dict]:
    """Get unassigned sprint issues that are Ready or Backlog."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_num = get_current_sprint()
    sprint_label = f"sprint-{sprint_num:02d}"

    available = []
    issues = get_issues(repo, labels=[sprint_label], state="open")
    for issue in issues:
        label_names = [l.name for l in issue.labels]
        if "agent-assigned" in label_names:
            continue
        if "in-review" in label_names:
            continue
        sp = get_sp_from_issue(issue)
        available.append({
            "number": issue.number,
            "title": issue.title,
            "body": (issue.body or "")[:300],
            "labels": label_names,
            "sp": sp,
        })

    return available


def assign_tasks_to_agents(repo_name: str, config: dict, assignments: list[dict]) -> list[str]:
    """Apply assignments: add labels, update issue assignees, notify agents."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    assigned = []

    for assignment in assignments:
        issue_num = assignment.get("task_issue_number")
        agent_id = assignment.get("assigned_to")
        if not issue_num or not agent_id:
            continue

        try:
            issue = repo.get_issue(issue_num)
            add_label_to_issue(issue, "agent-assigned")
            post_comment(issue,
                f"🤖 **Assigned to {agent_id}** by orchestrator\n"
                f"Priority: {assignment.get('priority', 'medium')}\n"
                f"Reason: {assignment.get('reason', '')}"
            )
            assigned.append(f"#{issue_num} → {agent_id}")
            logger.info(f"Assigned #{issue_num} to {agent_id}")
        except Exception as e:
            logger.error(f"Failed to assign #{issue_num}: {e}")

    return assigned


def write_orchestrator_standup(today_summary: str, yesterday_summary: str,
                                blockers: str, tasks_assigned: int,
                                agents_active: list, agents_blocked: list,
                                checkpoint_needed: bool, config: dict) -> None:
    root = get_repo_root()
    sprint_num = get_current_sprint()
    today = date.today().isoformat()
    standup_dir = root / f"sprint-{sprint_num:02d}" / "standup" / today
    standup_dir.mkdir(parents=True, exist_ok=True)

    content = ORCHESTRATOR_STANDUP_TEMPLATE.format(
        sprint_num=sprint_num,
        date=today,
        yesterday_summary=yesterday_summary or "No previous cycle data",
        today_summary=today_summary or "Monitoring agent progress",
        blockers_summary=blockers or "None",
        tasks_assigned=tasks_assigned,
        agents_active=", ".join(agents_active) or "none",
        agents_blocked=", ".join(agents_blocked) or "none",
        checkpoint_needed="YES — see escalations above" if checkpoint_needed else "no",
    )
    atomic_write(standup_dir / "agent-orchestrator.md", content)


def run_orchestrator_cycle(repo_name: str, config: dict) -> None:
    """Main orchestrator cycle. Runs on schedule when agent mode is enabled."""
    if not config.get("agents", {}).get("enabled"):
        logger.info("Agent mode disabled. Skipping orchestrator.")
        return

    today = date.today().isoformat()
    logger.info(f"Orchestrator cycle: {today}")

    # 1. Read current agent states
    agent_states = read_agent_standup_states(config, today)

    # 2. Check for human checkpoint triggers
    checkpoint_needed = check_human_checkpoint(agent_states, config, repo_name)
    if checkpoint_needed:
        logger.info("Human checkpoint triggered. Pausing orchestration.")
        return

    # 3. Get available tasks
    available_tasks = get_available_tasks(repo_name, config)
    if not available_tasks:
        logger.info("No available tasks to assign")
        return

    # 4. Build agent descriptions
    agent_specs = [
        {"id": a["id"], "type": a["type"], "specialty": a.get("specialty", "general")}
        for a in config.get("agents", {}).get("roles", [])
        if a.get("enabled") and a["type"] == "specialist"
    ]

    # 5. LLM assignment decision
    prompt = ASSIGN_TASK_PROMPT.format(
        available_tasks=json.dumps(available_tasks, indent=2),
        agents=json.dumps(agent_specs, indent=2),
        agent_states=json.dumps({
            k: {"today": v["today"][:200], "blocked": v["escalation_needed"]}
            for k, v in agent_states.items()
        }, indent=2),
    )
    decision = complete_json(prompt, system=SYSTEM_SCRUM_ASSISTANT)

    if not decision:
        logger.warning("Orchestrator LLM call failed. No assignments this cycle.")
        return

    # 6. Apply assignments
    assignments = decision.get("assignments", [])
    assigned = assign_tasks_to_agents(repo_name, config, assignments)

    # 7. Detect blocked agents
    agents_blocked = [aid for aid, state in agent_states.items()
                      if state.get("escalation_needed")]
    agents_active = [aid for aid in agent_states.keys()
                     if aid != "agent-orchestrator"]

    # 8. Write orchestrator standup
    write_orchestrator_standup(
        today_summary="\n".join(f"- Assigned {a}" for a in assigned),
        yesterday_summary=decision.get("orchestrator_notes", ""),
        blockers="\n".join(f"- {a}: needs human intervention" for a in agents_blocked),
        tasks_assigned=len(assigned),
        agents_active=agents_active,
        agents_blocked=agents_blocked,
        checkpoint_needed=len(agents_blocked) > 0,
        config=config,
    )

    # 9. Post Slack summary
    webhook = config.get("notifications", {}).get("slack_webhook")
    if webhook and assigned:
        post_to_slack(webhook,
            f"🤖 Orchestrator cycle complete:\n"
            + "\n".join(f"• {a}" for a in assigned)
        )

    logger.info(f"Orchestrator cycle complete: {len(assigned)} tasks assigned")
