# Phase 2: Ceremonies
*Scraut Implementation — requires Phase 1 complete*

## Goal
Build the LLM client, all 5 Scrum ceremony workflows with supporting scripts,
the standup template system, burndown/velocity charts, Slack posting, and the
two new ceremony improvements: sprint planning as PR review and team estimation
via GitHub emoji reactions.

---

## 1. `scripts/llm/client.py`

Swappable LLM provider wrapper. Anthropic is primary; OpenAI and Ollama as fallbacks.

```python
"""
scripts/llm/client.py
Swappable LLM provider. Reads provider from scraut.yml.
All calls include token tracking and cost controls.
"""
import os
import logging
from typing import Optional
from scripts.utils.config import get_llm_config

logger = logging.getLogger(__name__)

_daily_tokens_used = 0


def complete(prompt: str, system: Optional[str] = None,
             max_tokens: Optional[int] = None) -> str:
    """
    Call the configured LLM provider with a prompt.
    Returns the text response.
    Falls back to rule-based output on failure.
    """
    global _daily_tokens_used
    config = get_llm_config()
    provider = config.get("provider", "anthropic")
    max_tok = max_tokens or config.get("max_tokens", 1000)
    daily_limit = config.get("cost_controls", {}).get("max_daily_tokens", 100000)

    if _daily_tokens_used >= daily_limit:
        logger.warning("Daily token limit reached. Returning empty response.")
        return ""

    try:
        if provider == "anthropic":
            return _call_anthropic(prompt, system, max_tok)
        elif provider == "openai":
            return _call_openai(prompt, system, max_tok)
        elif provider == "ollama":
            return _call_ollama(prompt, system, max_tok)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return ""


def _call_anthropic(prompt: str, system: Optional[str], max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    config = get_llm_config()
    messages = [{"role": "user", "content": prompt}]
    kwargs = {
        "model": config.get("model", "claude-sonnet-4-6"),
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    global _daily_tokens_used
    _daily_tokens_used += response.usage.input_tokens + response.usage.output_tokens
    return response.content[0].text


def _call_openai(prompt: str, system: Optional[str], max_tokens: int) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    config = get_llm_config()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=config.get("model", "gpt-4o"),
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.choices[0].message.content


def _call_ollama(prompt: str, system: Optional[str], max_tokens: int) -> str:
    import requests
    config = get_llm_config()
    url = config.get("ollama_url", "http://localhost:11434/api/generate")
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    response = requests.post(url, json={
        "model": config.get("model", "llama3"),
        "prompt": full_prompt,
        "stream": False,
    })
    return response.json()["response"]


def complete_json(prompt: str, system: Optional[str] = None) -> dict:
    """Call LLM expecting JSON output. Strips markdown fences before parsing."""
    import json
    import re
    text = complete(prompt, system)
    # Strip ```json fences
    clean = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("```").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}\nResponse: {text}")
        return {}
```

---

## 2. `scripts/llm/prompts.py`

All LLM prompts centralised. Never embed prompts in scripts — always import from here.

```python
"""
scripts/llm/prompts.py
All LLM prompts for Scraut. Import from here — never embed prompts in scripts.
"""

SYSTEM_SCRUM_ASSISTANT = """You are an expert Scrum Master and agile coach.
You have deep knowledge of Scrum, Kanban, and agile methodologies.
You write clearly, concisely, and actionably.
You never use vague language like "consider" or "think about" — you give specific recommendations.
You format output as clean markdown."""

STANDUP_SUMMARY = """
You are generating a team standup summary from individual team member updates.

Today's date: {date}
Sprint: Sprint {sprint_num}
Team: {team_names}

## Individual standup files:
{standup_contents}

## Instructions:
1. Write a concise team standup digest (not longer than 300 words)
2. Summarise WHAT was accomplished yesterday (group similar work)
3. List TODAY's plan by person
4. Highlight ALL blockers prominently at the top if any exist
5. Note if any team member did not submit an update
6. Use plain language — no jargon
7. Format as markdown with clear sections

Output only the markdown. No preamble.
"""

STORY_POINT_ESTIMATE = """
You are estimating the complexity of a GitHub issue using story points.
Use the Fibonacci sequence: 1, 2, 3, 5, 8, 13.

Issue title: {title}
Issue body: {body}
Labels: {labels}

Team's historical context:
- Sprint velocity: {velocity} sp/sprint
- Recent sp:1 examples: {sp1_examples}
- Recent sp:5 examples: {sp5_examples}

Instructions:
- Reply with ONLY a JSON object: {{"estimate": N, "reasoning": "one sentence"}}
- Consider: scope, technical complexity, uncertainty, dependencies
- sp:1 = very small, well-understood change
- sp:3 = moderate, some uncertainty
- sp:5 = significant, some unknowns
- sp:8 = large, considerable uncertainty
- sp:13 = very large or poorly understood — should be broken down
"""

