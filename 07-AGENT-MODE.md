# Phase 7: Agent Mode
*Scraut Implementation — requires Phases 1–6 complete*

## Goal
Enable AI agent teams to coordinate through Scraut's text-file substrate.
Agents write the same markdown files as humans. The Orchestrator reads the
milestone roadmap and assigns tasks. Specialist agents claim work, execute,
and report via standup files. Human checkpoints prevent runaway automation.
Deadlock detection identifies coordination failures early.

## Important: Agent mode is OFF by default

```yaml
# scraut.yml
agents:
  enabled: false   # ← change to true to enable
```

When `enabled: false`, all agent workflows are skipped. Human teams work
identically whether agent mode is on or off. Enabling agents adds new
writers to the same file system — no architectural changes.

---

## Agent Coordination Principles

1. **Text files as blackboard** — agents coordinate via reading/writing the same
   markdown files as humans. No direct agent-to-agent communication.
2. **Claim via standup** — an agent "claims" a task by writing it to its Today section
3. **No conflicts** — each agent has its own standup file (`agent-backend.md`)
4. **Escalation via Blockers** — agents cannot self-resolve? Write to Blockers section
5. **Human checkpoints** — at sprint boundaries and on escalation thresholds, the system
   pauses and waits for human approval
6. **Identical format** — agent standup files use the same template as human files,
   with an optional `## Agent State` block appended at the end

---

## 1. `scripts/agents/orchestrator.py`

```python
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
        # Skip already assigned to an agent
        if "agent-assigned" in label_names:
            continue
        # Skip if in-review or has a PR
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
            # Note the assignment in a comment
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
```

---

## 2. `scripts/agents/checkpoint.py`

```python
"""
scripts/agents/checkpoint.py
Human checkpoint detection and management.
When triggered, pauses agent orchestration and notifies humans.
Creates a "checkpoint" GitHub Issue that must be resolved before agents resume.
"""
import logging
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import read_file
from scripts.github.api import get_github_client, create_issue
from scripts.notifications.slack_post import post_to_slack

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

    # Slack alert
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
    sprint_num = get_current_sprint()

    # Check if a checkpoint is already open
    if is_checkpoint_open(repo_name):
        logger.info("Existing checkpoint open. Agents remain paused.")
        return True

    # Check 1: Sprint boundary (always checkpoint at sprint end if configured)
    # This is triggered by sprint-review workflow, not here

    # Check 2: Too many agent escalations
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
```

---

## 3. `scripts/agents/deadlock_detect.py`

