"""
scrum/backlog/pr_knowledge_extract.py
When a PR is merged, extract "what we learned" from the PR description
and review comments. Append to workspace/knowledge/YYYY-MM.md.
Builds institutional memory from code reviews over time.
"""
import argparse
import logging
from datetime import date
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root
from scraut.platform.utils.file_utils import create_if_not_exists
from scraut.platform.github.api import get_github_client
from scraut.platform.llm.client import complete
from scraut.platform.llm.prompts import SYSTEM_SCRUM_ASSISTANT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """
You are extracting institutional knowledge from a merged GitHub PR.

## PR title: {title}
## PR description: {body}
## Review comments (key ones): {review_comments}

## Instructions:
Extract any REUSABLE insights from this PR. Only include if genuinely useful:
- New patterns or approaches discovered
- Pitfalls or gotchas to avoid
- Architectural decisions made and why
- Performance or security considerations
- Libraries or tools evaluated

If nothing notable, reply with exactly: SKIP

Otherwise reply with a concise bullet point (1-3 sentences max).
Do NOT include: PR-specific details, author names, issue numbers.
Write as a generic lesson, not "in this PR we..."
"""


def extract_knowledge(pr_number: int, repo_name: str, config: dict) -> None:
    g = get_github_client()
    repo = g.get_repo(repo_name)

    try:
        pr = repo.get_pull(pr_number)
    except Exception as e:
        logger.error(f"Could not access PR #{pr_number}: {e}")
        return

    if not pr.merged:
        logger.info(f"PR #{pr_number} not merged. Skipping.")
        return

    review_comments = []
    try:
        for comment in list(pr.get_review_comments())[:10]:
            if len(comment.body or "") > 20:
                review_comments.append(comment.body[:200])
    except Exception:
        pass

    review_text = "\n".join(f"- {c}" for c in review_comments) or "No review comments"

    insight = complete(
        EXTRACT_PROMPT.format(
            title=pr.title,
            body=(pr.body or "")[:600],
            review_comments=review_text,
        ),
        system=SYSTEM_SCRUM_ASSISTANT,
    )

    if not insight or insight.strip().upper() == "SKIP":
        logger.info(f"PR #{pr_number}: no notable insight to extract")
        return

    root = get_workspace_root()
    today = date.today()
    knowledge_file = root / "knowledge" / f"{today.year}-{today.month:02d}.md"
    knowledge_file.parent.mkdir(exist_ok=True)

    header = (
        f"<!-- BOT-GENERATED: extracted from merged PRs -->\n"
        f"# Knowledge — {today.strftime('%B %Y')}\n\n"
    )
    create_if_not_exists(knowledge_file, header)

    new_entry = f"- **{today.isoformat()}** (from PR #{pr_number}): {insight.strip()}\n"
    with open(knowledge_file, "a", encoding="utf-8") as f:
        f.write(new_entry)
    logger.info(f"Knowledge extracted from PR #{pr_number}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    extract_knowledge(args.pr, args.repo, config)