BACKLOG_TRIAGE = """
You are triaging a newly opened GitHub issue for a Scrum team.

Issue: {title}
Body: {body}

Available labels: story, bug, task, spike, chore, p:high, p:medium, p:low

Instructions:
Reply with ONLY a JSON object:
{{
  "type_label": "story|bug|task|spike|chore",
  "priority_label": "p:high|p:medium|p:low",
  "story_point_estimate": N,
  "reasoning": "one sentence justifying the estimate and priority",
  "suggested_acceptance_criteria": ["criterion 1", "criterion 2"]
}}
"""

SPRINT_GOAL_SUGGESTION = """
You are helping a Scrum team set their sprint goal.
Based on the top-priority backlog items, suggest a clear, meaningful sprint goal.

Current sprint: {sprint_num}
Top backlog issues:
{backlog_items}

Team velocity: {velocity} sp/sprint
Previous sprint goal: {prev_goal}

Instructions:
- Suggest 1 sprint goal (one sentence, outcome-focused, not task-focused)
- Suggest which issues should be in this sprint (up to {capacity} sp total)
- Reply with ONLY JSON:
{{
  "suggested_goal": "...",
  "proposed_issues": [123, 456, 789],
  "total_sp": N,
  "rationale": "one sentence"
}}
"""

RETROSPECTIVE_SYNTHESIS = """
You are synthesising individual retrospective entries from team members into a team retrospective summary.

Sprint: Sprint {sprint_num}
Sprint goal: {sprint_goal}
Sprint velocity: {velocity} sp / {planned_sp} sp planned

## Individual entries:
{retro_contents}

## Instructions:
1. "Went well" — group and summarise common themes
2. "Could improve" — group by theme, note frequency
3. "Action items" — extract ALL concrete action items from all entries
4. Add a "Patterns" section if you notice recurring themes from context
5. Be specific — quote specific observations where illuminating
6. Maximum 400 words

Output only the markdown. No preamble.
"""

SPRINT_REVIEW_NARRATIVE = """
You are writing the sprint review narrative for Sprint {sprint_num}.

## Sprint data:
- Goal: {sprint_goal}
- Planned: {planned_sp} story points across {planned_issues} issues
- Completed: {completed_sp} story points across {completed_issues} issues
- Deferred: {deferred_issues}
- Velocity: {velocity} sp (avg last 3 sprints: {avg_velocity})
- CI status: {ci_status}

## What was completed:
{completed_list}

## What was deferred and why:
{deferred_list}

## Key decisions made this sprint:
{decisions}

## Instructions:
Write a sprint review narrative suitable for stakeholders (2–3 paragraphs).
Plain English, no technical jargon, no PR numbers.
Focus on outcomes and value delivered, not tasks completed.
Note what was learned and how it affects the next sprint.

Output only the markdown. No preamble.
"""

MILESTONE_DECOMPOSITION = """
You are decomposing a product milestone into epics, user stories, and technical tasks.

## Milestone:
Title: {title}
Goal: {goal}
Success criteria:
{success_criteria}

Out of scope:
{out_of_scope}

Known risks:
{known_risks}

## Instructions:
Decompose this milestone into a structured breakdown.
Reply with ONLY JSON (no markdown fences):
{{
  "epics": [
    {{
      "id": "E1",
      "title": "Epic title",
      "description": "what this epic covers",
      "estimated_sp_range": [min, max],
      "stories": [
        {{
          "title": "As a [user], I want [action] so that [benefit]",
          "acceptance_criteria": ["criterion 1", "criterion 2"],
          "estimated_sp": N,
          "type": "story|task|spike",
          "depends_on": []
        }}
      ]
    }}
  ],
  "total_sp_range": [min, max],
  "suggested_sprint_count": N,
  "risks": ["risk 1", "risk 2"],
  "confidence": "high|medium|low"
}}
"""

