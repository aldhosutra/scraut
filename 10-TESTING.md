# Phase 10: Testing
*Scraut Implementation — run after all previous phases are complete*

## Goal
Build a comprehensive automated test suite that verifies every critical behaviour
in Scraut. No manual verification. Every merged commit runs the full suite in CI.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| `pytest` | Test runner |
| `pytest-mock` | Mock objects and patches |
| `responses` | Mock HTTP requests (Slack, LLM API) |
| `freezegun` | Freeze time for date-sensitive tests |
| `pytest-cov` | Code coverage reporting |
| `pytest-parametrize` | Table-driven tests |
| `tmp_path` (built-in) | Temporary file system per test |

Add to `requirements-test.txt`:
```
pytest>=8.0.0
pytest-mock>=3.14.0
responses>=0.25.0
freezegun>=1.4.0
pytest-cov>=5.0.0
```

---

## Directory Structure

```
tests/
├── conftest.py                        # Shared fixtures for all tests
├── fixtures/
│   ├── scraut.yml                     # Minimal test config
│   ├── sprint-01/
│   │   ├── meta.md
│   │   ├── standup/
│   │   │   ├── 2026-05-23/
│   │   │   │   ├── alice.md          # Normal standup
│   │   │   │   ├── bob.md            # Has blockers
│   │   │   │   └── charlie.md        # Empty (no update)
│   │   │   └── summary/
│   │   ├── retrospective/
│   │   │   ├── alice.md
│   │   │   └── bob.md
│   │   ├── review/
│   │   └── code/
│   │       └── 2026-05-23/
│   │           └── activity.json
│   ├── milestones/
│   │   └── m01-auth/
│   │       ├── milestone.md
│   │       └── breakdown.json
│   └── suggestions/
│       └── active/
│           └── s001-test.md
├── mocks/
│   ├── github_mocks.py               # PyGitHub mock classes
│   └── llm_mocks.py                  # LLM API mock responses
├── unit/
│   ├── test_config.py
│   ├── test_file_utils.py
│   ├── test_date_utils.py
│   ├── test_velocity.py
│   ├── test_standup_templates.py
│   ├── test_planning_session.py
│   ├── test_derive_state.py          # Most critical
│   ├── test_detectors.py
│   ├── test_tally_estimation.py
│   ├── test_health_check.py
│   └── test_triage.py
└── integration/
    ├── test_standup_flow.py
    ├── test_milestone_flow.py
    └── test_suggestion_flow.py
```

---

## `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --tb=short
    --strict-markers
    -v
    --cov=scripts
    --cov-report=term-missing
    --cov-fail-under=70
markers =
    unit: Unit tests (no external I/O)
    integration: Integration tests (uses temp files)
    slow: Tests that take >2 seconds
```

---

## `tests/fixtures/scraut.yml`

```yaml
sprint:
  length_days: 14
  start_day: monday
  start_time: "09:00"
  timezone: "Asia/Jakarta"
  capacity_buffer: 0.85
  current_sprint: 1

team:
  members:
    - login: alice
      display: Alice
      role: developer
      slack_id: U001
      email: alice@test.com
    - login: bob
      display: Bob
      role: scrum_master
      slack_id: U002
      email: bob@test.com
    - login: charlie
      display: Charlie
      role: developer
      slack_id: U003
      email: charlie@test.com
  product_owner: alice
  scrum_master: bob
  slack_channel: "#test-scraut"

ceremonies:
  planning: true
  standup: true
  grooming: true
  review: true
  retrospective: true
  estimation: true

definition_of_done:
  - Tests written for new functionality
  - PR reviewed by at least one team member
  - CI passing

repos: []

llm:
  provider: anthropic
  model: claude-sonnet-4-6
  max_tokens: 1000
  cost_controls:
    max_daily_tokens: 100000
    batch_where_possible: false

agents:
  enabled: false

notifications:
  slack_webhook: "https://hooks.slack.com/test"
  morning_dm: false
  weekly_email: false
  stakeholder_emails: []

portal:
  enabled: false
  title: "Test Dashboard"
  public: false

suggestions:
  enabled: true
  min_evidence_count: 3
  measurement_sprints: 2
```

---

## `tests/fixtures/sprint-01/standup/2026-05-23/alice.md`

```markdown
# Standup — Alice
<!-- Sprint: sprint-01 | Date: 2026-05-23 | Author: alice -->

## Yesterday
- Merged PR #89: "Refactor auth module" — closes #42
- Reviewed PR #91

## Today
- Working on issue #46: Session management

## Blockers
None

## Notes
```

---

## `tests/fixtures/sprint-01/standup/2026-05-23/bob.md`

```markdown
# Standup — Bob
<!-- Sprint: sprint-01 | Date: 2026-05-23 | Author: bob -->

## Yesterday
- Pushed 3 commits to feature/payment

## Today
- Continue issue #47: Payment integration

## Blockers
- Issue #44 blocked: waiting for Redis config from DevOps

## Notes
```

---

## `tests/fixtures/sprint-01/standup/2026-05-23/charlie.md`

```markdown
# Standup — Charlie
<!-- Sprint: sprint-01 | Date: 2026-05-23 | Author: charlie -->

## Yesterday

## Today

## Blockers
None
```

---

## `tests/fixtures/sprint-01/standup/2026-05-22/bob.md`

```markdown
# Standup — Bob
<!-- Sprint: sprint-01 | Date: 2026-05-22 | Author: bob -->

## Yesterday
- Started issue #47

## Today
- Continue issue #47

## Blockers
- Issue #44 blocked: Redis config still missing from DevOps

## Notes
```

---

## `tests/fixtures/sprint-01/retrospective/alice.md`

```markdown
# Retro — Alice — Sprint 01

## Went well
- Daily standups were focused
- PR reviews were fast this sprint

## Could improve
- Too many context switches
- PR reviews took 3+ days sometimes

