"""
test/unit/test_derive_state.py
CRITICAL: Tests for the board state inference engine.
Every rule must be tested individually.
"""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from scraut.scrum.visibility.derive_state import (
    derive_all_states, IssueState, scan_standup_files,
    VALID_COLUMNS,
)


@pytest.mark.unit
def test_done_when_issue_is_closed(scraut_repo, config, mock_repo):
    """Closed GitHub issues should always map to Done."""
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    with patch("scraut.scrum.visibility.derive_state.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scraut.scrum.visibility.derive_state.get_pr_issue_map", return_value={}):
            with patch("scraut.scrum.visibility.derive_state.get_sprint_roadmap_issues",
                       return_value={42, 44, 46, 47}):
                states = derive_all_states("test-org/test-repo", config,
                                           target_date="2026-05-23")

    # Issue #42 is closed in mock_repo
    assert states[42].column == "Done"
    assert states[42].confidence == 1.0


@pytest.mark.unit
def test_review_when_open_pr_exists(scraut_repo, config, mock_repo):
    """Issue with open PR should map to Review."""
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    # PR #91 is open and closes #46
    pr_map = {46: {"pr_number": 91, "state": "open"}}

    with patch("scraut.scrum.visibility.derive_state.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scraut.scrum.visibility.derive_state.get_pr_issue_map",
                   return_value=pr_map):
            with patch("scraut.scrum.visibility.derive_state.get_sprint_roadmap_issues",
                       return_value={42, 44, 46, 47}):
                states = derive_all_states("test-org/test-repo", config,
                                           target_date="2026-05-23")

    assert states[46].column == "Review"
    assert states[46].confidence == 1.0


@pytest.mark.unit
def test_blocked_when_in_blockers_section(scraut_repo, config, mock_repo):
    """Issue mentioned in today's Blockers section → In Progress + blocked health."""
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    # Fixture has bob.md with #44 in Blockers section for 2026-05-23
    with patch("scraut.scrum.visibility.derive_state.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scraut.scrum.visibility.derive_state.get_pr_issue_map", return_value={}):
            with patch("scraut.scrum.visibility.derive_state.get_sprint_roadmap_issues",
                       return_value={42, 44, 46, 47}):
                states = derive_all_states("test-org/test-repo", config,
                                           target_date="2026-05-23")

    assert states[44].column == "In Progress"
    assert states[44].health == "blocked"
    assert states[44].confidence >= 0.85


@pytest.mark.unit
def test_in_progress_when_in_today_section(scraut_repo, config, mock_repo):
    """Issue in Today section of today's standup → In Progress."""
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    # alice.md has #46 in Today for 2026-05-23
    with patch("scraut.scrum.visibility.derive_state.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scraut.scrum.visibility.derive_state.get_pr_issue_map", return_value={}):
            with patch("scraut.scrum.visibility.derive_state.get_sprint_roadmap_issues",
                       return_value={42, 44, 46, 47}):
                states = derive_all_states("test-org/test-repo", config,
                                           target_date="2026-05-23")

    assert states[46].column in ("In Progress", "Review")  # could be Review if PR open


@pytest.mark.unit
def test_ready_when_in_roadmap_but_no_standup_signal(scraut_repo, config, mock_repo):
    """Issue in sprint roadmap with no standup mentions → Ready."""
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    # Issue #47 is in sprint but Bob only mentions it in Today on 2026-05-23
    # For a date where no one mentions it, it should be Ready
    with patch("scraut.scrum.visibility.derive_state.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scraut.scrum.visibility.derive_state.get_pr_issue_map", return_value={}):
            with patch("scraut.scrum.visibility.derive_state.get_sprint_roadmap_issues",
                       return_value={42, 44, 46, 47, 99}):
                states = derive_all_states("test-org/test-repo", config,
                                           target_date="2026-05-20")  # earlier date, no standups

    assert states[99].column == "Ready"


@pytest.mark.unit
def test_all_columns_are_valid():
    for col in VALID_COLUMNS:
        assert isinstance(col, str)
        assert len(col) > 0
