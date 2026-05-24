"""
scripts/backlog/tally_estimation.py
Tally emoji reaction votes on the scraut-estimation comment.
Applies the winning story point label after 24h or when triggered.

Emoji-to-point mapping:
  👍 (+1) = 1 sp
  ❤️  (heart) = 3 sp
  🚀 (rocket) = 5 sp
  🎉 (hooray) = 8 sp
  🔥 (fire) = 13 sp
"""
import argparse
import logging
from scripts.utils.config import load_config
from scripts.github.api import get_github_client, set_sp_on_issue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REACTION_TO_SP = {
    "+1": 1,
    "heart": 3,
    "rocket": 5,
    "hooray": 8,
    "fire": 13,
}


def tally_estimation(issue_number: int, comment_id: int, repo_name: str) -> None:
    g = get_github_client()
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(issue_number)

    try:
        comment = repo.get_issue_comment(comment_id)
    except Exception as e:
        logger.error(f"Could not fetch comment {comment_id}: {e}")
        return

    if "<!-- scraut-estimation -->" not in comment.body:
        logger.info("Comment is not a scraut-estimation comment. Skipping.")
        return

    reactions = list(comment.get_reactions())
    vote_counts = {}
    for reaction in reactions:
        content = reaction.content
        sp = REACTION_TO_SP.get(content)
        if sp:
            vote_counts[sp] = vote_counts.get(sp, 0) + 1

    if not vote_counts:
        logger.info(f"No estimation votes on comment {comment_id} yet.")
        return

    winning_sp = max(vote_counts, key=vote_counts.get)
    logger.info(f"Vote tally for #{issue_number}: {vote_counts}. Winner: sp:{winning_sp}")

    set_sp_on_issue(repo, issue, winning_sp)
    logger.info(f"Applied sp:{winning_sp} to #{issue_number}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--comment", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    tally_estimation(args.issue, args.comment, args.repo)
