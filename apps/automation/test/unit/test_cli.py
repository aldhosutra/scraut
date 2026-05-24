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
    timezone="UTC",
    provider="anthropic",
    slack_webhook="",
):
    return "\n".join([repo, team, po, sm, channel, sprint_days, timezone, provider, slack_webhook])


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
        assert (tmp_path / "workspace" / "sprint" / "01" / "standup").is_dir()
        assert (tmp_path / "workspace" / "sprint" / "01" / "retrospective").is_dir()

    def test_scraut_output_dirs_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        CliRunner().invoke(cli, ["init"], input=_init_input())
        assert (tmp_path / ".scraut" / "suggestions" / "active").is_dir()
        assert (tmp_path / ".scraut" / "sprint" / "01" / "standup" / "summary").is_dir()

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
