"""
scrum/backlog/triage_issue.py
LLM-powered issue triage: suggests type label, priority, story points.
Posts suggestion as a GitHub comment and starts estimation ceremony.
"""
import argparse
import logging
from scraut.platform.utils.config import load_config
from scraut.platform.github.api import (get_github_client, ensure_label_exists,
                                 add_label_to_issue, post_comment)
from scraut.platform.llm.client import complete_json
from scraut.platform.llm.prompts import BACKLOG_TRIAGE, SYSTEM_SCRUM_ASSISTANT
from scraut.scrum.sprint.calculate_velocity import calculate_rolling_velocity

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

    velocity_data = calculate_rolling_velocity(repo_name)

    prompt = BACKLOG_TRIAGE.format(
        title=issue.title,
        body=issue.body or "",
    )
    result = complete_json(prompt, system=SYSTEM_SCRUM_ASSISTANT, use_small_model=True)

    if not result:
        logger.warning("LLM triage failed. Skipping.")
        return

    type_label = result.get("type_label", "task")
    priority_label = result.get("priority_label", "p:medium")
    sp_estimate = result.get("story_point_estimate", 3)
    reasoning = result.get("reasoning", "Estimated by Scraut")

    ensure_label_exists(repo, type_label)
    ensure_label_exists(repo, priority_label)
    add_label_to_issue(issue, type_label)
    add_label_to_issue(issue, priority_label)

    if result.get("suggested_acceptance_criteria") and (not issue.body or len(issue.body) < 100):
        criteria = "\n".join(f"- [ ] {c}" for c in result["suggested_acceptance_criteria"])
        updated_body = f"{issue.body or ''}\n\n## Acceptance criteria (suggested by Scraut)\n{criteria}"
        issue.edit(body=updated_body)

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