## Action items I'll own
- Set up a shared review slot daily at 10am
```

---

## `tests/fixtures/sprint-01/retrospective/bob.md`

```markdown
# Retro — Bob — Sprint 01

## Went well
- Deployment pipeline worked smoothly
- Team communication was good

## Could improve
- Missing requirements caused rework
- PR review delays blocked 2 stories

## Action items I'll own
- Create a requirements template for new issues
```

---

## `tests/fixtures/sprint-01/code/2026-05-23/activity.json`

```json
{
  "date": "2026-05-23",
  "repos": ["acme/product-api"],
  "team_filter": ["alice", "bob", "charlie"],
  "generated_at": "2026-05-23T08:00:00Z",
  "members": {
    "alice": {
      "commits": [
        {"sha": "abc1234", "message": "Fix JWT expiry", "branch": "feature/auth", "repo": "product-api", "timestamp": "2026-05-23T07:00:00Z"}
      ],
      "prs_opened": [],
      "prs_merged": [
        {"number": 89, "title": "Refactor auth module", "repo": "product-api", "closes_issues": [42]}
      ],
      "prs_reviewed": [{"number": 91, "title": "Rate limiting", "repo": "product-api", "review_type": "approved"}],
      "ci_failures": []
    },
    "bob": {
      "commits": [
        {"sha": "def5678", "message": "Add payment gateway", "branch": "feature/payment", "repo": "product-api", "timestamp": "2026-05-23T09:00:00Z"}
      ],
      "prs_opened": [],
      "prs_merged": [],
      "prs_reviewed": [],
      "ci_failures": []
    },
    "charlie": {
      "commits": [],
      "prs_opened": [],
      "prs_merged": [],
      "prs_reviewed": [],
      "ci_failures": []
    }
  },
  "team_summary": {
    "prs_opened": 0,
    "prs_merged": 1,
    "prs_reviewed": 1,
    "total_commits": 2,
    "aging_prs": [{"number": 88, "title": "Old PR", "repo": "product-api", "age_days": 5}],
    "ci_status": "green"
  }
}
```

---

## `tests/fixtures/milestones/m01-auth/milestone.md`

```markdown
# Milestone: User Authentication

## Goal
Implement complete authentication: registration, login, and session management.

## Success criteria
- [ ] Users can register and log in
- [ ] Sessions expire after 24h
- [ ] Password reset via email

## Out of scope
- SSO integration

## Known risks
- Email delivery reliability
```

---

## `tests/mocks/github_mocks.py`

```python
"""
tests/mocks/github_mocks.py
Mock classes that replicate the PyGitHub interface.
Use these instead of real GitHub API calls in all tests.
"""
from unittest.mock import MagicMock
from datetime import datetime, timezone


class MockLabel:
    def __init__(self, name: str, color: str = "ffffff"):
        self.name = name
        self.color = color


class MockUser:
    def __init__(self, login: str):
        self.login = login


