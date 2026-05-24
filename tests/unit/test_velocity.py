"""tests/unit/test_velocity.py"""
import pytest
from unittest.mock import patch
from scripts.sprint.calculate_velocity import (
    calculate_sprint_velocity, calculate_rolling_velocity,
)
from tests.mocks.github_mocks import MockRepository, MockIssue


@pytest.mark.unit
def test_calculate_sprint_velocity_counts_closed_sp(mock_repo):
    """Velocity should sum SP of closed issues with sprint label."""
    # Issue #42 is closed, sp:5. Issue #44 is open, sp:3. Issue #46 is open, sp:5.
    with patch("scripts.sprint.calculate_velocity.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        result = calculate_sprint_velocity(1, "test-org/test-repo")

    assert result["completed_sp"] == 5  # only issue #42 is closed with sp:5
    assert result["planned_sp"] == 21   # 5+3+5+8
    assert result["completion_rate"] == pytest.approx(5 / 21, abs=0.01)


@pytest.mark.unit
def test_calculate_rolling_velocity_handles_no_sprints():
    with patch("scripts.sprint.calculate_velocity.get_github_client") as mock_g:
        empty_repo = MockRepository()
        mock_g.return_value.get_repo.return_value = empty_repo
        result = calculate_rolling_velocity("test-org/test-repo", num_sprints=5)

    assert result["avg"] == 0
    assert result["sprints_sampled"] == 0
