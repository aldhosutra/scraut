"""
scrum/backlog/prioritize_backlog.py
LLM-powered backlog prioritization: rank unlabelled/unpointed issues
by value-to-effort ratio against the active OKR or milestone goal.
Called during backlog grooming ceremony.
"""
import argparse
import json
import logging
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_current_sprint
from scraut.platform.utils.file_utils import read_file, extract_section
from scraut.platform.github.api import (get_github_client, get_issues, get_sp_from_issue,
                                  add_label_to_issue, post_comment, ensure_label_exists)
from scraut.platform.llm.client import complete_json
from scraut.platform.llm.prompts import SYSTEM_SCRUM_ASSISTANT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PRIORITIZE_PROMPT = """
You are prioritising a product backlog for a Scrum team.

## Active milestone goal:
{milestone_goal}

## Current OKRs:
{okr_content}

## Issues to prioritise (no priority label yet):
{issues_json}

## Instructions:
Rank these issues by value/effort ratio considering the goal and OKRs.
Reply with ONLY JSON:
{{
  "ranked": [
    {{
      "number": N,
      "suggested_priority": "p:high|p:medium|p:low",
      "reasoning": "one sentence",
      "okr_alignment": "high|medium|low|none"
    }}
  ]
}}
"""


def read_active_milestone_goal(config: dict) -> str:
    root = get_workspace_root()
    milestones = list((root / "milestones").glob("*/milestone.md"))
    if not milestones:
        return "No active milestone"
    content = read_file(sorted(milestones)[-1])
    return extract_section(content, "Goal") or "No goal specified"


def read_current_okr(config: dict) -> str:
    root = get_workspace_root()
    okrs = sorted((root / "okr").glob("*.md"))
    if not okrs:
        return "No OKRs defined"
    return read_file(okrs[-1])[:500] or "No OKR content"


def prioritize_backlog(repo_name: str, config: dict, max_issues: int = 20) -> None:
    g = get_github_client()
    repo = g.get_repo(repo_name)

    all_open = get_issues(repo, state="open")
    to_prioritize = [
        i for i in all_open
        if not any(l.name.startswith("p:") for l in i.labels)
        and not any(l.name.startswith("sprint-") for l in i.labels)
    ][:max_issues]

    if not to_prioritize:
        logger.info("All open issues already have priority labels.")
        return

    issues_json = json.dumps([
        {"number": i.number, "title": i.title, "body": (i.body or "")[:200],
         "labels": [l.name for l in i.labels]}
        for i in to_prioritize
    ], indent=2)

    milestone_goal = read_active_milestone_goal(config)
    okr_content = read_current_okr(config)

    result = complete_json(
        PRIORITIZE_PROMPT.format(
            milestone_goal=milestone_goal,
            okr_content=okr_content,
            issues_json=issues_json,
        ),
        system=SYSTEM_SCRUM_ASSISTANT,
    )

    if not result or "ranked" not in result:
        logger.warning("LLM prioritization failed.")
        return

    for item in result["ranked"]:
        num = item.get("number")
        priority = item.get("suggested_priority", "p:medium")
        reasoning = item.get("reasoning", "")

        try:
            issue = repo.get_issue(num)
            ensure_label_exists(repo, priority)
            add_label_to_issue(issue, priority)
            post_comment(issue,
                f"🤖 **Suggested priority: `{priority}`** — {reasoning}\n"
                f"OKR alignment: {item.get('okr_alignment', 'unknown')}\n"
                f"_This is a suggestion — team can override by changing the label._"
            )
            logger.info(f"Prioritised #{num}: {priority}")
        except Exception as e:
            logger.error(f"Failed to prioritise #{num}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    parser.add_argument("--max-issues", type=int, default=20)
    args = parser.parse_args()
    config = load_config(args.config)
    prioritize_backlog(args.repo, config, args.max_issues)
