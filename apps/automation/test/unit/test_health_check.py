"""test/unit/test_health_check.py"""
import pytest
from scraut.scrum.milestone.health_check import score_sprint


@pytest.mark.unit
@pytest.mark.parametrize("params,expected_status", [
    # Perfect sprint: all planned issues closed, on milestone pace
    ({"planned_sp": 26, "actual_sp": 26, "planned_issues": [1, 2, 3],
      "completed_issues": [1, 2, 3], "milestone_total_sp": 100,
      "milestone_delivered_sp": 50, "sprint_num": 3, "total_planned_sprints": 6,
      "unplanned_stories": 0}, "on-track"),
    # Weak sprint: only 60% done, behind on milestone
    ({"planned_sp": 26, "actual_sp": 15, "planned_issues": [1, 2, 3, 4, 5],
      "completed_issues": [1, 2], "milestone_total_sp": 100,
      "milestone_delivered_sp": 20, "sprint_num": 3, "total_planned_sprints": 6,
      "unplanned_stories": 3}, "at-risk"),
    # Moderate sprint
    ({"planned_sp": 26, "actual_sp": 20, "planned_issues": [1, 2, 3],
      "completed_issues": [1, 2], "milestone_total_sp": 100,
      "milestone_delivered_sp": 40, "sprint_num": 3, "total_planned_sprints": 6,
      "unplanned_stories": 1}, "watch"),
])
def test_score_sprint_status(params, expected_status):
    result = score_sprint(**params)
    assert result["status"] == expected_status
    assert "velocity" in result
    assert "delivery" in result
    assert "milestone" in result
    assert "focus" in result
    assert "composite" in result


@pytest.mark.unit
def test_score_sprint_composite_between_0_and_100():
    result = score_sprint(
        planned_sp=26, actual_sp=22,
        planned_issues=[1, 2, 3, 4], completed_issues=[1, 2, 3],
        milestone_total_sp=100, milestone_delivered_sp=45,
        sprint_num=3, total_planned_sprints=6, unplanned_stories=1
    )
    assert 0 <= result["composite"] <= 100


@pytest.mark.unit
def test_score_sprint_perfect_score():
    result = score_sprint(
        planned_sp=26, actual_sp=26,
        planned_issues=[1, 2, 3], completed_issues=[1, 2, 3],
        milestone_total_sp=78, milestone_delivered_sp=52,  # exactly on pace (3/6 = 50%+)
        sprint_num=3, total_planned_sprints=6, unplanned_stories=0
    )
    assert result["velocity"] == 100
    assert result["delivery"] == 100
    assert result["focus"] == 100
    assert result["composite"] >= 90


@pytest.mark.unit
def test_score_sprint_zero_planned_sp_does_not_crash():
    """Edge case: sprint with no planned SP should not raise ZeroDivisionError."""
    result = score_sprint(
        planned_sp=0, actual_sp=0,
        planned_issues=[], completed_issues=[],
        milestone_total_sp=100, milestone_delivered_sp=10,
        sprint_num=1, total_planned_sprints=6, unplanned_stories=0
    )
    assert isinstance(result["composite"], (int, float))
