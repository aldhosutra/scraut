"""test/unit/test_planning_session.py — test /answer command parsing"""
import pytest
from scraut.scrum.milestone.planning_session import (
    parse_answers_from_comment,
    load_existing_answers,
    TOTAL_QUESTIONS,
)


@pytest.mark.unit
@pytest.mark.parametrize("comment,expected", [
    ("/answer Q1 6 sprints", {1: "6 sprints"}),
    ("/answer Q3 confirm", {3: "confirm"}),
    ("/answer Q5 core,sso,2fa", {5: "core,sso,2fa"}),
    ("/answer Q1 2026-09-01", {1: "2026-09-01"}),
    ("Just a regular comment", {}),
    ("Great work team!", {}),
    ("/ANSWER Q2 confirm", {2: "confirm"}),   # case-insensitive
])
def test_parse_answers_from_comment(comment, expected):
    result = parse_answers_from_comment(comment)
    assert result == expected


@pytest.mark.unit
def test_parse_multiple_answers_in_one_comment():
    comment = "/answer Q1 5 sprints\n/answer Q3 confirm\n/answer Q4 none"
    result = parse_answers_from_comment(comment)
    assert result == {1: "5 sprints", 3: "confirm", 4: "none"}


@pytest.mark.unit
def test_load_existing_answers_from_file(tmp_path):
    planning_file = tmp_path / "planning-session.md"
    planning_file.write_text(
        "# Planning Session\n\n## Q&A Log\n\nQ1: 6 sprints\nQ2: confirm\nQ3: 26\n"
    )
    answers = load_existing_answers(planning_file)
    assert answers[1] == "6 sprints"
    assert answers[2] == "confirm"
    assert answers[3] == "26"


@pytest.mark.unit
def test_total_questions_is_five():
    assert TOTAL_QUESTIONS == 5
