"""test/unit/test_standup_coach.py — tests for the standup coach feature."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from scraut.scrum.standup.coach import (
    is_today_vague,
    build_recommendation,
    _fallback_recommendation,
    run_coach,
)


# ─────────────────────────────────────────────
# is_today_vague — detection logic
# ─────────────────────────────────────────────

def _standup(today_section: str) -> str:
    return f"## Yesterday\nDid stuff\n\n## Today\n{today_section}\n\n## Blockers\nNone\n"


@pytest.mark.unit
def test_vague_short_no_issue_ref():
    content = _standup("working on things")
    assert is_today_vague(content) is True


@pytest.mark.unit
def test_not_vague_has_issue_ref():
    content = _standup("continue work on #42 rate limiting")
    assert is_today_vague(content) is False


@pytest.mark.unit
def test_not_vague_long_enough():
    long_today = " ".join(["word"] * 25)
    content = _standup(long_today)
    assert is_today_vague(content) is False


@pytest.mark.unit
@pytest.mark.parametrize("phrase", [
    "code review",
    "pr review",
    "pairing",
    "pair programming",
    "onboarding",
    "sprint planning",
    "retrospective",
    "all-hands",
    "interview",
    "out of office",
    "ooo",
    "sick leave",
    "holiday",
    "travel",
])
def test_not_vague_exempt_phrase(phrase):
    content = _standup(f"Attending {phrase} today")
    assert is_today_vague(content) is False


@pytest.mark.unit
def test_not_vague_empty_today_section():
    content = _standup("none")
    assert is_today_vague(content) is False


@pytest.mark.unit
def test_not_vague_missing_today_section():
    content = "## Yesterday\nDid stuff\n\n## Blockers\nNone\n"
    assert is_today_vague(content) is False


@pytest.mark.unit
def test_not_vague_when_require_issue_ref_false():
    # Short text, no issue ref, but require_issue_ref=False — still could flag on length
    content = _standup("fix the thing")
    assert is_today_vague(content, require_issue_ref=False) is True


@pytest.mark.unit
def test_not_vague_custom_min_words():
    content = _standup("working on stuff today and also other things")
    # 9 words — under default 20
    assert is_today_vague(content, min_words=5) is False  # 9 >= 5 → not vague
    assert is_today_vague(content, min_words=20) is True   # 9 < 20 → vague


# ─────────────────────────────────────────────
# _fallback_recommendation
# ─────────────────────────────────────────────

@pytest.mark.unit
def test_fallback_with_no_issues():
    msg = _fallback_recommendation("Alice", [])
    assert "Alice" in msg
    assert len(msg) > 20


@pytest.mark.unit
def test_fallback_with_issues():
    issues = [
        {"number": 12, "title": "Rate limiting", "sp": 5},
        {"number": 23, "title": "OAuth integration", "sp": 8},
    ]
    msg = _fallback_recommendation("Bob", issues)
    assert "#12" in msg
    assert "#23" in msg


@pytest.mark.unit
def test_fallback_caps_at_three_issues():
    issues = [{"number": i, "title": f"Issue {i}", "sp": 1} for i in range(10)]
    msg = _fallback_recommendation("Charlie", issues)
    # Should only mention up to 3 issues
    issue_refs = [f"#{i}" for i in range(10) if f"#{i}" in msg]
    assert len(issue_refs) <= 3


# ─────────────────────────────────────────────
# run_coach — integration with mocks
# ─────────────────────────────────────────────

def _make_config(enabled=True, min_words=20, require_ref=True, skip_days=0, notify_sm=False):
    return {
        "standup_coach": {
            "enabled": enabled,
            "min_today_words": min_words,
            "require_issue_ref": require_ref,
            "skip_sprint_start_days": skip_days,
            "notify_sm": notify_sm,
        },
        "sprint": {
            "current_sprint": 1,
            "length_days": 14,
            "start_day": "monday",
            "folder_padding": 3,
            "work_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        },
        "team": {
            "members": [
                {"login": "alice", "display": "Alice", "slack_id": "UALICE"},
                {"login": "bob", "display": "Bob", "slack_id": "UBBOB"},
            ],
            "scrum_master": "bob",
            "slack_channel": "#scraut-bot",
        },
        "llm": {"provider": "anthropic", "model": "claude-sonnet-4-6", "max_tokens": 500},
    }


@pytest.mark.unit
def test_run_coach_disabled_returns_early():
    cfg = _make_config(enabled=False)
    with patch("scraut.scrum.standup.coach.send_slack_dm") as mock_dm:
        run_coach(cfg, target_date="2026-05-25")
    mock_dm.assert_not_called()


@pytest.mark.unit
def test_run_coach_skips_on_sprint_start_day(tmp_path, monkeypatch):
    cfg = _make_config(enabled=True, skip_days=2)
    monkeypatch.chdir(tmp_path)

    with (
        patch("scraut.scrum.standup.coach.get_workspace_root", return_value=tmp_path),
        patch("scraut.scrum.standup.coach.get_scraut_root", return_value=tmp_path / ".scraut"),
        patch("scraut.scrum.standup.coach.get_current_sprint", return_value=1),
        patch("scraut.scrum.standup.coach.get_sprint_folder", return_value=tmp_path / "sprint" / "001"),
        patch("scraut.scrum.standup.coach.get_sprint_dates", return_value=(
            __import__("datetime").date(2026, 5, 25),
            __import__("datetime").date(2026, 6, 7),
        )),
        patch("scraut.scrum.standup.coach.working_days_elapsed", return_value=0),
        patch("scraut.scrum.standup.coach.send_slack_dm") as mock_dm,
    ):
        run_coach(cfg, target_date="2026-05-25")

    mock_dm.assert_not_called()


@pytest.mark.unit
def test_run_coach_sends_dm_for_vague_standup(tmp_path, monkeypatch):
    cfg = _make_config(enabled=True, skip_days=0)
    monkeypatch.chdir(tmp_path)

    # Create a vague standup for alice
    standup_dir = tmp_path / "sprint" / "001" / "standup" / "2026-05-25"
    standup_dir.mkdir(parents=True)
    (standup_dir / "alice.md").write_text(
        "## Yesterday\nDid some work\n\n## Today\nworking on things\n\n## Blockers\nNone\n"
    )
    # Bob has a specific standup — should NOT be coached
    (standup_dir / "bob.md").write_text(
        "## Yesterday\nMerged PR\n\n## Today\nContinue #42 rate limiting, review #45\n\n## Blockers\nNone\n"
    )
    (tmp_path / "okr").mkdir(parents=True)

    from datetime import date as dt_date
    with (
        patch("scraut.scrum.standup.coach.get_workspace_root", return_value=tmp_path),
        patch("scraut.scrum.standup.coach.get_scraut_root", return_value=tmp_path / ".scraut"),
        patch("scraut.scrum.standup.coach.get_current_sprint", return_value=1),
        patch("scraut.scrum.standup.coach.get_sprint_folder", return_value=tmp_path / "sprint" / "001"),
        patch("scraut.scrum.standup.coach.get_sprint_dates", return_value=(
            dt_date(2026, 5, 25), dt_date(2026, 6, 7)
        )),
        patch("scraut.scrum.standup.coach.working_days_elapsed", return_value=1),
        patch("scraut.scrum.standup.coach.working_days_remaining", return_value=8),
        patch("scraut.scrum.standup.coach.complete", return_value="Here's a helpful recommendation for Alice."),
        patch("scraut.scrum.standup.coach.send_slack_dm") as mock_dm,
    ):
        run_coach(cfg, target_date="2026-05-25", repo_name=None, dry_run=False)

    # Only Alice should receive a DM
    assert mock_dm.call_count == 1
    call_args = mock_dm.call_args
    assert call_args[0][0] == "UALICE"


@pytest.mark.unit
def test_run_coach_dry_run_does_not_send_dm(tmp_path, monkeypatch):
    cfg = _make_config(enabled=True, skip_days=0)
    monkeypatch.chdir(tmp_path)

    standup_dir = tmp_path / "sprint" / "001" / "standup" / "2026-05-25"
    standup_dir.mkdir(parents=True)
    (standup_dir / "alice.md").write_text(
        "## Yesterday\nDid work\n\n## Today\nworking on things\n\n## Blockers\nNone\n"
    )
    (tmp_path / "okr").mkdir(parents=True)

    from datetime import date as dt_date
    with (
        patch("scraut.scrum.standup.coach.get_workspace_root", return_value=tmp_path),
        patch("scraut.scrum.standup.coach.get_scraut_root", return_value=tmp_path / ".scraut"),
        patch("scraut.scrum.standup.coach.get_current_sprint", return_value=1),
        patch("scraut.scrum.standup.coach.get_sprint_folder", return_value=tmp_path / "sprint" / "001"),
        patch("scraut.scrum.standup.coach.get_sprint_dates", return_value=(
            dt_date(2026, 5, 25), dt_date(2026, 6, 7)
        )),
        patch("scraut.scrum.standup.coach.working_days_elapsed", return_value=1),
        patch("scraut.scrum.standup.coach.working_days_remaining", return_value=8),
        patch("scraut.scrum.standup.coach.complete", return_value="Recommendation text."),
        patch("scraut.scrum.standup.coach.send_slack_dm") as mock_dm,
    ):
        run_coach(cfg, target_date="2026-05-25", repo_name=None, dry_run=True)

    mock_dm.assert_not_called()


@pytest.mark.unit
def test_run_coach_no_dm_without_slack_id(tmp_path, monkeypatch):
    cfg = _make_config(enabled=True, skip_days=0)
    # Remove slack_id from alice
    cfg["team"]["members"][0].pop("slack_id")
    monkeypatch.chdir(tmp_path)

    standup_dir = tmp_path / "sprint" / "001" / "standup" / "2026-05-25"
    standup_dir.mkdir(parents=True)
    (standup_dir / "alice.md").write_text(
        "## Yesterday\nDid work\n\n## Today\nworking on things\n\n## Blockers\nNone\n"
    )
    (tmp_path / "okr").mkdir(parents=True)

    from datetime import date as dt_date
    with (
        patch("scraut.scrum.standup.coach.get_workspace_root", return_value=tmp_path),
        patch("scraut.scrum.standup.coach.get_scraut_root", return_value=tmp_path / ".scraut"),
        patch("scraut.scrum.standup.coach.get_current_sprint", return_value=1),
        patch("scraut.scrum.standup.coach.get_sprint_folder", return_value=tmp_path / "sprint" / "001"),
        patch("scraut.scrum.standup.coach.get_sprint_dates", return_value=(
            dt_date(2026, 5, 25), dt_date(2026, 6, 7)
        )),
        patch("scraut.scrum.standup.coach.working_days_elapsed", return_value=1),
        patch("scraut.scrum.standup.coach.working_days_remaining", return_value=8),
        patch("scraut.scrum.standup.coach.complete", return_value="Recommendation."),
        patch("scraut.scrum.standup.coach.send_slack_dm") as mock_dm,
    ):
        run_coach(cfg, target_date="2026-05-25", repo_name=None)

    mock_dm.assert_not_called()


@pytest.mark.unit
def test_run_coach_notify_sm_sends_summary(tmp_path, monkeypatch):
    cfg = _make_config(enabled=True, skip_days=0, notify_sm=True)
    monkeypatch.chdir(tmp_path)

    standup_dir = tmp_path / "sprint" / "001" / "standup" / "2026-05-25"
    standup_dir.mkdir(parents=True)
    (standup_dir / "alice.md").write_text(
        "## Yesterday\nDid work\n\n## Today\nworking on things\n\n## Blockers\nNone\n"
    )
    (tmp_path / "okr").mkdir(parents=True)

    from datetime import date as dt_date
    with (
        patch("scraut.scrum.standup.coach.get_workspace_root", return_value=tmp_path),
        patch("scraut.scrum.standup.coach.get_scraut_root", return_value=tmp_path / ".scraut"),
        patch("scraut.scrum.standup.coach.get_current_sprint", return_value=1),
        patch("scraut.scrum.standup.coach.get_sprint_folder", return_value=tmp_path / "sprint" / "001"),
        patch("scraut.scrum.standup.coach.get_sprint_dates", return_value=(
            dt_date(2026, 5, 25), dt_date(2026, 6, 7)
        )),
        patch("scraut.scrum.standup.coach.working_days_elapsed", return_value=1),
        patch("scraut.scrum.standup.coach.working_days_remaining", return_value=8),
        patch("scraut.scrum.standup.coach.complete", return_value="Recommendation."),
        patch("scraut.scrum.standup.coach.send_slack_dm") as mock_dm,
    ):
        run_coach(cfg, target_date="2026-05-25", repo_name=None)

    # Alice DM + SM summary DM = 2 calls
    assert mock_dm.call_count == 2
    sm_call = mock_dm.call_args_list[1]
    assert sm_call[0][0] == "UBBOB"
    assert "Alice" in sm_call[0][1]
