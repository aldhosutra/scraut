"""
scrum/backlog/tally_estimation.py
Tally emoji reaction votes on story point estimation comments.
Called by estimation-tally.yml when a reaction is added/removed on
a Scraut estimation comment.

Emoji → story point mapping (team convention):
  👍 = 1 sp
  ❤️  = 3 sp
  🚀 = 5 sp
  🎉 = 8 sp
  🔥 = 13 sp

After 24h OR when all team members have voted:
  → Apply the winning estimate as sp:N label on the issue
  → Post result comment
"""
import argparse
import logging
from datetime import datetime, timezone, timedelta
from scraut.platform.utils.config import load_config, get_team_logins
from scraut.platform.github.api import (get_github_client, set_sp_on_issue,
                                 post_comment, ensure_label_exists)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMOJI_TO_SP = {
    "+1":      1,   # 👍
    "heart":   3,   # ❤️
    "rocket":  5,   # 🚀
    "tada":    8,   # 🎉
    "fire":   13,   # 🔥
}

RESULT_COMMENT = """<!-- scraut-estimation-result -->
## 📊 Story Point Estimation Result

| Points | Votes |
|--------|-------|
{vote_table}

**Winning estimate: `sp:{winner}`** ({winner_votes} vote(s))

Applied automatically. To override: comment `/estimate N` where N ∈ {{1,2,3,5,8,13}}.
"""

TALLY_IN_PROGRESS_COMMENT = """<!-- scraut-estimation-progress -->
## 🗳️ Estimation votes so far ({voted}/{total} team members)

| Points | Votes |
|--------|-------|
{vote_table}

Voting closes when all team members vote OR 24h after the estimation comment was posted.
"""


def is_estimation_comment(comment_body: str) -> bool:
    return "<!-- scraut-estimation -->" in (comment_body or "")


def count_votes(comment_id: int, repo) -> dict:
    """Count emoji reactions on a comment by story point value."""
    votes = {}
    try:
        reactions = list(repo.get_comment(comment_id).get_reactions())
        team_logins = get_team_logins()
        for reaction in reactions:
            if reaction.user.login not in team_logins:
                continue
            sp = EMOJI_TO_SP.get(reaction.content)
            if sp:
                votes[sp] = votes.get(sp, 0) + 1
    except Exception as e:
        logger.error(f"Failed to count reactions: {e}")
    return votes


def format_vote_table(votes: dict) -> str:
    all_sp = [1, 3, 5, 8, 13]
    rows = [f"| sp:{sp} | {'⬛' * votes.get(sp, 0)} {votes.get(sp, 0)} |"
            for sp in all_sp if votes.get(sp, 0) > 0]
    return "\n".join(rows) if rows else "| — | No votes yet |"


def determine_winner(votes: dict):
    """Return winning SP value (most votes), None if no votes."""
    if not votes:
        return None
    return max(votes.items(), key=lambda x: x[1])[0]


def should_finalize(comment, team_logins: list, votes: dict) -> bool:
    """Decide whether to finalize the estimate or keep voting open."""
    unique_voters = sum(votes.values())
    if unique_voters >= len(team_logins):
        return True

    age = datetime.now(tz=timezone.utc) - comment.created_at.replace(tzinfo=timezone.utc)
    if age > timedelta(hours=24):
        return True

    return False


def tally_estimation(issue_number: int, comment_id: int,
                     repo_name: str, config: dict) -> None:
    g = get_github_client()
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    team_logins = get_team_logins()

    estimation_comment = None
    for comment in issue.get_comments():
        if is_estimation_comment(comment.body or ""):
            estimation_comment = comment
            break

    if not estimation_comment:
        logger.warning(f"No estimation comment found on #{issue_number}")
        return

    votes = count_votes(estimation_comment.id, repo)
    total_team = len(team_logins)
    voted_count = sum(votes.values())

    if should_finalize(estimation_comment, team_logins, votes):
        winner = determine_winner(votes)
        if winner:
            set_sp_on_issue(repo, issue, winner)

            for comment in issue.get_comments():
                if "<!-- scraut-estimation-progress -->" in (comment.body or ""):
                    comment.delete()

            result_body = RESULT_COMMENT.format(
                vote_table=format_vote_table(votes),
                winner=winner,
                winner_votes=votes.get(winner, 0),
            )
            post_comment(issue, result_body)
            logger.info(f"#{issue_number}: estimated at sp:{winner} ({votes})")
        else:
            post_comment(issue,
                f"⏱️ Estimation vote closed with no votes. "
                f"Using Scraut's LLM suggestion. Comment `/estimate N` to override."
            )
    else:
        for comment in issue.get_comments():
            if "<!-- scraut-estimation-progress -->" in (comment.body or ""):
                comment.delete()
                break

        if votes:
            progress_body = TALLY_IN_PROGRESS_COMMENT.format(
                voted=voted_count,
                total=total_team,
                vote_table=format_vote_table(votes),
            )
            post_comment(issue, progress_body)

    logger.info(f"Tally complete for #{issue_number}: {votes}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--comment", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    tally_estimation(args.issue, args.comment, args.repo, config)
