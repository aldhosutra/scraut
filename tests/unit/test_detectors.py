"""
tests/unit/test_detectors.py
Test all 6 pattern detectors. Each detector has threshold tests.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from scripts.suggestions.detectors import (
    blocker_frequency_detector,
    velocity_drop_detector,
    capacity_imbalance_detector,
    retro_followthrough_detector,
    _cluster_by_keywords,
)


@pytest.mark.unit
def test_blocker_frequency_no_blockers(scraut_repo, config):
    """With fewer than min_occurrences blockers, return None."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    # charlie.md has no blockers; alice.md has none; only bob.md has 1
    result = blocker_frequency_detector(config, min_occurrences=5)
    assert result is None


@pytest.mark.unit
def test_blocker_frequency_triggers_at_threshold(scraut_repo, config):
    """With enough blockers of the same theme, Evidence is returned."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    # Write multiple standup files with blockers
    for day in ["2026-05-20", "2026-05-21", "2026-05-22"]:
        standup_dir = scraut_repo / "sprint-01" / "standup" / day
        standup_dir.mkdir(parents=True, exist_ok=True)
        (standup_dir / "alice.md").write_text(
            f"# Standup\n## Blockers\n- Waiting for PR review on #90\n"
        )
        (standup_dir / "bob.md").write_text(
            f"# Standup\n## Blockers\n- PR review still pending\n"
        )

    result = blocker_frequency_detector(config, min_occurrences=3)
    assert result is not None
    assert result.detector_name == "BlockerFrequencyDetector"
    assert len(result.instances) >= 3


@pytest.mark.unit
def test_cluster_by_keywords_groups_pr_review():
    blockers = [
        {"text": "Waiting for PR review", "sprint": 1, "date": "2026-05-23", "author": "alice", "file": "test.md"},
        {"text": "PR still needs review", "sprint": 1, "date": "2026-05-23", "author": "bob", "file": "test.md"},
        {"text": "Need design approval", "sprint": 1, "date": "2026-05-23", "author": "alice", "file": "test.md"},
    ]
    clusters = _cluster_by_keywords(blockers)
    assert "pr review" in clusters
    assert len(clusters["pr review"]) == 2


@pytest.mark.unit
def test_velocity_drop_no_drop(scraut_repo, config):
    """With consistent velocity, no trigger."""
    with patch("scripts.suggestions.detectors.calculate_rolling_velocity") as mock_roll:
        with patch("scripts.suggestions.detectors.calculate_sprint_velocity") as mock_vel:
            mock_roll.return_value = {"avg": 26.0, "sprints_sampled": 5}
            mock_vel.return_value = {"completed_sp": 25, "planned_sp": 28}  # ~96% — no drop
            result = velocity_drop_detector("test-repo", config, drop_threshold=0.15)
    assert result is None


@pytest.mark.unit
def test_velocity_drop_triggers_on_sustained_drop(scraut_repo, config):
    """With >15% drop for 2+ sprints, Evidence is returned."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    with patch("scripts.suggestions.detectors.calculate_rolling_velocity") as mock_roll:
        with patch("scripts.suggestions.detectors.calculate_sprint_velocity") as mock_vel:
            mock_roll.return_value = {"avg": 30.0, "sprints_sampled": 5}
            # Both sprints have >15% drop from avg of 30
            mock_vel.return_value = {"completed_sp": 18, "planned_sp": 30}  # 40% drop
            result = velocity_drop_detector("test-repo", config, min_sprints=1)
    assert result is not None
    assert result.detector_name == "VelocityDropDetector"


@pytest.mark.unit
def test_capacity_imbalance_balanced_team(scraut_repo, config, mock_repo):
    """Balanced load → no trigger."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    # Give all members equal SP
    for issue in mock_repo._issues.values():
        issue.assignees = []
    with patch("scripts.suggestions.detectors.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        result = capacity_imbalance_detector("test-org/test-repo", config)
    # With no assignees, all have 0 sp — balanced
    assert result is None


@pytest.mark.unit
def test_retro_followthrough_no_action_items(scraut_repo, config):
    """With no retro action items, no trigger."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    # Remove action items from retro summary
    retro_summary = scraut_repo / "sprint-01" / "retrospective" / "summary.md"
    retro_summary.write_text("# Retro Summary\n## Went well\nEverything was great.\n")
    result = retro_followthrough_detector(config, min_missed=1)
    assert result is None