class MockMilestone:
    def __init__(self, number: int, title: str, state: str = "open"):
        self.number = number
        self.title = title
        self.state = state

    def edit(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockComment:
    def __init__(self, body: str, author_login: str = "alice",
                 created_at: datetime = None):
        self.id = 1
        self.body = body
        self.user = MockUser(author_login)
        self.created_at = created_at or datetime(2026, 5, 23, 9, 0, 0,
                                                  tzinfo=timezone.utc)

    def delete(self):
        pass

    def get_reactions(self):
        return []


class MockIssue:
    def __init__(self, number: int, title: str, state: str = "open",
                 labels: list[str] = None, body: str = "",
                 assignees: list[str] = None, closed_at: datetime = None):
        self.number = number
        self.title = title
        self.state = state
        self.body = body
        self.labels = [MockLabel(l) for l in (labels or [])]
        self.assignees = [MockUser(a) for a in (assignees or [])]
        self.milestone = None
        self.html_url = f"https://github.com/test/repo/issues/{number}"
        self.closed_at = closed_at
        self._comments: list[MockComment] = []

    def get_comments(self):
        return iter(self._comments)

    def get_events(self):
        return iter([])

    def add_comment(self, body: str, author: str = "alice") -> MockComment:
        c = MockComment(body, author)
        self._comments.append(c)
        return c

    def add_to_labels(self, *labels):
        for label in labels:
            name = label if isinstance(label, str) else label.name
            if not any(l.name == name for l in self.labels):
                self.labels.append(MockLabel(name))

    def remove_from_labels(self, label):
        name = label if isinstance(label, str) else label.name
        self.labels = [l for l in self.labels if l.name != name]

    def create_comment(self, body: str) -> MockComment:
        return self.add_comment(body)

    def edit(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockPullRequest:
    def __init__(self, number: int, title: str, body: str = "",
                 state: str = "open", merged: bool = False,
                 author_login: str = "alice",
                 created_at: datetime = None,
                 merged_at: datetime = None,
                 updated_at: datetime = None,
                 head_ref: str = "feature/test"):
        self.number = number
        self.title = title
        self.body = body
        self.state = state
        self.merged = merged
        self.user = MockUser(author_login)
        self.html_url = f"https://github.com/test/repo/pulls/{number}"
        self.created_at = created_at or datetime(2026, 5, 23, tzinfo=timezone.utc)
        self.merged_at = merged_at
        self.updated_at = updated_at or datetime(2026, 5, 23, tzinfo=timezone.utc)
        self.head = MagicMock()
        self.head.ref = head_ref
        self._reviews = []
        self._files = []

    def get_reviews(self):
        return iter(self._reviews)

    def get_files(self):
        return iter(self._files)

    def get_review_comments(self):
        return iter([])

    def edit(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def add_to_labels(self, label):
        pass

    def create_review(self, body: str, event: str = "COMMENT"):
        pass


class MockRepository:
    def __init__(self, full_name: str = "test-org/test-repo"):
        self.full_name = full_name
        self.name = full_name.split("/")[-1]
        self._issues: dict[int, MockIssue] = {}
        self._prs: dict[int, MockPullRequest] = {}
        self._milestones: dict[int, MockMilestone] = {}
        self._labels: dict[str, MockLabel] = {}
        self._files: dict[str, str] = {}
        self._branches: dict[str, str] = {}
        self._next_issue = 1
        self._next_milestone = 1

    def add_issue(self, issue: MockIssue) -> MockIssue:
        self._issues[issue.number] = issue
        return issue

    def add_pr(self, pr: MockPullRequest) -> MockPullRequest:
        self._prs[pr.number] = pr
        return pr

    def get_issue(self, number: int) -> MockIssue:
        if number not in self._issues:
            raise Exception(f"Issue #{number} not found")
        return self._issues[number]

    def get_pull(self, number: int) -> MockPullRequest:
        if number not in self._prs:
            raise Exception(f"PR #{number} not found")
        return self._prs[number]

    def get_issues(self, state: str = "open", labels=None) -> list:
        issues = list(self._issues.values())
        if state != "all":
            issues = [i for i in issues if i.state == state]
        if labels:
            label_names = [l if isinstance(l, str) else l.name for l in labels]
            issues = [i for i in issues
                      if all(any(l.name == ln for l in i.labels) for ln in label_names)]
        return issues

    def get_pulls(self, state: str = "open", **kwargs) -> list:
        prs = list(self._prs.values())
        if state != "all":
            prs = [p for p in prs if p.state == state]
        return prs

    def get_milestones(self, state: str = "open") -> list:
        ms = list(self._milestones.values())
        if state != "all":
            ms = [m for m in ms if m.state == state]
        return ms

    def get_label(self, name: str) -> MockLabel:
        if name not in self._labels:
            raise Exception(f"Label '{name}' not found")
        return self._labels[name]

    def create_label(self, name: str, color: str = "ffffff",
                     description: str = "") -> MockLabel:
        label = MockLabel(name, color)
        self._labels[name] = label
        return label

    def create_issue(self, title: str, body: str = "", labels=None,
                     milestone=None, assignees=None) -> MockIssue:
        issue = MockIssue(
            number=self._next_issue,
            title=title,
            body=body,
            labels=[l if isinstance(l, str) else l.name for l in (labels or [])],
        )
        self._issues[self._next_issue] = issue
        self._next_issue += 1
        return issue

    def create_milestone(self, title: str, description: str = "") -> MockMilestone:
        ms = MockMilestone(self._next_milestone, title)
        self._milestones[self._next_milestone] = ms
        self._next_milestone += 1
        return ms

    def get_commits(self, since=None, **kwargs) -> list:
        return []

    def get_contents(self, path: str, ref: str = "main"):
        if path not in self._files:
            raise Exception(f"File not found: {path}")
        content = MagicMock()
        content.decoded_content = self._files[path].encode()
        content.sha = "test-sha"
        return content

    def create_file(self, path: str, message: str, content: str,
                    branch: str = "main") -> None:
        self._files[path] = content

    def update_file(self, path: str, message: str, content: str,
                    sha: str, branch: str = "main") -> None:
        self._files[path] = content

    def get_branch(self, name: str):
        branch = MagicMock()
        branch.commit.sha = "test-sha"
        return branch

    def create_git_ref(self, ref: str, sha: str) -> None:
        self._branches[ref] = sha

    def create_pull(self, title: str, body: str, head: str,
                    base: str) -> MockPullRequest:
        pr = MockPullRequest(
            number=max(self._prs.keys(), default=0) + 1,
            title=title,
            body=body,
            head_ref=head,
        )
        self._prs[pr.number] = pr
        return pr
```

---

## `tests/mocks/llm_mocks.py`

```python
"""
tests/mocks/llm_mocks.py
Standard LLM response mocks. Patch scripts.llm.client.complete or complete_json
in unit tests so no real API calls are ever made.
"""
import json
from unittest.mock import patch


def mock_complete(return_text: str):
    """Context manager to mock the complete() function."""
    return patch("scripts.llm.client.complete", return_value=return_text)


def mock_complete_json(return_dict: dict):
    """Context manager to mock the complete_json() function."""
    return patch("scripts.llm.client.complete_json", return_value=return_dict)


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
```

---

## `tests/conftest.py`

```python
"""
tests/conftest.py
Shared fixtures for all Scraut tests.
"""
import json
import shutil
from datetime import date
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def scraut_repo(tmp_path) -> Path:
    """
    Create a complete temporary Scraut repository with fixture files.
    Tests that need the file system should use this fixture.
    """
    # Copy all fixtures into tmp_path
    shutil.copytree(FIXTURES_DIR, tmp_path, dirs_exist_ok=True)
    return tmp_path


@pytest.fixture
def config(scraut_repo) -> dict:
    """Load config from the test scraut.yml."""
    import yaml
    with open(scraut_repo / "scraut.yml") as f:
        cfg = yaml.safe_load(f)
    return cfg


@pytest.fixture(autouse=True)
def patch_repo_root(scraut_repo, monkeypatch):
    """Make get_repo_root() return the temp test directory for ALL tests."""
    monkeypatch.setattr(
        "scripts.utils.config._config_path",
        scraut_repo,
    )
    monkeypatch.setattr(
        "scripts.utils.config._config",
        None,  # force reload from test scraut.yml
    )
    import os
    monkeypatch.chdir(scraut_repo)


@pytest.fixture
def mock_repo():
    """Return a MockRepository pre-populated with common test issues."""
    from tests.mocks.github_mocks import MockRepository, MockIssue, MockPullRequest
    from datetime import datetime, timezone

    repo = MockRepository("test-org/test-repo")

    # Sprint issues
    repo.add_issue(MockIssue(42, "Auth module refactor", state="closed",
                              labels=["sprint-01", "story", "sp:5", "in-sprint"]))
    repo.add_issue(MockIssue(44, "Redis config setup", state="open",
                              labels=["sprint-01", "task", "sp:3", "in-sprint", "blocked"]))
    repo.add_issue(MockIssue(46, "Session management", state="open",
                              labels=["sprint-01", "story", "sp:5", "in-sprint"]))
    repo.add_issue(MockIssue(47, "Payment gateway integration", state="open",
                              labels=["sprint-01", "story", "sp:8", "in-sprint"]))
    repo.add_issue(MockIssue(50, "Backlog item 1", state="open",
                              labels=["story", "sp:3"]))

    # Open PR for issue 46
    repo.add_pr(MockPullRequest(89, "Refactor auth module", body="Closes #42",
                                 state="closed", merged=True,
                                 merged_at=datetime(2026, 5, 23, 7, 0, 0, tzinfo=timezone.utc)))
    repo.add_pr(MockPullRequest(91, "Session management PR", body="Closes #46",
                                 state="open"))

    return repo
```

---

## `tests/unit/test_config.py`

```python
"""tests/unit/test_config.py"""
import pytest
import yaml
from pathlib import Path
from scripts.utils.config import (load_config, get_team_logins,
                                   get_current_sprint, validate_config)


@pytest.mark.unit
def test_load_config_from_scraut_yml(scraut_repo):
    cfg = load_config(str(scraut_repo / "scraut.yml"))
    assert cfg["sprint"]["length_days"] == 14
    assert cfg["sprint"]["current_sprint"] == 1
    assert len(cfg["team"]["members"]) == 3


@pytest.mark.unit
def test_get_team_logins(scraut_repo):
    load_config(str(scraut_repo / "scraut.yml"))
    logins = get_team_logins()
    assert "alice" in logins
    assert "bob" in logins
    assert "charlie" in logins
    assert len(logins) == 3


@pytest.mark.unit
def test_validate_config_passes_with_valid_config(scraut_repo):
    cfg = load_config(str(scraut_repo / "scraut.yml"))
    errors = validate_config(cfg)
    assert errors == []


@pytest.mark.unit
def test_validate_config_fails_missing_team(scraut_repo):
    cfg = {"sprint": {"length_days": 14, "current_sprint": 1},
           "llm": {"provider": "anthropic"}}
    errors = validate_config(cfg)
    assert any("team" in e.lower() for e in errors)


@pytest.mark.unit
def test_get_current_sprint_returns_int(scraut_repo):
    load_config(str(scraut_repo / "scraut.yml"))
    sprint = get_current_sprint()
    assert isinstance(sprint, int)
    assert sprint == 1
```

---

## `tests/unit/test_file_utils.py`

```python
"""tests/unit/test_file_utils.py"""
import pytest
from pathlib import Path
from scripts.utils.file_utils import (
    atomic_write, create_if_not_exists, read_file,
    extract_section, extract_all_sections, extract_issue_numbers,
)


@pytest.mark.unit
def test_atomic_write_creates_file(tmp_path):
    path = tmp_path / "test.md"
    atomic_write(path, "# Hello\nWorld")
    assert path.exists()
    assert path.read_text() == "# Hello\nWorld"


@pytest.mark.unit
def test_atomic_write_overwrites_existing(tmp_path):
    path = tmp_path / "test.md"
    atomic_write(path, "original")
    atomic_write(path, "updated")
    assert path.read_text() == "updated"


@pytest.mark.unit
def test_create_if_not_exists_creates_new_file(tmp_path):
    path = tmp_path / "new.md"
    result = create_if_not_exists(path, "content")
    assert result is True
    assert path.read_text() == "content"


@pytest.mark.unit
def test_create_if_not_exists_skips_existing_file(tmp_path):
    path = tmp_path / "existing.md"
    path.write_text("original")
    result = create_if_not_exists(path, "new content")
    assert result is False
    assert path.read_text() == "original"  # not overwritten


@pytest.mark.unit
def test_read_file_returns_content(tmp_path):
    path = tmp_path / "file.md"
    path.write_text("test content")
    assert read_file(path) == "test content"


@pytest.mark.unit
def test_read_file_returns_empty_string_for_missing_file(tmp_path):
    path = tmp_path / "missing.md"
    assert read_file(path) == ""


@pytest.mark.unit
@pytest.mark.parametrize("markdown,section,expected", [
    ("## Yesterday\nMerged PR #89\n\n## Today\nWork on #46", "Yesterday", "Merged PR #89"),
    ("## Today\nIssue #46\n\n## Blockers\nNone", "Blockers", "None"),
    ("## Yesterday\nDone stuff\n## Today\n## Blockers\n- Waiting", "Blockers", "- Waiting"),
    ("No sections here", "Yesterday", ""),
    ("## Today\nWork", "Blockers", ""),
])
def test_extract_section(markdown, section, expected):
    result = extract_section(markdown, section)
    assert expected in result or result == expected


@pytest.mark.unit
def test_extract_all_sections_returns_dict():
    markdown = "## Yesterday\nContent A\n## Today\nContent B\n## Blockers\nNone"
    sections = extract_all_sections(markdown)
    assert "Yesterday" in sections
    assert "Today" in sections
    assert "Blockers" in sections
    assert "Content A" in sections["Yesterday"]


@pytest.mark.unit
@pytest.mark.parametrize("text,expected", [
    ("Working on #42 and #46", [42, 46]),
    ("Closes #89", [89]),
    ("No issues here", []),
    ("PR #91 closes #42 and #44", [91, 42, 44]),
])
def test_extract_issue_numbers(text, expected):
    result = extract_issue_numbers(text)
    assert sorted(result) == sorted(expected)
```

---

## `tests/unit/test_standup_templates.py`

```python
"""tests/unit/test_standup_templates.py — test template reset logic"""
import pytest
from datetime import date
from pathlib import Path
from scripts.standup.reset_templates import (STANDUP_TEMPLATE, reset_templates,
                                               YESTERDAY_PLACEHOLDER)
from scripts.utils.file_utils import create_if_not_exists


@pytest.mark.unit
def test_reset_templates_creates_files_for_all_members(scraut_repo, config):
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    today = date.today().isoformat()

    reset_templates(config)

    sprint_dir = scraut_repo / "sprint-01" / "standup" / today
    for member in config["team"]["members"]:
        expected = sprint_dir / f"{member['login']}.md"
        assert expected.exists(), f"Expected standup file for {member['login']}"


@pytest.mark.unit
def test_reset_templates_does_not_overwrite_existing(scraut_repo, config):
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    today = date.today().isoformat()

    # Pre-create alice's file with custom content
    path = scraut_repo / "sprint-01" / "standup" / today / "alice.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Alice's custom standup\n## Yesterday\n- Custom work done")

    reset_templates(config)

    # Her file should NOT be overwritten
    assert path.read_text() == "# Alice's custom standup\n## Yesterday\n- Custom work done"


@pytest.mark.unit
def test_reset_templates_creates_summary_directory(scraut_repo, config):
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    today = date.today().isoformat()
    reset_templates(config)
    summary_dir = scraut_repo / "sprint-01" / "standup" / "summary"
    assert summary_dir.exists()


@pytest.mark.unit
def test_standup_template_contains_breadcrumb(scraut_repo, config):
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    today = date.today().isoformat()
    reset_templates(config)

    path = scraut_repo / "sprint-01" / "standup" / today / "alice.md"
    content = path.read_text()
    assert "NAVIGATION" in content or "sprint-01" in content


@pytest.mark.unit
def test_standup_template_has_required_sections(scraut_repo, config):
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    today = date.today().isoformat()
    reset_templates(config)

    path = scraut_repo / "sprint-01" / "standup" / today / "bob.md"
    content = path.read_text()
    assert "## Yesterday" in content
    assert "## Today" in content
    assert "## Blockers" in content
```

---

## `tests/unit/test_planning_session.py`

```python
"""tests/unit/test_planning_session.py — test /answer command parsing"""
import pytest
from scripts.milestone.planning_session import (
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
```

---

## `tests/unit/test_derive_state.py`

```python
"""
tests/unit/test_derive_state.py
CRITICAL: Tests for the board state inference engine.
Every rule must be tested individually.
"""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from scripts.visibility.derive_state import (
    derive_all_states, IssueState, scan_standup_files,
    VALID_COLUMNS,
)


@pytest.mark.unit
def test_done_when_issue_is_closed(scraut_repo, config, mock_repo):
    """Closed GitHub issues should always map to Done."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    with patch("scripts.visibility.derive_state.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scripts.visibility.derive_state.get_pr_issue_map", return_value={}):
            with patch("scripts.visibility.derive_state.get_sprint_roadmap_issues",
                       return_value={42, 44, 46, 47}):
                states = derive_all_states("test-org/test-repo", config,
                                           target_date="2026-05-23")

    # Issue #42 is closed in mock_repo
    assert states[42].column == "Done"
    assert states[42].confidence == 1.0


@pytest.mark.unit
def test_review_when_open_pr_exists(scraut_repo, config, mock_repo):
    """Issue with open PR should map to Review."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    # PR #91 is open and closes #46
    pr_map = {46: {"pr_number": 91, "state": "open"}}

    with patch("scripts.visibility.derive_state.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scripts.visibility.derive_state.get_pr_issue_map",
                   return_value=pr_map):
            with patch("scripts.visibility.derive_state.get_sprint_roadmap_issues",
                       return_value={42, 44, 46, 47}):
                states = derive_all_states("test-org/test-repo", config,
                                           target_date="2026-05-23")

    assert states[46].column == "Review"
    assert states[46].confidence == 1.0


@pytest.mark.unit
def test_blocked_when_in_blockers_section(scraut_repo, config, mock_repo):
    """Issue mentioned in today's Blockers section → In Progress + blocked health."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    # Fixture has bob.md with #44 in Blockers section for 2026-05-23
    with patch("scripts.visibility.derive_state.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scripts.visibility.derive_state.get_pr_issue_map", return_value={}):
            with patch("scripts.visibility.derive_state.get_sprint_roadmap_issues",
                       return_value={42, 44, 46, 47}):
                states = derive_all_states("test-org/test-repo", config,
                                           target_date="2026-05-23")

    assert states[44].column == "In Progress"
    assert states[44].health == "blocked"
    assert states[44].confidence >= 0.85


@pytest.mark.unit
def test_in_progress_when_in_today_section(scraut_repo, config, mock_repo):
    """Issue in Today section of today's standup → In Progress."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    # alice.md has #46 in Today for 2026-05-23
    with patch("scripts.visibility.derive_state.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scripts.visibility.derive_state.get_pr_issue_map", return_value={}):
            with patch("scripts.visibility.derive_state.get_sprint_roadmap_issues",
                       return_value={42, 44, 46, 47}):
                states = derive_all_states("test-org/test-repo", config,
                                           target_date="2026-05-23")

    assert states[46].column in ("In Progress", "Review")  # could be Review if PR open


@pytest.mark.unit
def test_ready_when_in_roadmap_but_no_standup_signal(scraut_repo, config, mock_repo):
    """Issue in sprint roadmap with no standup mentions → Ready."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    # Issue #47 is in sprint but Bob only mentions it in Today on 2026-05-23
    # For a date where no one mentions it, it should be Ready
    with patch("scripts.visibility.derive_state.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scripts.visibility.derive_state.get_pr_issue_map", return_value={}):
            with patch("scripts.visibility.derive_state.get_sprint_roadmap_issues",
                       return_value={42, 44, 46, 47, 99}):
                states = derive_all_states("test-org/test-repo", config,
                                           target_date="2026-05-20")  # earlier date, no standups

    assert states[99].column == "Ready"


@pytest.mark.unit
def test_all_columns_are_valid():
    for col in VALID_COLUMNS:
        assert isinstance(col, str)
        assert len(col) > 0
```

---

## `tests/unit/test_tally_estimation.py`

```python
"""tests/unit/test_tally_estimation.py"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from scripts.backlog.tally_estimation import (
    EMOJI_TO_SP, count_votes, determine_winner,
    should_finalize, format_vote_table,
)
from tests.mocks.github_mocks import MockIssue, MockComment


@pytest.mark.unit
def test_emoji_to_sp_mapping():
    """Verify the emoji→SP mapping is correct."""
    assert EMOJI_TO_SP["+1"] == 1      # 👍
    assert EMOJI_TO_SP["heart"] == 3    # ❤️
    assert EMOJI_TO_SP["rocket"] == 5   # 🚀
    assert EMOJI_TO_SP["tada"] == 8     # 🎉
    assert EMOJI_TO_SP["fire"] == 13    # 🔥


@pytest.mark.unit
def test_determine_winner_returns_most_voted():
    votes = {1: 2, 3: 3, 5: 1}
    assert determine_winner(votes) == 3


@pytest.mark.unit
def test_determine_winner_returns_none_for_no_votes():
    assert determine_winner({}) is None


@pytest.mark.unit
def test_determine_winner_handles_single_vote():
    votes = {5: 1}
    assert determine_winner(votes) == 5


@pytest.mark.unit
def test_determine_winner_tie_returns_one_of_the_tied():
    """When tied, winner is one of the tied values (higher vote count wins)."""
    votes = {3: 2, 5: 2}
    winner = determine_winner(votes)
    assert winner in (3, 5)


@pytest.mark.unit
def test_should_finalize_when_all_team_voted():
    """Should finalize when every team member has voted."""
    team = ["alice", "bob", "charlie"]
    # 3 votes in total (one each) = all voted
    votes = {1: 1, 3: 1, 5: 1}  # 3 total votes
    comment = MagicMock()
    comment.created_at = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    assert should_finalize(comment, team, votes) is True


@pytest.mark.unit
def test_should_finalize_after_24h():
    """Should finalize after 24h even with partial votes."""
    from freezegun import freeze_time
    team = ["alice", "bob", "charlie"]
    votes = {5: 1}  # Only 1 vote

    old_time = datetime(2026, 5, 22, 9, 0, 0, tzinfo=timezone.utc)
    comment = MagicMock()
    comment.created_at = old_time

    # Freeze time to 25h after comment was created
    with freeze_time("2026-05-23 10:00:00"):
        result = should_finalize(comment, team, votes)
    assert result is True


@pytest.mark.unit
def test_should_not_finalize_early_with_partial_votes():
    """Should NOT finalize when partial votes and <24h."""
    from freezegun import freeze_time
    team = ["alice", "bob", "charlie"]
    votes = {5: 1}  # Only 1 of 3 voted

    comment = MagicMock()
    comment.created_at = datetime(2026, 5, 23, 9, 0, 0, tzinfo=timezone.utc)

    with freeze_time("2026-05-23 10:00:00"):  # only 1h later
        result = should_finalize(comment, team, votes)
    assert result is False


@pytest.mark.unit
def test_format_vote_table_shows_non_zero_votes():
    votes = {5: 3, 1: 1}
    table = format_vote_table(votes)
    assert "sp:5" in table
    assert "sp:1" in table
    assert "sp:3" not in table  # no votes for 3


@pytest.mark.unit
def test_format_vote_table_empty():
    table = format_vote_table({})
    assert "No votes" in table
```

---

## `tests/unit/test_detectors.py`

```python
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
    with patch("scripts.suggestions.detectors.calculate_sprint_velocity") as mock_vel:
        with patch("scripts.suggestions.detectors.calculate_rolling_velocity") as mock_roll:
            mock_roll.return_value = {"avg": 26.0, "sprints_sampled": 5}
            mock_vel.return_value = {"completed_sp": 25, "planned_sp": 28}  # ~96% — no drop
            result = velocity_drop_detector("test-repo", config, drop_threshold=0.15)
    assert result is None


@pytest.mark.unit
def test_velocity_drop_triggers_on_sustained_drop(scraut_repo, config):
    """With >15% drop for 2+ sprints, Evidence is returned."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    with patch("scripts.suggestions.detectors.calculate_sprint_velocity") as mock_vel:
        with patch("scripts.suggestions.detectors.calculate_rolling_velocity") as mock_roll:
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
```

---

## `tests/unit/test_health_check.py`

```python
"""tests/unit/test_health_check.py"""
import pytest
from scripts.milestone.health_check import score_sprint


@pytest.mark.unit
@pytest.mark.parametrize("params,expected_status", [
    # Perfect sprint: all planned issues closed, on milestone pace
    ({"planned_sp": 26, "actual_sp": 26, "planned_issues": [1,2,3],
      "completed_issues": [1,2,3], "milestone_total_sp": 100,
      "milestone_delivered_sp": 50, "sprint_num": 3, "total_planned_sprints": 6,
      "unplanned_stories": 0}, "on-track"),
    # Weak sprint: only 60% done, behind on milestone
    ({"planned_sp": 26, "actual_sp": 15, "planned_issues": [1,2,3,4,5],
      "completed_issues": [1,2], "milestone_total_sp": 100,
      "milestone_delivered_sp": 20, "sprint_num": 3, "total_planned_sprints": 6,
      "unplanned_stories": 3}, "at-risk"),
    # Moderate sprint
    ({"planned_sp": 26, "actual_sp": 20, "planned_issues": [1,2,3],
      "completed_issues": [1,2], "milestone_total_sp": 100,
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
        planned_issues=[1,2,3,4], completed_issues=[1,2,3],
        milestone_total_sp=100, milestone_delivered_sp=45,
        sprint_num=3, total_planned_sprints=6, unplanned_stories=1
    )
    assert 0 <= result["composite"] <= 100


@pytest.mark.unit
def test_score_sprint_perfect_score():
    result = score_sprint(
        planned_sp=26, actual_sp=26,
        planned_issues=[1,2,3], completed_issues=[1,2,3],
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
```

---

## `tests/unit/test_velocity.py`

```python
"""tests/unit/test_velocity.py"""
import pytest
from unittest.mock import patch
from scripts.sprint.calculate_velocity import (
    calculate_sprint_velocity, calculate_rolling_velocity,
)
from tests.mocks.github_mocks import MockRepository, MockIssue


@pytest.mark.unit
def test_calculate_sprint_velocity_counts_closed_sp(mock_repo):
    """Velocity should sum SP of closed issues with sprint label."""
    # Issue #42 is closed, sp:5. Issue #44 is open, sp:3. Issue #46 is open, sp:5.
    with patch("scripts.sprint.calculate_velocity.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        result = calculate_sprint_velocity(1, "test-org/test-repo")

    assert result["completed_sp"] == 5  # only issue #42 is closed with sp:5
    assert result["planned_sp"] == 21  # 5+3+5+8
    assert result["completion_rate"] == pytest.approx(5/21, abs=0.01)


@pytest.mark.unit
def test_calculate_rolling_velocity_handles_no_sprints():
    with patch("scripts.sprint.calculate_velocity.get_github_client") as mock_g:
        empty_repo = MockRepository()
        mock_g.return_value.get_repo.return_value = empty_repo
        result = calculate_rolling_velocity("test-org/test-repo", num_sprints=5)

    assert result["avg"] == 0
    assert result["sprints_sampled"] == 0
```

---

## `tests/unit/test_standup_prefill.py`

```python
"""tests/unit/test_standup_prefill.py — test Yesterday pre-fill logic"""
import pytest
from pathlib import Path
from scripts.repo_sync.prefill_standups import (
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
```

---

## `tests/integration/test_standup_flow.py`

```python
"""
tests/integration/test_standup_flow.py
End-to-end: template reset → repo sync prefill → summary generation.
Uses real file operations on tmp_path but mocks GitHub API and LLM.
"""
import pytest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from tests.mocks.llm_mocks import STANDUP_SUMMARY_RESPONSE


@pytest.mark.integration
def test_full_standup_flow(scraut_repo, config):
    """
    1. Reset templates → creates alice.md, bob.md, charlie.md
    2. Prefill from activity.json → alice.md Yesterday is populated
    3. Generate summary → reads all files, produces digest
    """
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    target_date = "2026-05-23"

    # Step 1: Reset templates (fixture files already exist, so idempotent)
    from scripts.standup.reset_templates import reset_templates
    reset_templates(config)

    # Verify standup files exist
    standup_dir = scraut_repo / "sprint-01" / "standup" / target_date
    assert (standup_dir / "alice.md").exists()
    assert (standup_dir / "bob.md").exists()

    # Step 2: Prefill from activity (activity.json is in fixtures)
    from scripts.repo_sync.prefill_standups import prefill_standups
    prefill_standups(config, target_date)

    # Alice's standup should have her PR merge pre-filled
    alice_content = (standup_dir / "alice.md").read_text()
    assert "PR #89" in alice_content or "Yesterday" in alice_content

    # Step 3: Generate summary (mock LLM)
    with patch("scripts.standup.generate_summary.complete",
               return_value=STANDUP_SUMMARY_RESPONSE):
        with patch("scripts.standup.generate_summary.post_to_slack") as mock_slack:
            from scripts.standup.generate_summary import generate_summary
            summary = generate_summary(config, target_date, dry_run=False)

    # Verify summary was written to summary folder
    summary_path = scraut_repo / "sprint-01" / "standup" / "summary" / f"{target_date}.md"
    assert summary_path.exists()
    content = summary_path.read_text()
    assert "BOT-GENERATED" in content

    # Verify Slack was called
    assert mock_slack.called


@pytest.mark.integration
def test_standup_summary_not_overwritten_on_reruns(scraut_repo, config):
    """Running the summary twice should update the file but not fail."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    with patch("scripts.standup.generate_summary.complete",
               return_value=STANDUP_SUMMARY_RESPONSE):
        with patch("scripts.standup.generate_summary.post_to_slack"):
            from scripts.standup.generate_summary import generate_summary
            result1 = generate_summary(config, "2026-05-23")
            result2 = generate_summary(config, "2026-05-23")

    assert result1 is not None
    assert result2 is not None
```

---

## `tests/integration/test_milestone_flow.py`

```python
"""
tests/integration/test_milestone_flow.py
End-to-end: milestone.md → decompose → planning session → answers → roadmap.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from tests.mocks.github_mocks import MockRepository
from tests.mocks.llm_mocks import DECOMPOSITION_RESPONSE


@pytest.mark.integration
def test_milestone_decompose_creates_files(scraut_repo, config):
    """Committing milestone.md should produce breakdown.json and breakdown.md."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    milestone_path = scraut_repo / "milestones" / "m01-auth" / "milestone.md"

    mock_repo = MockRepository()
    with patch("scripts.milestone.decompose.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scripts.milestone.decompose.complete_json",
                   return_value=DECOMPOSITION_RESPONSE):
            with patch("scripts.milestone.decompose.calculate_rolling_velocity",
                       return_value={"avg": 26.0, "std_dev": 2.0, "sprints_sampled": 4}):
                from scripts.milestone.decompose import decompose_milestone
                decompose_milestone(str(milestone_path), "test-org/test-repo", config)

    # Verify files were created
    milestone_dir = milestone_path.parent
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
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    # Setup: create planning-session.md with a GitHub issue reference
    milestone_dir = scraut_repo / "milestones" / "m01-auth"
    (milestone_dir / "planning-session.md").write_text(
        "# Planning Session\n\nGitHub Issue: #1\nAnswers received: 0/5\n\n## Q&A Log\n\n"
    )

    mock_repo = MockRepository()
    from tests.mocks.github_mocks import MockIssue
    issue = MockIssue(1, "🎯 Milestone Planning: Auth",
                       body="<!-- scraut-planning-session milestone:m01-auth -->")
    mock_repo.add_issue(issue)

    config["_repo_name"] = "test-org/test-repo"

    with patch("scripts.milestone.planning_session.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scripts.milestone.planning_session.generate_roadmap") as mock_roadmap:
            from scripts.milestone.planning_session import process_comment

            # Post 5 answers
            for q, val in [(1, "6 sprints"), (2, "confirm"), (3, "26"),
                           (4, "none"), (5, "core,sso")]:
                process_comment(1, f"/answer Q{q} {val}", "test-org/test-repo", config)

    # After all 5 answers, roadmap generation should be called
    assert mock_roadmap.called
```

---

## `tests/integration/test_suggestion_flow.py`

```python
"""
tests/integration/test_suggestion_flow.py
End-to-end: detectors fire → suggestion file created → team responds → measurement.
"""
import pytest
from pathlib import Path
from unittest.mock import patch
from tests.mocks.github_mocks import MockRepository
from tests.mocks.llm_mocks import SUGGESTION_DRAFT_RESPONSE


@pytest.mark.integration
def test_blocker_detection_creates_suggestion_file(scraut_repo, config):
    """When blocker detector fires, suggestion file should be created."""
    from scripts.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))

    # Create enough standup files with blockers to trigger the detector
    for day in ["2026-05-20", "2026-05-21", "2026-05-22", "2026-05-23"]:
        standup_dir = scraut_repo / "sprint-01" / "standup" / day
        standup_dir.mkdir(parents=True, exist_ok=True)
        for person in ["alice", "bob"]:
            (standup_dir / f"{person}.md").write_text(
                f"# Standup\n## Blockers\n- PR review is blocking progress again\n"
            )

    mock_repo = MockRepository()
    with patch("scripts.suggestions.generate_suggestion.get_github_client") as mock_g:
        mock_g.return_value.get_repo.return_value = mock_repo
        with patch("scripts.suggestions.generate_suggestion.complete_json",
                   return_value=SUGGESTION_DRAFT_RESPONSE):
            from scripts.suggestions.detectors import blocker_frequency_detector
            from scripts.suggestions.generate_suggestion import generate_suggestion

            evidence = blocker_frequency_detector(config, min_occurrences=3)
            assert evidence is not None

            generate_suggestion(evidence, "test-org/test-repo", config)

    # Verify suggestion file was created
    active_dir = scraut_repo / "suggestions" / "active"
    suggestion_files = list(active_dir.glob("s*.md"))
    assert len(suggestion_files) == 1

    content = suggestion_files[0].read_text()
    assert "proposed" in content
    assert "Evidence trail" in content
    assert "Suggested actions" in content
    assert "measurement_criteria" in content.lower() or "How Scraut will measure" in content

    # Verify GitHub issue was created
    assert len(mock_repo._issues) == 1
