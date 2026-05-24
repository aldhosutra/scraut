"""tests/unit/test_tally_estimation.py"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from scripts.backlog.tally_estimation import (
    EMOJI_TO_SP, count_votes, determine_winner,
    should_finalize, format_vote_table,
)
from tests.mocks.github_mocks import MockIssue, MockComment


@pytest.mark.unit
def test_emoji_to_sp_mapping():
    """Verify the emoji→SP mapping is correct."""
    assert EMOJI_TO_SP["+1"] == 1      # 👍
    assert EMOJI_TO_SP["heart"] == 3    # ❤️
    assert EMOJI_TO_SP["rocket"] == 5   # 🚀
    assert EMOJI_TO_SP["tada"] == 8     # 🎉
    assert EMOJI_TO_SP["fire"] == 13    # 🔥


@pytest.mark.unit
def test_determine_winner_returns_most_voted():
    votes = {1: 2, 3: 3, 5: 1}
    assert determine_winner(votes) == 3


@pytest.mark.unit
def test_determine_winner_returns_none_for_no_votes():
    assert determine_winner({}) is None


@pytest.mark.unit
def test_determine_winner_handles_single_vote():
    votes = {5: 1}
    assert determine_winner(votes) == 5


@pytest.mark.unit
def test_determine_winner_tie_returns_one_of_the_tied():
    """When tied, winner is one of the tied values (higher vote count wins)."""
    votes = {3: 2, 5: 2}
    winner = determine_winner(votes)
    assert winner in (3, 5)


@pytest.mark.unit
def test_should_finalize_when_all_team_voted():
    """Should finalize when every team member has voted."""
    team = ["alice", "bob", "charlie"]
    # 3 votes in total (one each) = all voted
    votes = {1: 1, 3: 1, 5: 1}  # 3 total votes
    comment = MagicMock()
    comment.created_at = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    assert should_finalize(comment, team, votes) is True


@pytest.mark.unit
def test_should_finalize_after_24h():
    """Should finalize after 24h even with partial votes."""
    from freezegun import freeze_time
    team = ["alice", "bob", "charlie"]
    votes = {5: 1}  # Only 1 vote

    old_time = datetime(2026, 5, 22, 9, 0, 0, tzinfo=timezone.utc)
    comment = MagicMock()
    comment.created_at = old_time

    # Freeze time to 25h after comment was created
    with freeze_time("2026-05-23 10:00:00"):
        result = should_finalize(comment, team, votes)
    assert result is True


@pytest.mark.unit
def test_should_not_finalize_early_with_partial_votes():
    """Should NOT finalize when partial votes and <24h."""
    from freezegun import freeze_time
    team = ["alice", "bob", "charlie"]
    votes = {5: 1}  # Only 1 of 3 voted

    comment = MagicMock()
    comment.created_at = datetime(2026, 5, 23, 9, 0, 0, tzinfo=timezone.utc)

    with freeze_time("2026-05-23 10:00:00"):  # only 1h later
        result = should_finalize(comment, team, votes)
    assert result is False


@pytest.mark.unit
def test_format_vote_table_shows_non_zero_votes():
    votes = {5: 3, 1: 1}
    table = format_vote_table(votes)
    assert "sp:5" in table
    assert "sp:1" in table
    assert "sp:3" not in table  # no votes for 3


@pytest.mark.unit
def test_format_vote_table_empty():
    table = format_vote_table({})
    assert "No votes" in table
