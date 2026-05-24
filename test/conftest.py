"""
test/conftest.py
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
        "scraut.platform.utils.config._config_path",
        scraut_repo,
    )
    monkeypatch.setattr(
        "scraut.platform.utils.config._config",
        None,  # force reload from test scraut.yml
    )
    import os
    monkeypatch.chdir(scraut_repo)


@pytest.fixture
def mock_repo():
    """Return a MockRepository pre-populated with common test issues."""
    from test.mocks.github_mocks import MockRepository, MockIssue, MockPullRequest
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