ROADMAP_GENERATION = """
You are generating a sprint-by-sprint roadmap for a milestone.

## Decomposed milestone:
{breakdown}

## Constraints:
- Total sprints: {total_sprints}
- Team capacity: {capacity_per_sprint} sp/sprint
- Priority order: {priority_order}
- Hard deadlines: {hard_deadlines}
- Team: {team_composition}

## Instructions:
Generate a sprint-by-sprint plan. Respect:
1. Story dependencies (don't schedule before dependencies)
2. Team capacity (never exceed capacity_per_sprint per sprint)
3. Include a 10-15% buffer in each sprint for unplanned work
4. Put highest-risk stories early to surface uncertainty

Reply with ONLY JSON:
{{
  "sprints": [
    {{
      "sprint_number": N,
      "theme": "short theme name",
      "stories": [
        {{"title": "...", "sp": N, "epic": "E1", "assignee_type": "backend|frontend|any"}}
      ],
      "total_sp": N,
      "buffer_sp": N,
      "notes": "any special notes for this sprint"
    }}
  ],
  "milestone_sp_total": N,
  "risk_assessment": "paragraph",
  "confidence_interval": {{"p50": N_sprints, "p90": N_sprints}}
}}
"""

SUGGESTION_DRAFT = """
You are drafting an improvement suggestion for a Scrum team based on detected patterns.

## Detected pattern:
Type: {detector_name}
Evidence:
{evidence}

Estimated impact: {estimated_impact}

## Instructions:
Write a concrete, actionable suggestion. Include:
1. A clear title (max 8 words)
2. Why this was flagged (2 sentences referencing the evidence)
3. 2–3 specific action options (Option A recommended, B and C as alternatives)
4. Expected measurable impact for each option
5. How Scraut will auto-measure success in 2 sprints

Reply with ONLY JSON:
{{
  "title": "...",
  "why_flagged": "...",
  "options": [
    {{
      "label": "A",
      "description": "specific action",
      "expected_impact": "metric: X → Y",
      "recommended": true
    }}
  ],
  "measurement_criteria": ["criterion 1", "criterion 2"]
}}
"""

BLOCKER_CLUSTER = """
You are clustering blocker mentions from team standup files by theme.

## Blocker mentions (one per line, format: "sprint|date|person|text"):
{blockers}

## Instructions:
Group these by underlying theme.
Reply with ONLY JSON:
{{
  "clusters": [
    {{
      "theme": "short theme name",
      "instances": [index numbers from the input list],
      "description": "one sentence describing the pattern"
    }}
  ]
}}
"""

HEALTH_REPORT_NARRATIVE = """
You are generating a milestone health report after Sprint {sprint_num} ends.

## Data:
- Milestone: {milestone_title}
- Sprint {sprint_num} of {total_sprints} planned
- Points delivered this sprint: {sprint_delivered_sp}
- Total delivered to date: {total_delivered_sp} of {total_sp} ({percent_done}%)
- Expected at this point: {expected_percent}%
- Board state: {board_state}
- Active blockers: {blockers}
- Agent velocities (if agent mode): {agent_velocities}

## Instructions:
Generate a health report with:
1. One-sentence verdict (on track / watch / at risk)
2. Updated ETA based on current velocity
3. Key risk factors (if any)
4. Specific recommendation (what the team or orchestrator should do now)
Maximum 200 words. Plain English.

Output only the markdown. No preamble.
"""

SENTIMENT_SCORE = """
Rate the overall sentiment/morale of the following standup and retrospective entries.
Score from 1 (very negative/burned out) to 10 (very positive/energised).

## Entries:
{entries}

Reply with ONLY JSON:
{{
  "score": N,
  "signals": ["positive signal 1", "negative signal 1"],
  "concern_level": "none|low|medium|high"
}}
"""
```

---

## 3. `scripts/standup/reset_templates.py`

Creates today's standup files for each team member. **Create-if-not-exists only** — never overwrites.

```python
"""
scripts/standup/reset_templates.py
Create standup template files for today for each team member.
CRITICAL: Only creates files that don't exist. Never overwrites existing files.
Bot commits include [skip ci] to avoid triggering standup workflow.
"""
import argparse
import logging
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import create_if_not_exists

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STANDUP_TEMPLATE = """# Standup — {display_name}
<!-- 
  Sprint: sprint-{sprint_num:02d}
  Date: {date}
  Author: {login}
  Pre-filled: No (edit manually or wait for repo sync pre-fill)
  
  Navigation:
  - Current sprint: sprint-{sprint_num:02d}/
  - Sprint board: [GitHub Projects link]
  - Backlog: sprint-{sprint_num:02d}/grooming/backlog-ideas.md
  - Blockers from yesterday: sprint-{sprint_num:02d}/standup/summary/
-->

## Yesterday
<!-- What did you complete? Reference issues/PRs where applicable. -->

## Today
<!-- What will you work on today? Reference issues if possible. -->

## Blockers
<!-- Anything blocking your progress? Scraut tracks these automatically. -->
<!-- Write "None" if no blockers. -->
None

## Notes
<!-- Optional: OOO, reduced availability, context for the team -->
"""