```python
"""
scripts/agents/deadlock_detect.py
Detect agent coordination deadlocks:
- Agent A is waiting for Agent B, which is waiting for Agent A
- Agent has been in WIP for more than N hours with zero commits
- Two agents have claimed the same issue

Runs as part of the orchestrator cycle.
"""
import json
import logging
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import read_file, extract_section
from scripts.github.api import get_github_client, get_issues

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def detect_duplicate_claims(repo_name: str, config: dict) -> list[dict]:
    """Detect cases where two agents have claimed the same issue."""
    root = get_repo_root()
    sprint_num = get_current_sprint()
    today = date.today().isoformat()
    standup_dir = root / f"sprint-{sprint_num:02d}" / "standup" / today

    issue_claimants = {}  # issue_num → list of agent_ids

    if not standup_dir.exists():
        return []

    for f in standup_dir.glob("agent-*.md"):
        agent_id = f.stem
        content = read_file(f)
        today_section = extract_section(content, "Today")
        import re
        claimed_issues = re.findall(r"#(\d+)", today_section or "")
        for issue_num in claimed_issues:
            num = int(issue_num)
            issue_claimants.setdefault(num, []).append(agent_id)

    conflicts = [
        {"issue": num, "claimed_by": agents}
        for num, agents in issue_claimants.items()
        if len(agents) > 1
    ]
    return conflicts


def detect_stale_wip(repo_name: str, config: dict,
                     stale_hours: int = 24) -> list[dict]:
    """
    Detect agents that have been claiming an issue in their Today section
    for more than N hours with no corresponding commits.
    Uses activity.json from repo sync as the commit source.
    """
    root = get_repo_root()
    sprint_num = get_current_sprint()
    stale = []

    # Check last 2 days of activity for each agent
    from datetime import timedelta as td
    for days_ago in range(1, 3):
        check_date = (date.today() - td(days=days_ago)).isoformat()
        activity_path = (root / f"sprint-{sprint_num:02d}" /
                         "code" / check_date / "activity.json")
        content = read_file(activity_path)
        if not content:
            continue

        activity = json.loads(content)
        agents_with_commits = set(
            login for login, data in activity.get("members", {}).items()
            if data.get("commits")
        )

        standup_dir = root / f"sprint-{sprint_num:02d}" / "standup" / check_date
        if not standup_dir.exists():
            continue

        for f in standup_dir.glob("agent-*.md"):
            agent_id = f.stem
            login = agent_id.replace("agent-", "")  # map agent-backend → backend login
            content_s = read_file(f)
            today_section = extract_section(content_s, "Today")

            if today_section and login not in agents_with_commits:
                stale.append({
                    "agent": agent_id,
                    "date": check_date,
                    "today_section": today_section[:200],
                    "days_without_commits": days_ago,
                })

    return stale


def detect_all_deadlocks(repo_name: str, config: dict) -> dict:
    """Run all deadlock detectors. Returns summary dict."""
    duplicates = detect_duplicate_claims(repo_name, config)
    stale = detect_stale_wip(repo_name, config)

    if duplicates:
        logger.warning(f"⚠️ Duplicate claims detected: {duplicates}")
    if stale:
        logger.warning(f"⚠️ Stale WIP detected: {[s['agent'] for s in stale]}")

    return {
        "duplicate_claims": duplicates,
        "stale_wip": stale,
        "has_issues": bool(duplicates or stale),
    }
```

---

## 4. GitHub Actions Workflow

### `.github/workflows/agent-orchestrator.yml`

```yaml
name: Scraut — Agent Orchestrator
on:
  schedule:
    - cron: '0 */4 * * 1-5'  # Every 4 hours on weekdays
  workflow_dispatch:

jobs:
  orchestrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Check if agent mode is enabled
        id: check_agents
        run: |
          ENABLED=$(python -c "
          import yaml
          cfg = yaml.safe_load(open('scraut.yml'))
          print(str(cfg.get('agents', {}).get('enabled', False)).lower())
          ")
          echo "agents_enabled=$ENABLED" >> $GITHUB_OUTPUT

      - name: Run orchestrator cycle
        if: steps.check_agents.outputs.agents_enabled == 'true'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
        run: |
          python - << 'EOF'
          import sys
          import os
          sys.path.insert(0, '.')
          from scripts.utils.config import load_config
          from scripts.agents.orchestrator import run_orchestrator_cycle
          from scripts.agents.deadlock_detect import detect_all_deadlocks

          config = load_config()
          repo = os.environ.get('GITHUB_REPOSITORY', '')

          # Check for deadlocks first
          deadlocks = detect_all_deadlocks(repo, config)
          if deadlocks["has_issues"]:
              print(f"⚠️ Deadlocks detected: {deadlocks}")
              # Deadlocks are surfaced but don't block orchestration
              # Orchestrator will handle them in its cycle

          # Run orchestrator
          run_orchestrator_cycle(repo, config)
          EOF

      - name: Commit orchestrator standup
        if: steps.check_agents.outputs.agents_enabled == 'true'
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add sprint-*/standup/
          git diff --staged --quiet || git commit -m "chore: orchestrator cycle [skip ci]"
          git push

  # Checkpoint response handler
  process-checkpoint:
    runs-on: ubuntu-latest
    if: github.event_name == 'issue_comment' &&
        contains(github.event.comment.body, '/resume') ||
        contains(github.event.comment.body, '/pause')
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Process checkpoint command
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          python - << 'EOF'
          import sys, os
          sys.path.insert(0, '.')
          from scripts.utils.config import load_config
          from scripts.agents.checkpoint import process_checkpoint_response

          config = load_config()
          repo = os.environ.get('GITHUB_REPOSITORY', '')
          issue_num = int(os.environ.get('ISSUE_NUMBER', '0'))
          comment = os.environ.get('COMMENT_BODY', '')
          process_checkpoint_response(issue_num, comment, repo)
          EOF
        env:
          ISSUE_NUMBER: ${{ github.event.issue.number }}
          COMMENT_BODY: ${{ github.event.comment.body }}
```

