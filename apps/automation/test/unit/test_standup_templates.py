"""test/unit/test_standup_templates.py — test template reset logic"""
import pytest
from datetime import date
from pathlib import Path
from scraut.scrum.standup.reset_templates import (STANDUP_TEMPLATE, reset_templates,
                                               YESTERDAY_PLACEHOLDER)
from scraut.platform.utils.file_utils import create_if_not_exists


@pytest.mark.unit
def test_reset_templates_creates_files_for_all_members(scraut_repo, config):
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    today = date.today().isoformat()

    reset_templates(config)

    sprint_dir = scraut_repo / "sprint" / "01" / "standup" / today
    for member in config["team"]["members"]:
        expected = sprint_dir / f"{member['login']}.md"
        assert expected.exists(), f"Expected standup file for {member['login']}"


@pytest.mark.unit
def test_reset_templates_does_not_overwrite_existing(scraut_repo, config):
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    today = date.today().isoformat()

    # Pre-create alice's file with custom content
    path = scraut_repo / "sprint" / "01" / "standup" / today / "alice.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Alice's custom standup\n## Yesterday\n- Custom work done")

    reset_templates(config)

    # Her file should NOT be overwritten
    assert path.read_text() == "# Alice's custom standup\n## Yesterday\n- Custom work done"


@pytest.mark.unit
def test_reset_templates_creates_summary_directory(scraut_repo, config):
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    today = date.today().isoformat()
    reset_templates(config)
    summary_dir = scraut_repo / ".scraut" / "sprint" / "01" / "standup" / "summary"
    assert summary_dir.exists()


@pytest.mark.unit
def test_standup_template_contains_breadcrumb(scraut_repo, config):
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    today = date.today().isoformat()
    reset_templates(config)

    path = scraut_repo / "sprint" / "01" / "standup" / today / "alice.md"
    content = path.read_text()
    assert "NAVIGATION" in content or "sprint-01" in content


@pytest.mark.unit
def test_standup_template_has_required_sections(scraut_repo, config):
    from scraut.platform.utils.config import load_config
    load_config(str(scraut_repo / "scraut.yml"))
    today = date.today().isoformat()
    reset_templates(config)

    path = scraut_repo / "sprint" / "01" / "standup" / today / "bob.md"
    content = path.read_text()
    assert "## Yesterday" in content
    assert "## Today" in content
    assert "## Blockers" in content
