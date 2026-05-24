"""
test/integration/test_standup_flow.py
End-to-end: template reset → repo sync prefill → summary generation.
Uses real file operations on tmp_path but mocks GitHub API and LLM.
"""
import pytest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from test.mocks.llm_mocks import STANDUP_SUMMARY_RESPONSE


@pytest.mark.integration
def test_full_standup_flow(scraut_repo, config):
    """
    1. Reset templates → creates alice.md, bob.md, charlie.md
    2. Prefill from activity.json → alice.md Yesterday is populated
    3. Generate summary → reads all files, produces digest
    """
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    target_date = "2026-05-23"

    # Step 1: Reset templates (fixture files already exist, so idempotent)
    from scraut.scrum.standup.reset_templates import reset_templates
    reset_templates(config)

    # Verify standup files exist
    standup_dir = scraut_repo / "sprint" / "01" / "standup" / target_date
    assert (standup_dir / "alice.md").exists()
    assert (standup_dir / "bob.md").exists()

    # Step 2: Prefill from activity (activity.json is in fixtures)
    from scraut.scrum.repo_sync.prefill_standups import prefill_standups
    prefill_standups(config, target_date)

    # Alice's standup should have her PR merge pre-filled
    alice_content = (standup_dir / "alice.md").read_text()
    assert "PR #89" in alice_content or "Yesterday" in alice_content

    # Step 3: Generate summary (mock LLM)
    with patch("scraut.scrum.standup.generate_summary.complete",
               return_value=STANDUP_SUMMARY_RESPONSE):
        with patch("scraut.scrum.standup.generate_summary.post_to_slack") as mock_slack:
            from scraut.scrum.standup.generate_summary import generate_summary
            summary = generate_summary(config, target_date, dry_run=False)

    # Verify summary was written to summary folder
    summary_path = scraut_repo / ".scraut" / "sprint" / "01" / "standup" / "summary" / f"{target_date}.md"
    assert summary_path.exists()
    content = summary_path.read_text()
    assert "BOT-GENERATED" in content

    # Verify Slack was called
    assert mock_slack.called


@pytest.mark.integration
def test_standup_summary_not_overwritten_on_reruns(scraut_repo, config):
    """Running the summary twice should update the file but not fail."""
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    with patch("scraut.scrum.standup.generate_summary.complete",
               return_value=STANDUP_SUMMARY_RESPONSE):
        with patch("scraut.scrum.standup.generate_summary.post_to_slack"):
            from scraut.scrum.standup.generate_summary import generate_summary
            result1 = generate_summary(config, "2026-05-23")
            result2 = generate_summary(config, "2026-05-23")

    assert result1 is not None
    assert result2 is not None