---

## 5. Specialist Agent Template

Each specialist agent is a GitHub Actions workflow. Here is the Backend Agent template.
Create similar files for `agent-frontend.yml`, `agent-test.yml`, `agent-review.yml`.

### `.github/workflows/agent-backend.yml`

```yaml
name: Scraut — Backend Agent
on:
  schedule:
    - cron: '30 */4 * * 1-5'  # 30 min after orchestrator
  workflow_dispatch:
    inputs:
      task_issue:
        description: 'Issue number to work on (optional — agent discovers from board)'
        required: false

jobs:
  work:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Check if agent mode enabled
        id: check
        run: |
          ENABLED=$(python -c "
          import yaml
          cfg = yaml.safe_load(open('scraut.yml'))
          agents = cfg.get('agents', {})
          enabled = agents.get('enabled', False)
          roles = {r['id']: r.get('enabled', False) for r in agents.get('roles', [])}
          print(str(enabled and roles.get('agent-backend', False)).lower())
          ")
          echo "enabled=$ENABLED" >> $GITHUB_OUTPUT

      - name: Discover and claim task
        if: steps.check.outputs.enabled == 'true'
        id: claim
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python - << 'EOF'
          import sys, os, json
          sys.path.insert(0, '.')
          from scripts.utils.config import load_config
          from scripts.github.api import get_github_client, get_issues, get_sp_from_issue
          from scripts.utils.config import get_current_sprint

          config = load_config()
          repo_name = os.environ.get('GITHUB_REPOSITORY', '')
          sprint_num = get_current_sprint()
          sprint_label = f"sprint-{sprint_num:02d}"

          # Find an assigned-to-me, in-progress task or claim a new Ready one
          g = get_github_client()
          repo = g.get_repo(repo_name)
          issues = get_issues(repo, labels=[sprint_label], state="open")

          # Look for agent-assigned + backend tasks
          for issue in issues:
              label_names = [l.name for l in issue.labels]
              if ("agent-assigned" in label_names and
                  "in-sprint" in label_names and
                  "in-review" not in label_names):
                  # Check if comment says assigned to this agent
                  comments = list(issue.get_comments())
                  for c in reversed(comments):
                      if "agent-backend" in (c.body or ""):
                          print(f"CLAIMED_ISSUE={issue.number}")
                          with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                              f.write(f"claimed_issue={issue.number}\n")
                          break
                  break
          else:
              print("No task available for agent-backend this cycle")
          EOF

      - name: Write agent standup
        if: steps.check.outputs.enabled == 'true'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          CLAIMED_ISSUE: ${{ steps.claim.outputs.claimed_issue }}
        run: |
          python - << 'EOF'
          import sys, os
          from datetime import date
          from pathlib import Path
          sys.path.insert(0, '.')
          from scripts.utils.config import load_config, get_repo_root, get_current_sprint
          from scripts.utils.file_utils import atomic_write

          config = load_config()
          root = get_repo_root()
          sprint_num = get_current_sprint()
          today = date.today().isoformat()
          claimed = os.environ.get('CLAIMED_ISSUE', '')

          standup_dir = root / f"sprint-{sprint_num:02d}" / "standup" / today
          standup_dir.mkdir(parents=True, exist_ok=True)

          content = f"""# Standup — agent-backend
<!-- Sprint: sprint-{sprint_num:02d} | Date: {today} | Author: agent-backend -->

## Yesterday
- Reviewed assigned tasks from orchestrator

## Today
{f'- Working on #{claimed}: [implementing assigned task]' if claimed else '- No task assigned this cycle — awaiting orchestrator'}

## Blockers
None

## Agent State
- Role: backend specialist
- CI status: pending
- Escalation needed: no
- Last cycle: {today}
"""
          atomic_write(standup_dir / "agent-backend.md", content)
          print("Standup written for agent-backend")
          EOF

      - name: Commit agent standup
        if: steps.check.outputs.enabled == 'true'
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add sprint-*/standup/
          git diff --staged --quiet || git commit -m "chore: agent-backend standup [skip ci]"
          git push
```