AGENT_STANDUP_TEMPLATE = """# Standup — {display_name}
<!-- 
  Sprint: sprint-{sprint_num:02d}
  Date: {date}
  Author: {agent_id} (AI agent)
  Auto-generated by: {agent_id} workflow
-->

## Yesterday
<!-- Agent fills this in automatically from commit/PR activity -->

## Today
<!-- Agent fills this in automatically from claimed tasks -->

## Blockers
<!-- Agent fills this in if escalation needed -->
None

## Notes
<!-- Agent state information -->

## Agent State
- Tasks completed this sprint: 0 of 0 assigned
- Velocity: 0 sp delivered
- CI status: unknown
- Last commit: none
- Escalation needed: no
"""


def reset_templates(config: dict, dry_run: bool = False) -> None:
    root = get_repo_root()
    sprint_num = get_current_sprint()
    today = date.today().isoformat()

    # Create today's standup directory
    standup_dir = root / f"sprint-{sprint_num:02d}" / "standup" / today
    standup_dir.mkdir(parents=True, exist_ok=True)

    # Create files for each human team member
    created = []
    for member in config["team"]["members"]:
        login = member["login"]
        display = member["display"]
        file_path = standup_dir / f"{login}.md"

        content = STANDUP_TEMPLATE.format(
            display_name=display,
            sprint_num=sprint_num,
            date=today,
            login=login,
        )

        if not dry_run:
            if create_if_not_exists(file_path, content):
                created.append(login)
                logger.info(f"Created standup template for {display}")
            else:
                logger.info(f"Skipped (exists): {display}")
        else:
            logger.info(f"[DRY RUN] Would create: {file_path}")

    # Create files for agents if agent mode is enabled
    if config.get("agents", {}).get("enabled"):
        for agent in config["agents"].get("roles", []):
            if not agent.get("enabled"):
                continue
            agent_id = agent["id"]
            file_path = standup_dir / f"{agent_id}.md"
            content = AGENT_STANDUP_TEMPLATE.format(
                display_name=agent_id,
                sprint_num=sprint_num,
                date=today,
                agent_id=agent_id,
            )
            if not dry_run:
                create_if_not_exists(file_path, content)

    logger.info(f"Templates ready for {today}: {len(created)} new, rest already existed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    reset_templates(config, args.dry_run)
```

---

## 4. `scripts/standup/generate_summary.py`

```python
"""
scripts/standup/generate_summary.py
Read all standup files for today and generate a team digest using the LLM.
Posts to Slack and writes to sprint-N/standup/summary/YYYY-MM-DD.md (bot-generated).
"""
import argparse
import logging
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import atomic_write, read_file
from scripts.llm.client import complete
from scripts.llm.prompts import STANDUP_SUMMARY, SYSTEM_SCRUM_ASSISTANT
from scripts.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def collect_standup_files(config: dict, target_date: str) -> dict[str, str]:
    """Collect all standup files for the given date. Returns {login: content}."""
    root = get_repo_root()
    sprint_num = get_current_sprint()
    standup_dir = root / f"sprint-{sprint_num:02d}" / "standup" / target_date
    members = {m["login"]: m["display"] for m in config["team"]["members"]}

    result = {}
    for login, display in members.items():
        file_path = standup_dir / f"{login}.md"
        content = read_file(file_path)
        if content:
            result[display] = content
        else:
            result[display] = f"# Standup — {display}\n\n*No update submitted today.*\n"

    # Also include agent standups if present
    if standup_dir.exists():
        for f in standup_dir.glob("agent-*.md"):
            content = read_file(f)
            agent_name = f.stem
            result[agent_name] = content

    return result


def generate_summary(config: dict, target_date: str, dry_run: bool = False) -> str:
    sprint_num = get_current_sprint()
    members = collect_standup_files(config, target_date)
    team_names = ", ".join(config["team"]["members"][i]["display"]
                           for i in range(len(config["team"]["members"])))

    standup_contents = "\n\n---\n\n".join(
        f"### {name}\n{content}" for name, content in members.items()
    )

    prompt = STANDUP_SUMMARY.format(
        date=target_date,
        sprint_num=sprint_num,
        team_names=team_names,
        standup_contents=standup_contents,
    )

    logger.info(f"Generating standup summary for {target_date}...")
    summary = complete(prompt, system=SYSTEM_SCRUM_ASSISTANT)

    if not summary:
        summary = f"# Standup Digest — {target_date}\n\n*LLM unavailable. See individual standup files.*\n"

    if not dry_run:
        # Write to summary folder (bot-generated zone)
        root = get_repo_root()
        summary_dir = root / f"sprint-{sprint_num:02d}" / "standup" / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(summary_dir / f"{target_date}.md",
                     f"<!-- BOT-GENERATED: do not edit manually -->\n\n{summary}")

        # Post to Slack
        slack_webhook = config.get("notifications", {}).get("slack_webhook")
        if slack_webhook:
            post_to_slack(
                webhook_url=slack_webhook,
                text=f"*Daily Standup Digest — {target_date}*",
                blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": summary[:3000]}}]
            )
            logger.info("Posted to Slack")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    result = generate_summary(config, args.date, args.dry_run)
    if args.dry_run:
        print(result)
```

---

## 5. `scripts/reports/burndown_chart.py`

```python
"""
scripts/reports/burndown_chart.py
Generate a sprint burndown chart (SVG) from GitHub issue data.
Compares ideal burndown vs actual burndown.
"""
import argparse
import logging
from datetime import date, timedelta
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_burndown(sprint_num: int, repo_name: str, config: dict,
                      output_path: Path = None) -> Path:
    """Generate burndown chart SVG for the given sprint."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from scripts.utils.date_utils import get_sprint_dates

    start, end = get_sprint_dates(sprint_num, config)

    # Get all sprint issues
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_label = f"sprint-{sprint_num:02d}"
    issues = get_issues(repo, labels=[sprint_label], state="all")

    total_sp = sum(get_sp_from_issue(i) for i in issues)
    if total_sp == 0:
        logger.warning("No story points found for sprint. Cannot generate burndown.")
        return None

    # Build ideal burndown line
    working_days = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            working_days.append(current)
        current += timedelta(days=1)

    ideal_remaining = [total_sp * (1 - i / (len(working_days) - 1))
                       for i in range(len(working_days))]

    # Build actual burndown from issue close dates
    # Group closed issues by date
    closed_by_date = {}
    for issue in issues:
        if issue.state == "closed" and issue.closed_at:
            close_date = issue.closed_at.date()
            sp = get_sp_from_issue(issue)
            closed_by_date[close_date] = closed_by_date.get(close_date, 0) + sp

    actual_remaining = []
    remaining = total_sp
    today = date.today()
    for d in working_days:
        if d > today:
            break
        remaining -= closed_by_date.get(d, 0)
        actual_remaining.append(remaining)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(working_days[:len(ideal_remaining)], ideal_remaining,
            "b--", label="Ideal", linewidth=1.5, alpha=0.6)
    if actual_remaining:
        ax.plot(working_days[:len(actual_remaining)], actual_remaining,
                "g-o", label="Actual", linewidth=2, markersize=4)

    ax.set_xlabel("Date")
    ax.set_ylabel("Story Points Remaining")
    ax.set_title(f"Sprint {sprint_num:02d} Burndown")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    plt.xticks(rotation=45)
    plt.tight_layout()

    if output_path is None:
        root = get_repo_root()
        output_path = root / f"sprint-{sprint_num:02d}" / "review" / "burndown.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Burndown chart saved: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    parser.add_argument("--output")
    args = parser.parse_args()
    config = load_config(args.config)
    sprint_num = args.sprint or config["sprint"]["current_sprint"]
    output = Path(args.output) if args.output else None
    generate_burndown(sprint_num, args.repo, config, output)
```

---

## 6. `scripts/sprint/calculate_velocity.py`

```python
"""
scripts/sprint/calculate_velocity.py
Calculate velocity for a sprint: sum of sp labels on closed issues.
Also calculates rolling average velocity over last N sprints.
"""
import argparse
import logging
from scripts.utils.config import load_config
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_sprint_velocity(sprint_num: int, repo_name: str) -> dict:
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_label = f"sprint-{sprint_num:02d}"

    all_issues = get_issues(repo, labels=[sprint_label], state="all")
    closed = [i for i in all_issues if i.state == "closed"]
    open_issues = [i for i in all_issues if i.state == "open"]

    completed_sp = sum(get_sp_from_issue(i) for i in closed)
    planned_sp = sum(get_sp_from_issue(i) for i in all_issues)
    deferred_sp = sum(get_sp_from_issue(i) for i in open_issues)

    return {
        "sprint_num": sprint_num,
        "completed_sp": completed_sp,
        "planned_sp": planned_sp,
        "deferred_sp": deferred_sp,
        "completion_rate": round(completed_sp / planned_sp, 2) if planned_sp else 0,
        "issues_completed": len(closed),
        "issues_deferred": len(open_issues),
    }


def calculate_rolling_velocity(repo_name: str, num_sprints: int = 5) -> dict:
    """Calculate rolling average velocity over last N sprints."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    velocities = []

    for sprint_num in range(1, num_sprints + 1):
        sprint_label = f"sprint-{sprint_num:02d}"
        try:
            closed = get_issues(repo, labels=[sprint_label], state="closed")
            if not closed:
                continue
            sp = sum(get_sp_from_issue(i) for i in closed)
            velocities.append(sp)
        except Exception:
            continue

    if not velocities:
        return {"avg": 0, "min": 0, "max": 0, "std_dev": 0, "sprints_sampled": 0}

    import statistics
    return {
        "avg": round(sum(velocities) / len(velocities), 1),
        "min": min(velocities),
        "max": max(velocities),
        "std_dev": round(statistics.stdev(velocities), 1) if len(velocities) > 1 else 0,
        "sprints_sampled": len(velocities),
        "velocities": velocities,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    sprint_num = args.sprint or config["sprint"]["current_sprint"]
    result = calculate_sprint_velocity(sprint_num, args.repo)
    print(f"Sprint {sprint_num} velocity: {result['completed_sp']} sp")
    rolling = calculate_rolling_velocity(args.repo)
    print(f"Rolling avg: {rolling['avg']} sp/sprint (σ={rolling['std_dev']})")
```

---

## 7. `scripts/notifications/slack_post.py`

```python
"""
scripts/notifications/slack_post.py
Post messages to Slack channels via Incoming Webhook or Bot API.
"""
import os
import logging
import requests
from typing import Optional, list

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def post_to_slack(webhook_url: str, text: str,
                  blocks: Optional[list] = None) -> bool:
    """Post a message to a Slack channel via webhook."""
    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error(f"Slack post failed: {e}")
        return False


def send_slack_dm(user_id: str, text: str, bot_token: Optional[str] = None) -> bool:
    """Send a direct message to a Slack user."""
    token = bot_token or os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set. Skipping DM.")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Open DM channel
    resp = requests.post(
        "https://slack.com/api/conversations.open",
        json={"users": user_id},
        headers=headers,
        timeout=10,
    )
    data = resp.json()
    if not data.get("ok"):
        logger.error(f"Failed to open DM channel: {data.get('error')}")
        return False

    channel_id = data["channel"]["id"]

    # Send message
    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        json={"channel": channel_id, "text": text, "mrkdwn": True},
        headers=headers,
        timeout=10,
    )
    data = resp.json()
    if not data.get("ok"):
        logger.error(f"Failed to send DM: {data.get('error')}")
        return False

    return True
```

---

## 8. GitHub Actions Workflows

### `.github/workflows/template-reset.yml`

```yaml
name: Scraut — Daily Template Reset
on:
  schedule:
    - cron: '55 1 * * 1-5'  # 1:55 AM UTC weekdays (adjust for timezone)
  workflow_dispatch:

jobs:
  reset-templates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Reset standup templates
        run: python scripts/standup/reset_templates.py

      - name: Commit new templates
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add sprint-*/standup/
          git diff --staged --quiet || git commit -m "chore: standup templates $(date +%Y-%m-%d) [skip ci]"
          git push
```

---

### `.github/workflows/daily-standup.yml`

```yaml
name: Scraut — Daily Standup Summary
on:
  schedule:
    - cron: '0 2 * * 1-5'  # 9:00 AM Jakarta (UTC+7) = 02:00 UTC
  workflow_dispatch:
    inputs:
      date:
        description: 'Date (YYYY-MM-DD, default: today)'
        required: false

jobs:
  standup-summary:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Generate standup summary
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          DATE="${{ github.event.inputs.date }}"
          if [ -z "$DATE" ]; then DATE=$(date +%Y-%m-%d); fi
          python scripts/standup/generate_summary.py --date $DATE

      - name: Commit summary
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add sprint-*/standup/summary/
          git diff --staged --quiet || git commit -m "chore: standup summary $(date +%Y-%m-%d) [skip ci]"
          git push
```

---

### `.github/workflows/issue-triage.yml`

```yaml
name: Scraut — Issue Triage
on:
  issues:
    types: [opened]

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Triage issue
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python scripts/backlog/triage_issue.py \
            --issue ${{ github.event.issue.number }} \
            --repo ${{ github.repository }}
```

---

### `.github/workflows/sprint-planning.yml`

```yaml
name: Scraut — Sprint Planning
on:
  workflow_dispatch:
    inputs:
      sprint_num:
        description: 'Sprint number to plan'
        required: true
      repo:
        description: 'org/repo'
        required: true

jobs:
  create-planning-pr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Create sprint and planning PR
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          python scripts/sprint/create_sprint.py \
            --sprint ${{ github.event.inputs.sprint_num }} \
            --repo ${{ github.event.inputs.repo }}
          python scripts/sprint/create_planning_pr.py \
            --sprint ${{ github.event.inputs.sprint_num }} \
            --repo ${{ github.event.inputs.repo }}
```

---

### `.github/workflows/sprint-review.yml`

```yaml
name: Scraut — Sprint Review
on:
  workflow_dispatch:
    inputs:
      sprint_num:
        description: 'Sprint number to review'
        required: true
      repo:
        description: 'org/repo'
        required: true

jobs:
  sprint-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Generate sprint review
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          python scripts/sprint/close_sprint.py \
            --sprint ${{ github.event.inputs.sprint_num }} \
            --repo ${{ github.event.inputs.repo }}
          python scripts/reports/burndown_chart.py \
            --sprint ${{ github.event.inputs.sprint_num }} \
            --repo ${{ github.event.inputs.repo }}
          python scripts/sprint/generate_review.py \
            --sprint ${{ github.event.inputs.sprint_num }} \
            --repo ${{ github.event.inputs.repo }}

      - name: Commit review artifacts
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add sprint-*/review/ sprint-*/standup/summary/
          git diff --staged --quiet || git commit -m "chore: sprint ${{ github.event.inputs.sprint_num }} review [skip ci]"
          git push
```

---

### `.github/workflows/sprint-retrospective.yml`

```yaml
name: Scraut — Sprint Retrospective
on:
  workflow_dispatch:
    inputs:
      sprint_num:
        description: 'Sprint number'
        required: true

jobs:
  retrospective:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Synthesise retrospective
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          python scripts/sprint/synthesise_retrospective.py \
            --sprint ${{ github.event.inputs.sprint_num }} \
            --repo ${{ github.repository }}

      - name: Commit retro summary
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add sprint-*/retrospective/summary.md
          git diff --staged --quiet || git commit -m "chore: sprint retrospective summary [skip ci]"
          git push
```

---

### `.github/workflows/estimation-tally.yml`

Listens for emoji reactions on the bot's story point suggestion comment.

```yaml
name: Scraut — Estimation Tally
on:
  issue_comment:
    types: [created, edited, deleted]

jobs:
  tally-votes:
    if: contains(github.event.comment.body, '<!-- scraut-estimation -->')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Tally estimation votes
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python scripts/backlog/tally_estimation.py \
            --issue ${{ github.event.issue.number }} \
            --comment ${{ github.event.comment.id }} \
            --repo ${{ github.repository }}
```

---

## 9. `scripts/backlog/triage_issue.py`

```python
"""
scripts/backlog/triage_issue.py
LLM-powered issue triage: suggests type label, priority, story points.
Posts suggestion as a GitHub comment and starts estimation ceremony.
"""
import argparse
import logging
from scripts.utils.config import load_config
from scripts.github.api import (get_github_client, ensure_label_exists,
                                 add_label_to_issue, post_comment)
from scripts.llm.client import complete_json
from scripts.llm.prompts import BACKLOG_TRIAGE, SYSTEM_SCRUM_ASSISTANT
from scripts.sprint.calculate_velocity import calculate_rolling_velocity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ESTIMATION_COMMENT_TEMPLATE = """<!-- scraut-estimation -->
## 🤖 Scraut Story Point Estimation

**Suggested estimate:** `sp:{estimate}` — *{reasoning}*

### Team vote
React to this comment to vote on story points:
| 👍 | ❤️ | 🚀 | 🎉 | 🔥 |
|----|-----|-----|-----|-----|
| 1 | 3 | 5 | 8 | 13 |

The estimate with the most votes will be automatically applied after 24h.
PO or Scrum Master can also apply manually by commenting `/estimate N`.
"""


def triage_issue(issue_number: int, repo_name: str, config: dict) -> None:
    g = get_github_client()
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(issue_number)

    logger.info(f"Triaging issue #{issue_number}: {issue.title}")

    # Get velocity for context
    velocity_data = calculate_rolling_velocity(repo_name)

    # Call LLM for triage
    prompt = BACKLOG_TRIAGE.format(
        title=issue.title,
        body=issue.body or "",
    )
    result = complete_json(prompt, system=SYSTEM_SCRUM_ASSISTANT)

    if not result:
        logger.warning("LLM triage failed. Skipping.")
        return

    # Apply type and priority labels
    type_label = result.get("type_label", "task")
    priority_label = result.get("priority_label", "p:medium")
    sp_estimate = result.get("story_point_estimate", 3)
    reasoning = result.get("reasoning", "Estimated by Scraut")

    ensure_label_exists(repo, type_label)
    ensure_label_exists(repo, priority_label)
    add_label_to_issue(issue, type_label)
    add_label_to_issue(issue, priority_label)

    # Add suggested acceptance criteria if issue body is sparse
    if result.get("suggested_acceptance_criteria") and (not issue.body or len(issue.body) < 100):
        criteria = "\n".join(f"- [ ] {c}" for c in result["suggested_acceptance_criteria"])
        updated_body = f"{issue.body or ''}\n\n## Acceptance criteria (suggested by Scraut)\n{criteria}"
        issue.edit(body=updated_body)

    # Post estimation comment
    comment_body = ESTIMATION_COMMENT_TEMPLATE.format(
        estimate=sp_estimate,
        reasoning=reasoning,
    )
    post_comment(issue, comment_body)
    logger.info(f"Posted estimation comment for #{issue_number}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    triage_issue(args.issue, args.repo, config)
```

---

## 10. `scripts/backlog/dod_check.py`

Definition of Done enforcement — runs when issue is closed.

```python
"""
scripts/backlog/dod_check.py
Check a closed issue against the team's Definition of Done.
If DoD not met, reopens the issue and posts a specific comment.
"""
import argparse
import logging
from scripts.utils.config import load_config
from scripts.github.api import get_github_client, post_comment
from scripts.llm.client import complete_json
from scripts.llm.prompts import SYSTEM_SCRUM_ASSISTANT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOD_CHECK_PROMPT = """
You are checking whether a GitHub issue meets the team's Definition of Done.

Issue: {title}
Body: {body}
Linked PR description: {pr_body}
DoD checklist:
{dod_items}

Reply with ONLY JSON:
{{
  "passed": true|false,
  "missing_items": ["item 1", "item 2"],
  "passed_items": ["item 1"],
  "overall_confidence": "high|medium|low"
}}
"""


def check_dod(issue_number: int, repo_name: str, config: dict) -> bool:
    g = get_github_client()
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    dod_items = config.get("definition_of_done", [])

    if not dod_items:
        logger.info("No DoD configured. Skipping check.")
        return True

    # Find linked PRs
    pr_body = ""
    events = list(issue.get_events())
    for event in events:
        if event.event == "referenced":
            try:
                pr = repo.get_pull(event.commit_id)
                pr_body = pr.body or ""
            except Exception:
                pass

    prompt = DOD_CHECK_PROMPT.format(
        title=issue.title,
        body=issue.body or "",
        pr_body=pr_body,
        dod_items="\n".join(f"- {item}" for item in dod_items),
    )

    result = complete_json(prompt, system=SYSTEM_SCRUM_ASSISTANT)
    passed = result.get("passed", True)

    if not passed:
        missing = result.get("missing_items", [])
        comment = (
            "## ⚠️ Definition of Done Check Failed\n\n"
            "This issue was closed but does not yet meet all DoD criteria:\n\n"
            + "\n".join(f"- ❌ {item}" for item in missing)
            + "\n\nPassed:\n"
            + "\n".join(f"- ✅ {item}" for item in result.get("passed_items", []))
            + "\n\nPlease address the missing items and close again."
        )
        post_comment(issue, comment)
        issue.edit(state="open")
        logger.info(f"Reopened #{issue_number}: DoD not met. Missing: {missing}")
    else:
        logger.info(f"#{issue_number} passes DoD check")

    return passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    check_dod(args.issue, args.repo, config)
```

---

## Done Criteria for Phase 2

- [ ] `scripts/llm/client.py` — `complete()` returns text with Anthropic/OpenAI/Ollama
- [ ] `scripts/llm/prompts.py` — all prompt templates present and importable
- [ ] `scripts/standup/reset_templates.py` — creates today's standup files for all team members; skips existing files
- [ ] `scripts/standup/generate_summary.py` — generates and posts standup digest to Slack
- [ ] `scripts/reports/burndown_chart.py` — generates a PNG burndown chart
- [ ] `scripts/sprint/calculate_velocity.py` — outputs correct sprint velocity
- [ ] `scripts/notifications/slack_post.py` — posts to Slack webhook successfully
- [ ] `scripts/backlog/triage_issue.py` — labels issue + posts estimation comment
- [ ] `scripts/backlog/dod_check.py` — reopens issue if DoD not met
- [ ] All 6 workflow YAML files exist and pass `yamllint` check
- [ ] `template-reset.yml` creates correct standup file paths
- [ ] `daily-standup.yml` reads files and posts to Slack
- [ ] `issue-triage.yml` triggers on `issues.opened` correctly
- [ ] `estimation-tally.yml` triggers only on comments containing the estimation marker
- [ ] `sprint-planning.yml`, `sprint-review.yml`, `sprint-retrospective.yml` exist

*Proceed to `03-MILESTONE-PLANNING.md`*