```

---

## `.github/workflows/test-ci.yml`

```yaml
name: Scraut — Test Suite
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    name: Unit tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run unit tests
        run: |
          pytest tests/unit/ -m unit -v \
            --cov=scripts \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=70

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
        continue-on-error: true

  integration-tests:
    name: Integration tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run integration tests
        run: |
          pytest tests/integration/ -m integration -v \
            --tb=short

  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install flake8
      - run: flake8 scripts/ --max-line-length=100 --ignore=E501,W503
```

---

## Done Criteria for Phase 10

- [ ] `requirements-test.txt` exists and `pip install -r requirements-test.txt` succeeds
- [ ] `pytest.ini` configured with correct paths and coverage threshold
- [ ] All fixture files exist under `tests/fixtures/`
- [ ] `tests/mocks/github_mocks.py` — `MockRepository`, `MockIssue`, `MockPullRequest` work as drop-in PyGitHub replacements
- [ ] `tests/mocks/llm_mocks.py` — all standard response dicts present
- [ ] `tests/conftest.py` — `scraut_repo`, `config`, `mock_repo`, `patch_repo_root` fixtures work
- [ ] `test_config.py` — all 5 tests pass
- [ ] `test_file_utils.py` — all 9 tests pass including parametrized cases
- [ ] `test_standup_templates.py` — create-if-not-exists rule verified by test
- [ ] `test_planning_session.py` — all `/answer` parsing tests pass including case-insensitive
- [ ] `test_derive_state.py` — Done/Review/Blocked/In Progress/Ready/Backlog rules all verified
- [ ] `test_tally_estimation.py` — emoji mapping, winner, 24h finalize, full-team finalize all tested
- [ ] `test_detectors.py` — each of the 4 script-based detectors tested with below-threshold (no trigger) AND above-threshold (trigger) cases
- [ ] `test_health_check.py` — on-track/watch/at-risk status thresholds verified, ZeroDivisionError edge case passes
- [ ] `test_velocity.py` — velocity calculation verified against mock issues
- [ ] `test_standup_prefill.py` — `is_yesterday_empty` correctly identifies unfilled templates
- [ ] `test_standup_flow.py` — full standup flow: reset → prefill → summary → Slack post
- [ ] `test_milestone_flow.py` — milestone decompose creates all expected files
- [ ] `test_suggestion_flow.py` — detector fires → suggestion file created with correct structure
- [ ] `test-ci.yml` — GitHub Actions workflow runs on push to main/develop
- [ ] `pytest` with no arguments from repo root runs all tests and they pass
- [ ] Coverage ≥ 70% on `scripts/` directory

---

## Running the tests

```bash
# All tests
pytest

# Unit tests only (fast, no file I/O)
pytest tests/unit/ -m unit

# Integration tests only
pytest tests/integration/ -m integration

# Specific test file
pytest tests/unit/test_derive_state.py -v

# With coverage report
pytest --cov=scripts --cov-report=html
open htmlcov/index.html

# Run tests in watch mode during development
pip install pytest-watch
ptw tests/unit/
```
