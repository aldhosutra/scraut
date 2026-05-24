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
