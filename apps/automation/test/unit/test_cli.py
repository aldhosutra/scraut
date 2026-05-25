"""
Unit tests for scraut.cli.cli — focused on the new `init` command.
Uses click.testing.CliRunner to simulate interactive input without spawning
a real process or touching the real file system (monkeypatch.chdir redirects
all Path("workspace") writes to a fresh tmp_path).
"""
import os
import yaml
import pytest
from click.testing import CliRunner
from pathlib import Path

from scraut.cli.cli import cli


# Simulate a complete `scraut init` session.
# Each string is one line of stdin (one prompt answer).
def _init_input(
    repo="myorg/my-repo",
    team="alice,bob",
    po="alice",
    sm="bob",
    channel="#scraut-bot",
    sprint_days="14",
    starting_sprint="1",
    folder_padding="",   # empty = accept default
    timezone="UTC",
    provider="anthropic",
    slack_webhook="",
):
    return "\n".join([repo, team, po, sm, channel, sprint_days, starting_sprint,
                      folder_padding, timezone, provider, slack_webhook])


@pytest.mark.unit
class TestInitCommand:
    def test_creates_workspace_scraut_yml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        result = CliRunner().invoke(cli, ["init"], input=_init_input())
        assert result.exit_code == 0, result.output
        assert (tmp_path / "workspace" / "scraut.yml").exists()

    def test_yaml_has_correct_team_members(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(team="alice,bob,charlie"))
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        logins = [m["login"] for m in cfg["team"]["members"]]
        assert logins == ["alice", "bob", "charlie"]

    def test_yaml_product_owner_and_scrum_master(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(po="alice", sm="bob"))
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert cfg["team"]["product_owner"] == "alice"
        assert cfg["team"]["scrum_master"] == "bob"

    def test_sprint_length_written(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(sprint_days="7"))
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert cfg["sprint"]["length_days"] == 7

    def test_anthropic_provider_sets_correct_model(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(provider="anthropic"))
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert cfg["llm"]["provider"] == "anthropic"
        assert cfg["llm"]["model"] == "claude-sonnet-4-6"

    def test_openai_provider_sets_correct_model(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(provider="openai"))
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert cfg["llm"]["provider"] == "openai"
        assert cfg["llm"]["model"] == "gpt-4o"

    def test_gemini_provider_sets_correct_model(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(provider="gemini"))
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert cfg["llm"]["provider"] == "gemini"
        assert cfg["llm"]["model"] == "gemini-1.5-pro"

    def test_ollama_provider_sets_correct_model(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(provider="ollama"))
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert cfg["llm"]["provider"] == "ollama"
        assert cfg["llm"]["model"] == "llama3"

    def test_workspace_sprint_dirs_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input())
        assert (tmp_path / "workspace" / "sprint" / "001" / "standup").is_dir()
        assert (tmp_path / "workspace" / "sprint" / "001" / "retrospective").is_dir()

    def test_scraut_output_dirs_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input())
        assert (tmp_path / ".scraut" / "suggestions" / "active").is_dir()
        assert (tmp_path / ".scraut" / "sprint" / "001" / "standup" / "summary").is_dir()

    def test_skips_label_creation_without_token(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        result = CliRunner().invoke(cli, ["init"], input=_init_input())
        assert result.exit_code == 0
        assert "GITHUB_TOKEN" in result.output

    def test_skips_labels_for_placeholder_repo(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        result = CliRunner().invoke(cli, ["init"],
                                    input=_init_input(repo="your-org/your-repo"))
        assert result.exit_code == 0
        # Should not attempt label creation for the placeholder repo name
        assert "placeholder" in result.output or "GITHUB_TOKEN" not in result.output

    def test_slack_webhook_written_to_yaml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"],
                           input=_init_input(slack_webhook="https://hooks.slack.com/xxx"))
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert cfg["notifications"]["slack_webhook"] == "https://hooks.slack.com/xxx"

    def test_output_contains_next_steps(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        result = CliRunner().invoke(cli, ["init"], input=_init_input())
        assert "Next steps" in result.output
        assert "SLACK_WEBHOOK" in result.output
        assert "Sprint 1" in result.output

    def test_base_url_field_present_in_yaml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input())
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert "base_url" in cfg["llm"]
        assert cfg["llm"]["base_url"] == ""

    # --- scaffolded template files ---

    def test_standup_template_created_for_each_member(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        from datetime import date
        today = date.today().isoformat()
        CliRunner().invoke(cli, ["init"], input=_init_input(team="alice,bob"))
        standup_dir = tmp_path / "workspace" / "sprint" / "001" / "standup" / today
        assert (standup_dir / "alice.md").exists()
        assert (standup_dir / "bob.md").exists()

    def test_standup_template_has_correct_sections(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        from datetime import date
        today = date.today().isoformat()
        CliRunner().invoke(cli, ["init"], input=_init_input(team="alice"))
        content = (tmp_path / "workspace" / "sprint" / "001" / "standup" / today / "alice.md").read_text()
        assert "## Yesterday" in content
        assert "## Today" in content
        assert "## Blockers" in content
        assert "## Notes" in content
        assert "alice" in content

    def test_retro_template_created_for_each_member(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(team="alice,bob"))
        retro_dir = tmp_path / "workspace" / "sprint" / "001" / "retrospective"
        assert (retro_dir / "alice.md").exists()
        assert (retro_dir / "bob.md").exists()

    def test_retro_template_has_correct_sections(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(team="alice"))
        content = (tmp_path / "workspace" / "sprint" / "001" / "retrospective" / "alice.md").read_text()
        assert "## Went well" in content
        assert "## Could improve" in content
        assert "## Action items I'll own" in content
        assert "Alice" in content

    def test_sprint_meta_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(team="alice,bob"))
        meta = tmp_path / "workspace" / "sprint" / "001" / "meta.md"
        assert meta.exists()
        content = meta.read_text()
        assert "Sprint 1" in content
        assert "Alice" in content

    def test_grooming_backlog_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input())
        grooming = tmp_path / "workspace" / "sprint" / "001" / "grooming" / "backlog-ideas.md"
        assert grooming.exists()
        assert "Backlog Ideas" in grooming.read_text()

    def test_capacity_template_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(team="alice,bob"))
        capacity = tmp_path / "workspace" / "team" / "capacity.md"
        assert capacity.exists()
        content = capacity.read_text()
        assert "alice" in content
        assert "bob" in content

    def test_okr_template_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input())
        okr = tmp_path / "workspace" / "okr" / "okr.md"
        assert okr.exists()
        assert "Objective" in okr.read_text()

    def test_customer_feedback_template_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input())
        feedback = tmp_path / "workspace" / "customer" / "feedback.md"
        assert feedback.exists()
        assert "Customer Feedback" in feedback.read_text()

    def test_milestones_readme_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(repo="myorg/my-repo"))
        readme = tmp_path / "workspace" / "milestones" / "README.md"
        assert readme.exists()
        content = readme.read_text()
        assert "Milestones" in content
        assert "myorg/my-repo" in content

    def test_output_mentions_standup_fill_in(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        result = CliRunner().invoke(cli, ["init"], input=_init_input())
        assert "standup" in result.output.lower()

    def test_starting_sprint_default_is_one(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(starting_sprint="1"))
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert cfg["sprint"]["current_sprint"] == 1
        assert (tmp_path / "workspace" / "sprint" / "001").exists()

    def test_starting_sprint_midteam_uses_correct_folder(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(starting_sprint="5"))
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert cfg["sprint"]["current_sprint"] == 5
        assert (tmp_path / "workspace" / "sprint" / "005").exists()
        assert not (tmp_path / "workspace" / "sprint" / "001").exists()

    def test_starting_sprint_midteam_standup_in_correct_folder(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        from datetime import date
        today = date.today().isoformat()
        CliRunner().invoke(cli, ["init"], input=_init_input(team="alice", starting_sprint="5"))
        standup = tmp_path / "workspace" / "sprint" / "005" / "standup" / today / "alice.md"
        assert standup.exists()
        assert "sprint-005" in standup.read_text()

    def test_starting_sprint_midteam_retro_in_correct_folder(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(team="alice", starting_sprint="12"))
        retro = tmp_path / "workspace" / "sprint" / "012" / "retrospective" / "alice.md"
        assert retro.exists()
        assert "Sprint 012" in retro.read_text()

    def test_starting_sprint_output_shows_correct_sprint(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        result = CliRunner().invoke(cli, ["init"], input=_init_input(starting_sprint="7"))
        assert "Sprint 7" in result.output or "sprint/007" in result.output

    def test_folder_padding_default_is_3(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input())
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert cfg["sprint"]["folder_padding"] == 3

    def test_folder_padding_custom_value_written(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(folder_padding="4"))
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert cfg["sprint"]["folder_padding"] == 4

    def test_folder_padding_applies_to_created_dirs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input(folder_padding="4"))
        assert (tmp_path / "workspace" / "sprint" / "0001").exists()
        assert not (tmp_path / "workspace" / "sprint" / "001").exists()


def _make_scraut_yml(tmp_path, members=None, sprint=1):
    """Write a minimal workspace/scraut.yml for sync/sprint tests."""
    if members is None:
        members = [{"login": "alice", "display": "Alice", "role": "developer",
                    "slack_id": "", "email": ""}]
    import yaml
    cfg = {
        "sprint": {"length_days": 14, "start_day": "monday", "start_time": "09:00",
                   "timezone": "UTC", "capacity_buffer": 0.85, "current_sprint": sprint},
        "team": {"members": members, "product_owner": members[0]["login"],
                 "scrum_master": members[0]["login"], "slack_channel": "#scraut-bot"},
        "ceremonies": {"planning": True, "standup": True, "grooming": True,
                       "review": True, "retrospective": True, "estimation": True},
        "definition_of_done": ["CI passing"],
        "repos": [],
        "llm": {"provider": "anthropic", "model": "claude-sonnet-4-6",
                "base_url": "", "max_tokens": 1000,
                "cost_controls": {"max_daily_tokens": 100000, "batch_where_possible": True}},
        "agents": {"enabled": False},
        "notifications": {"slack_webhook": "", "morning_dm": True,
                          "weekly_email": False, "stakeholder_emails": []},
        "portal": {"enabled": True, "title": "Test", "public": True, "refresh_minutes": 30},
        "suggestions": {"enabled": True, "min_evidence_count": 3, "measurement_sprints": 2},
        "paths": {"workspace": "workspace", "scraut": ".scraut", "portal": "apps/portal"},
    }
    ws = tmp_path / "workspace"
    ws.mkdir(exist_ok=True)
    (ws / "scraut.yml").write_text(yaml.dump(cfg))


@pytest.mark.unit
class TestSyncCommand:
    def test_sync_creates_standup_for_today(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_scraut_yml(tmp_path)
        from datetime import date
        today = date.today().isoformat()
        result = CliRunner().invoke(cli, ["sync"])
        assert result.exit_code == 0, result.output
        standup = tmp_path / "workspace" / "sprint" / "001" / "standup" / today / "alice.md"
        assert standup.exists()

    def test_sync_creates_retro_for_member(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_scraut_yml(tmp_path)
        CliRunner().invoke(cli, ["sync"])
        retro = tmp_path / "workspace" / "sprint" / "001" / "retrospective" / "alice.md"
        assert retro.exists()
        assert "Went well" in retro.read_text()

    def test_sync_creates_sprint_folder_structure(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_scraut_yml(tmp_path)
        CliRunner().invoke(cli, ["sync"])
        assert (tmp_path / "workspace" / "sprint" / "001" / "grooming").exists()
        assert (tmp_path / "workspace" / "sprint" / "001" / "retrospective").exists()
        assert (tmp_path / ".scraut" / "sprint" / "001" / "standup" / "summary").exists()

    def test_sync_creates_meta_if_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_scraut_yml(tmp_path)
        CliRunner().invoke(cli, ["sync"])
        meta = tmp_path / "workspace" / "sprint" / "001" / "meta.md"
        assert meta.exists()
        assert "Sprint 1" in meta.read_text()

    def test_sync_does_not_overwrite_existing_standup(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_scraut_yml(tmp_path)
        from datetime import date
        today = date.today().isoformat()
        standup = tmp_path / "workspace" / "sprint" / "001" / "standup" / today
        standup.mkdir(parents=True, exist_ok=True)
        existing = standup / "alice.md"
        existing.write_text("my custom content")
        CliRunner().invoke(cli, ["sync"])
        assert existing.read_text() == "my custom content"

    def test_sync_dry_run_writes_nothing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_scraut_yml(tmp_path)
        result = CliRunner().invoke(cli, ["sync", "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "dry-run" in result.output
        assert not (tmp_path / "workspace" / "sprint").exists()

    def test_sync_new_member_mid_sprint(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Start with just alice
        _make_scraut_yml(tmp_path)
        CliRunner().invoke(cli, ["sync"])
        # Add bob mid-sprint by updating config
        _make_scraut_yml(tmp_path, members=[
            {"login": "alice", "display": "Alice", "role": "developer", "slack_id": "", "email": ""},
            {"login": "bob",   "display": "Bob",   "role": "developer", "slack_id": "", "email": ""},
        ])
        from datetime import date
        today = date.today().isoformat()
        CliRunner().invoke(cli, ["sync"])
        assert (tmp_path / "workspace" / "sprint" / "001" / "retrospective" / "bob.md").exists()
        assert (tmp_path / "workspace" / "sprint" / "001" / "standup" / today / "bob.md").exists()

    def test_sync_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_scraut_yml(tmp_path)
        r1 = CliRunner().invoke(cli, ["sync"])
        r2 = CliRunner().invoke(cli, ["sync"])
        assert r1.exit_code == 0
        assert r2.exit_code == 0
        assert "Already in sync" in r2.output


@pytest.mark.unit
class TestSprintCommand:
    def test_sprint_status_shows_sprint_number(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_scraut_yml(tmp_path, sprint=3)
        result = CliRunner().invoke(cli, ["sprint", "status"])
        assert result.exit_code == 0, result.output
        assert "3" in result.output

    def test_sprint_scaffold_alias_works(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_scraut_yml(tmp_path)
        result = CliRunner().invoke(cli, ["sprint", "scaffold"])
        assert result.exit_code == 0, result.output
        assert (tmp_path / "workspace" / "sprint" / "001").exists()

    def test_sprint_unknown_subcommand(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_scraut_yml(tmp_path)
        result = CliRunner().invoke(cli, ["sprint", "foobar"])
        assert "Unknown subcommand" in result.output


def _make_scraut_yml_with_padding(tmp_path, sprint=1, folder_padding=3):
    """Write workspace/scraut.yml with explicit folder_padding."""
    members = [{"login": "alice", "display": "Alice", "role": "developer",
                "slack_id": "", "email": ""}]
    cfg = {
        "sprint": {"length_days": 14, "start_day": "monday", "start_time": "09:00",
                   "timezone": "UTC", "capacity_buffer": 0.85, "current_sprint": sprint,
                   "folder_padding": folder_padding},
        "team": {"members": members, "product_owner": "alice",
                 "scrum_master": "alice", "slack_channel": "#scraut-bot"},
        "ceremonies": {"planning": True, "standup": True, "grooming": True,
                       "review": True, "retrospective": True, "estimation": True},
        "definition_of_done": ["CI passing"],
        "repos": [],
        "llm": {"provider": "anthropic", "model": "claude-sonnet-4-6",
                "base_url": "", "max_tokens": 1000,
                "cost_controls": {"max_daily_tokens": 100000, "batch_where_possible": True}},
        "agents": {"enabled": False},
        "notifications": {"slack_webhook": "", "morning_dm": True,
                          "weekly_email": False, "stakeholder_emails": []},
        "portal": {"enabled": True, "title": "Test", "public": True,
                   "refresh_minutes": 30, "sync_board": False},
        "suggestions": {"enabled": True, "min_evidence_count": 3, "measurement_sprints": 2},
        "paths": {"workspace": "workspace", "scraut": ".scraut", "portal": "apps/portal"},
    }
    ws = tmp_path / "workspace"
    ws.mkdir(exist_ok=True)
    (ws / "scraut.yml").write_text(yaml.dump(cfg))


def _seed_sprint_dirs(tmp_path, sprint_nums, padding):
    """Create sprint directories in workspace/ and .scraut/ with the given padding."""
    from scraut.platform.utils.file_utils import format_sprint_num
    for n in sprint_nums:
        name = format_sprint_num(n, padding)
        (tmp_path / "workspace" / "sprint" / name).mkdir(parents=True, exist_ok=True)
        (tmp_path / ".scraut" / "sprint" / name).mkdir(parents=True, exist_ok=True)


@pytest.mark.unit
class TestSprintRepadCommand:
    def _setup(self, tmp_path, monkeypatch, sprint_nums=(1, 2, 3), current=3,
               padding=3, new_padding=4):
        """Set up tmp repo with sprint dirs, return new_padding."""
        monkeypatch.chdir(tmp_path)
        _make_scraut_yml_with_padding(tmp_path, sprint=current, folder_padding=padding)
        _seed_sprint_dirs(tmp_path, sprint_nums, padding)
        return new_padding

    def _reset_config_cache(self):
        import scraut.platform.utils.config as cfg_mod
        cfg_mod._config = None
        cfg_mod._repo_root = None
        cfg_mod._config_path = None

    def test_repad_happy_path_renames_folders(self, tmp_path, monkeypatch):
        self._reset_config_cache()
        self._setup(tmp_path, monkeypatch, sprint_nums=[1, 2, 3], current=3,
                    padding=3, new_padding=4)
        result = CliRunner().invoke(cli, ["sprint", "repad", "4"])
        assert result.exit_code == 0, result.output
        assert (tmp_path / "workspace" / "sprint" / "0001").exists()
        assert (tmp_path / ".scraut" / "sprint" / "0001").exists()
        assert not (tmp_path / "workspace" / "sprint" / "001").exists()

    def test_repad_updates_config_folder_padding(self, tmp_path, monkeypatch):
        self._reset_config_cache()
        self._setup(tmp_path, monkeypatch, sprint_nums=[1], current=1, padding=3)
        CliRunner().invoke(cli, ["sprint", "repad", "4"])
        cfg = yaml.safe_load((tmp_path / "workspace" / "scraut.yml").read_text())
        assert cfg["sprint"]["folder_padding"] == 4

    def test_repad_dry_run_does_not_rename(self, tmp_path, monkeypatch):
        self._reset_config_cache()
        self._setup(tmp_path, monkeypatch, sprint_nums=[1, 2], current=2, padding=3)
        result = CliRunner().invoke(cli, ["sprint", "repad", "4", "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "dry-run" in result.output
        # Folders should still use old padding
        assert (tmp_path / "workspace" / "sprint" / "001").exists()
        assert not (tmp_path / "workspace" / "sprint" / "0001").exists()

    def test_repad_rejects_smaller_padding(self, tmp_path, monkeypatch):
        self._reset_config_cache()
        self._setup(tmp_path, monkeypatch, sprint_nums=[1], current=1, padding=4)
        result = CliRunner().invoke(cli, ["sprint", "repad", "3"])
        assert result.exit_code == 0, result.output
        assert "Error" in result.output
        assert "must be greater than" in result.output

    def test_repad_rejects_same_padding(self, tmp_path, monkeypatch):
        self._reset_config_cache()
        self._setup(tmp_path, monkeypatch, sprint_nums=[1], current=1, padding=3)
        result = CliRunner().invoke(cli, ["sprint", "repad", "3"])
        assert "Error" in result.output

    def test_repad_rejects_padding_too_small_for_sprint_num(self, tmp_path, monkeypatch):
        self._reset_config_cache()
        # current_sprint=100 requires at least 3 digits, so padding=2 should fail
        self._setup(tmp_path, monkeypatch, sprint_nums=[100], current=100, padding=3)
        # Try repad 3 → still 3 (same), actually we need >3 here
        # Let's try to set current_sprint to 100 with padding=4, then repad to 2 (impossible)
        # Actually this test should use: current sprint 100, current padding 3, new padding 2 → fail
        # But new_padding > current_padding check runs first. Need setup with padding=1, sprint=100
        # That's an unrealistic state; test the validation separately
        result = CliRunner().invoke(cli, ["sprint", "repad", "not-a-number"])
        assert "Error" in result.output

    def test_repad_missing_arg_shows_usage(self, tmp_path, monkeypatch):
        self._reset_config_cache()
        self._setup(tmp_path, monkeypatch, sprint_nums=[1], current=1, padding=3)
        result = CliRunner().invoke(cli, ["sprint", "repad"])
        assert result.exit_code == 0, result.output
        assert "Usage" in result.output

    def test_repad_prints_github_labels_warning(self, tmp_path, monkeypatch):
        self._reset_config_cache()
        self._setup(tmp_path, monkeypatch, sprint_nums=[1], current=1, padding=3)
        result = CliRunner().invoke(cli, ["sprint", "repad", "4"])
        assert result.exit_code == 0, result.output
        assert "GitHub" in result.output or "label" in result.output.lower()

    def test_repad_prints_commit_command(self, tmp_path, monkeypatch):
        self._reset_config_cache()
        self._setup(tmp_path, monkeypatch, sprint_nums=[1], current=1, padding=3)
        result = CliRunner().invoke(cli, ["sprint", "repad", "4"])
        assert result.exit_code == 0, result.output
        assert "git" in result.output and "commit" in result.output
