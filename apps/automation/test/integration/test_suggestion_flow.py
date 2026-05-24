"""
test/integration/test_suggestion_flow.py
End-to-end: detectors fire → suggestion file created → team responds → measurement.
"""
import pytest
from pathlib import Path
from unittest.mock import patch
from test.mocks.github_mocks import MockRepository
from test.mocks.llm_mocks import SUGGESTION_DRAFT_RESPONSE


@pytest.mark.integration
def test_blocker_detection_creates_suggestion_file(scraut_repo, config):
    """When blocker detector fires, suggestion file should be created."""
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    # Create enough standup files with blockers to trigger the detector
    for day in ["2026-05-20", "2026-05-21", "2026-05-22", "2026-05-23"]:
        standup_dir = scraut_repo / "sprint" / "01" / "standup" / day
        standup_dir.mkdir(parents=True, exist_ok=True)
        for person in ["alice", "bob"]:
            (standup_dir / f"{person}.md").write_text(
                f"# Standup\n## Blockers\n- PR review is blocking progress again\n"
            )

    mock_repo = MockRepository()
    with patch("scraut.scrum.suggestions.generate_suggestion.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scraut.scrum.suggestions.generate_suggestion.complete_json",
                   return_value=SUGGESTION_DRAFT_RESPONSE):
            from scraut.scrum.suggestions.detectors import blocker_frequency_detector
            from scraut.scrum.suggestions.generate_suggestion import generate_suggestion

            evidence = blocker_frequency_detector(config, min_occurrences=3)
            assert evidence is not None

            generate_suggestion(evidence, "test-org/test-repo", config)

    # Verify suggestion file was created
    active_dir = scraut_repo / ".scraut" / "suggestions" / "active"
    suggestion_files = list(active_dir.glob("s*.md"))
    assert len(suggestion_files) == 1

    content = suggestion_files[0].read_text()
    assert "proposed" in content
    assert "Evidence trail" in content
    assert "Suggested actions" in content
    assert "measurement_criteria" in content.lower() or "How Scraut will measure" in content

    # Verify GitHub issue was created
    assert len(mock_repo._issues) == 1