---

## 6. `scraut.yml` Agent Section (Full)

Add this to `scraut.yml` when enabling agents:

```yaml
agents:
  enabled: false               # Set to true to activate agent mode

  roles:
    - id: agent-orchestrator
      type: orchestrator
      enabled: false
      description: "Plans sprints, assigns tasks to specialist agents"

    - id: agent-backend
      type: specialist
      specialty: backend
      enabled: false
      github_workflow: .github/workflows/agent-backend.yml
      description: "Implements backend/API tasks"

    - id: agent-frontend
      type: specialist
      specialty: frontend
      enabled: false
      github_workflow: .github/workflows/agent-frontend.yml
      description: "Implements UI/frontend tasks"

    - id: agent-test
      type: specialist
      specialty: testing
      enabled: false
      github_workflow: .github/workflows/agent-test.yml
      description: "Reviews PRs, writes tests, validates DoD"

    - id: agent-review
      type: specialist
      specialty: review
      enabled: false
      github_workflow: .github/workflows/agent-review.yml
      description: "Reviews PRs, leaves structured feedback"

  human_checkpoints:
    - event: sprint_boundary     # Pause before every new sprint (requires human approval to start)
    - event: milestone_eta_slip  # Pause if ETA drifts > 1 sprint from target
    - event: escalation_count    # Pause if ≥2 agents are simultaneously blocked
    - event: agent_failure       # Pause if any agent workflow fails repeatedly (>3 times/day)

  autonomy_level: supervised     # supervised | semi-auto | full-auto
  # supervised: human approves sprint plan before agents execute
  # semi-auto: agents run freely, checkpoint at sprint boundaries
  # full-auto: agents run continuously, humans receive reports only
```

---

## Done Criteria for Phase 7

- [ ] `scripts/agents/orchestrator.py` — reads available sprint issues, calls LLM for assignment decision, applies assignments via GitHub labels + comments
- [ ] `scripts/agents/orchestrator.py` — writes its own `agent-orchestrator.md` standup file
- [ ] `scripts/agents/checkpoint.py` — correctly detects escalation_count trigger when ≥2 agents are blocked
- [ ] `scripts/agents/checkpoint.py` — creates GitHub Issue with correct template when checkpoint triggered
- [ ] `scripts/agents/checkpoint.py` — `/resume` comment closes the checkpoint issue
- [ ] `scripts/agents/deadlock_detect.py` — detects duplicate issue claims
- [ ] `scripts/agents/deadlock_detect.py` — detects stale WIP (agent claiming issue but no commits)
- [ ] `agent-orchestrator.yml` — skips entirely when `agents.enabled: false`
- [ ] `agent-backend.yml` — skips when its specific role `enabled: false`
- [ ] Agent standup files follow the canonical format from ROADMAP `## Agent State` block
- [ ] End-to-end test: enable agent mode, run `agent-orchestrator.yml` manually, verify it creates standup file and assigns issues with `agent-assigned` label

*Proceed to `08-SETUP-CLI.md`*
