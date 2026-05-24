"""
test/mocks/llm_mocks.py
Standard LLM response mocks. Patch scraut.platform.llm.client.complete or complete_json
in unit tests so no real API calls are ever made.
"""
import json
from unittest.mock import patch


def mock_complete(return_text: str):
    """Context manager to mock the complete() function."""
    return patch("scraut.platform.llm.client.complete", return_value=return_text)


def mock_complete_json(return_dict: dict):
    """Context manager to mock the complete_json() function."""
    return patch("scraut.platform.llm.client.complete_json", return_value=return_dict)


# Standard mock responses for common LLM calls

TRIAGE_RESPONSE = {
    "type_label": "story",
    "priority_label": "p:medium",
    "story_point_estimate": 3,
    "reasoning": "Moderate complexity, clear requirements",
    "suggested_acceptance_criteria": ["Users can log in", "Session expires after 24h"],
}

STANDUP_SUMMARY_RESPONSE = """## Team Standup — 2026-05-23

**Blockers (1):**
- Bob: waiting for Redis config from DevOps (#44)

**Yesterday:**
- Alice: Merged PR #89 (auth refactor), reviewed PR #91
- Bob: Pushed 3 commits to payment feature

**Today:**
- Alice: Session management (#46)
- Bob: Continue payment integration (#47)
- Charlie: No update submitted
"""

SPRINT_GOAL_RESPONSE = {
    "suggested_goal": "Ship core authentication and begin payment gateway integration",
    "proposed_issues": [42, 46, 47],
    "total_sp": 22,
    "rationale": "These are the highest-priority unstarted stories aligned with the auth milestone",
}

DECOMPOSITION_RESPONSE = {
    "epics": [
        {
            "id": "E1",
            "title": "Core Authentication",
            "description": "Registration, login, session management",
            "estimated_sp_range": [15, 20],
            "stories": [
                {"title": "As a user, I can register", "acceptance_criteria": ["Email unique"], "estimated_sp": 5, "type": "story", "depends_on": []},
                {"title": "As a user, I can log in", "acceptance_criteria": ["JWT returned"], "estimated_sp": 3, "type": "story", "depends_on": []},
            ],
        }
    ],
    "total_sp_range": [15, 20],
    "suggested_sprint_count": 2,
    "risks": ["Email delivery reliability"],
    "confidence": "high",
}

SUGGESTION_DRAFT_RESPONSE = {
    "title": "PR Review Is a Recurring Bottleneck",
    "why_flagged": "PR review delay mentioned 3+ times in standup blockers across 2 sprints.",
    "options": [
        {
            "label": "A",
            "description": "Implement daily review rotation with 4-hour SLA",
            "expected_impact": "PR wait: 3.2 days → <1 day",
            "recommended": True,
        },
        {
            "label": "B",
            "description": "Add daily 10am review timebox to calendar",
            "expected_impact": "PR wait: 3.2 days → ~1.5 days",
            "recommended": False,
        },
    ],
    "measurement_criteria": [
        "Re-run PRReviewLagDetector — expect avg wait <48h",
        "Blocker mentions about review — expect ≤1 per sprint",
    ],
}
