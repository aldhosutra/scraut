"""
test/integration/test_milestone_flow.py
End-to-end: milestone.md → decompose → planning session → answers → roadmap.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from test.mocks.github_mocks import MockRepository
from test.mocks.llm_mocks import DECOMPOSITION_RESPONSE


@pytest.mark.integration
def test_milestone_decompose_creates_files(scraut_repo, config):
    """Committing milestone.md should produce breakdown.json and breakdown.md."""
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    milestone_path = scraut_repo / "milestones" / "m01-auth" / "milestone.md"

    mock_repo = MockRepository()
    with patch("scraut.scrum.milestone.decompose.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scraut.scrum.milestone.decompose.complete_json",
                   return_value=DECOMPOSITION_RESPONSE):
            with patch("scraut.scrum.milestone.decompose.calculate_rolling_velocity",
                       return_value={"avg": 26.0, "std_dev": 2.0, "sprints_sampled": 4}):
                from scraut.scrum.milestone.decompose import decompose_milestone
                decompose_milestone(str(milestone_path), "test-org/test-repo", config)

    # Verify files were created
    milestone_dir = scraut_repo / ".scraut" / "milestones" / "m01-auth"
    assert (milestone_dir / "breakdown.json").exists()
    assert (milestone_dir / "breakdown.md").exists()
    assert (milestone_dir / "planning-session.md").exists()

    # Verify breakdown.json has correct structure
    breakdown = json.loads((milestone_dir / "breakdown.json").read_text())
    assert "epics" in breakdown
    assert len(breakdown["epics"]) > 0

    # Verify GitHub Issue was created
    assert len(mock_repo._issues) == 1
    issue = list(mock_repo._issues.values())[0]
    assert "Planning" in issue.title or "Milestone" in issue.title


@pytest.mark.integration
def test_planning_session_answer_parsing_and_accumulation(scraut_repo, config):
    """Posting /answer commands should accumulate in planning-session.md."""
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    # Setup: create planning-session.md with a GitHub issue reference
    milestone_dir = scraut_repo / ".scraut" / "milestones" / "m01-auth"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    (milestone_dir / "planning-session.md").write_text(
        "# Planning Session\n\nGitHub Issue: #1\nAnswers received: 0/5\n\n## Q&A Log\n\n"
    )

    mock_repo = MockRepository()
    from test.mocks.github_mocks import MockIssue
    issue = MockIssue(1, "🎯 Milestone Planning: Auth",
                       body="<!-- scraut-planning-session milestone:m01-auth -->")
    mock_repo.add_issue(issue)

    config["_repo_name"] = "test-org/test-repo"

    with patch("scraut.scrum.milestone.planning_session.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scraut.scrum.milestone.planning_session.generate_roadmap") as mock_roadmap:
            with patch("scraut.scrum.milestone.planning_session.calculate_rolling_velocity",
                       return_value={"avg": 26.0, "sprints_sampled": 3, "std_dev": 2.0}):
                from scraut.scrum.milestone.planning_session import process_comment

                # Post 5 answers
                for q, val in [(1, "6 sprints"), (2, "confirm"), (3, "26"),
                               (4, "none"), (5, "core,sso")]:
                    process_comment(1, f"/answer Q{q} {val}", "test-org/test-repo", config)

    # After all 5 answers, roadmap generation should be called
    assert mock_roadmap.called
