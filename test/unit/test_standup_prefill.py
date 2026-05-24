"""test/unit/test_standup_prefill.py — test Yesterday pre-fill logic"""
import pytest
from pathlib import Path
from scraut.scrum.repo_sync.prefill_standups import (
    is_yesterday_empty, format_activity_as_bullets
)


@pytest.mark.unit
def test_is_yesterday_empty_returns_true_for_placeholder():
    content = (
        "# Standup — Alice\n\n"
        "## Yesterday\n"
        "<!-- What did you complete? Reference issues/PRs where applicable. -->\n"
        "\n## Today\n"
    )
    assert is_yesterday_empty(content) is True


@pytest.mark.unit
def test_is_yesterday_empty_returns_false_when_filled():
    content = (
        "# Standup — Alice\n\n"
        "## Yesterday\n"
        "- Merged PR #89\n"
        "\n## Today\n"
    )
    assert is_yesterday_empty(content) is False


@pytest.mark.unit
def test_format_activity_as_bullets_with_merged_pr():
    member_data = {
        "commits": [],
        "prs_merged": [{"number": 89, "title": "Auth refactor",
                         "repo": "product-api", "closes_issues": [42]}],
        "prs_opened": [],
        "prs_reviewed": [],
    }
    result = format_activity_as_bullets(member_data, "Alice")
    assert "PR #89" in result
    assert "#42" in result


@pytest.mark.unit
def test_format_activity_as_bullets_with_no_activity():
    member_data = {"commits": [], "prs_merged": [],
                   "prs_opened": [], "prs_reviewed": []}
    result = format_activity_as_bullets(member_data, "Charlie")
    assert "No activity detected" in result or "No commits" in result
