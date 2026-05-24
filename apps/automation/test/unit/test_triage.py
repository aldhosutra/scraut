"""test/unit/test_triage.py"""
import pytest
from unittest.mock import patch
from test.mocks.github_mocks import MockRepository, MockIssue
from test.mocks.llm_mocks import TRIAGE_RESPONSE


@pytest.mark.unit
def test_triage_applies_labels(scraut_repo, config):
    """Triage should apply type and priority labels to the issue."""
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    repo = MockRepository()
    issue = MockIssue(99, "Add user profile endpoint", body="User needs to view their profile.")
    repo.add_issue(issue)
    # Pre-create labels so ensure_label_exists doesn't fail
    repo.create_label("story")
    repo.create_label("p:medium")

    with patch("scraut.scrum.backlog.triage_issue.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = repo
        with patch("scraut.scrum.backlog.triage_issue.complete_json", return_value=TRIAGE_RESPONSE):
            with patch("scraut.scrum.backlog.triage_issue.calculate_rolling_velocity",
                       return_value={"avg": 26.0, "sprints_sampled": 3, "std_dev": 2.0}):
                from scraut.scrum.backlog.triage_issue import triage_issue
                triage_issue(99, "test-org/test-repo", config)

    label_names = [l.name for l in issue.labels]
    assert "story" in label_names
    assert "p:medium" in label_names


@pytest.mark.unit
def test_triage_posts_estimation_comment(scraut_repo, config):
    """Triage should post an estimation comment with the LLM suggestion."""
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    repo = MockRepository()
    issue = MockIssue(100, "New feature request", body="Some description.")
    repo.add_issue(issue)
    repo.create_label("story")
    repo.create_label("p:medium")

    with patch("scraut.scrum.backlog.triage_issue.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = repo
        with patch("scraut.scrum.backlog.triage_issue.complete_json", return_value=TRIAGE_RESPONSE):
            with patch("scraut.scrum.backlog.triage_issue.calculate_rolling_velocity",
                       return_value={"avg": 26.0, "sprints_sampled": 3, "std_dev": 2.0}):
                from scraut.scrum.backlog.triage_issue import triage_issue
                triage_issue(100, "test-org/test-repo", config)

    # Check that a comment was posted
    assert len(issue._comments) >= 1
    comment_bodies = [c.body for c in issue._comments]
    assert any("scraut-estimation" in body for body in comment_bodies)
