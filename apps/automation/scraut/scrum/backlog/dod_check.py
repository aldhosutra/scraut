"""
scrum/backlog/dod_check.py
Check a closed issue against the team's Definition of Done.
If DoD not met, reopens the issue and posts a specific comment.
"""
import argparse
import logging
from scraut.platform.utils.config import load_config
from scraut.platform.github.api import get_github_client, post_comment
from scraut.platform.llm.client import complete_json
from scraut.platform.llm.prompts import SYSTEM_SCRUM_ASSISTANT

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
  "passed": true,
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
