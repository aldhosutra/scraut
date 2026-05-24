"""
Unit tests for the inline Python snippets embedded in .github/workflows/*.yml.

The orchestrator checks agents.enabled; each agent-*.yml checks
agents.enabled AND that specific role is enabled.  These code paths have
no other coverage because they run as `python -c "..."` inside bash steps.
"""
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[4]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

# Maps each agent workflow file to the role id it checks.
AGENT_ROLE_WORKFLOWS = {
    "agent-backend.yml": "agent-backend",
    "agent-frontend.yml": "agent-frontend",
    "agent-review.yml": "agent-review",
    "agent-test.yml": "agent-test",
}


# ---------------------------------------------------------------------------
# Logic mirrors — identical to what the workflow one-liners do
# ---------------------------------------------------------------------------

def _orchestrator_enabled(cfg_path: Path) -> str:
    """Mirror of the 'Check if agent mode is enabled' step in agent-orchestrator.yml."""
    cfg = yaml.safe_load(cfg_path.read_text())
    return str(cfg.get("agents", {}).get("enabled", False)).lower()


def _agent_role_enabled(cfg_path: Path, role_id: str) -> str:
    """Mirror of the 'Check if agent mode enabled' step in agent-*.yml."""
    cfg = yaml.safe_load(cfg_path.read_text())
    agents = cfg.get("agents", {})
    enabled = agents.get("enabled", False)
    roles = {r["id"]: r.get("enabled", False) for r in agents.get("roles", [])}
    return str(enabled and roles.get(role_id, False)).lower()


# ---------------------------------------------------------------------------
# Orchestrator check
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestOrchestratorAgentCheck:
    def test_enabled(self, tmp_path):
        f = tmp_path / "scraut.yml"
        f.write_text("agents:\n  enabled: true\n")
        assert _orchestrator_enabled(f) == "true"

    def test_disabled(self, tmp_path):
        f = tmp_path / "scraut.yml"
        f.write_text("agents:\n  enabled: false\n")
        assert _orchestrator_enabled(f) == "false"

    def test_missing_agents_key(self, tmp_path):
        f = tmp_path / "scraut.yml"
        f.write_text("sprint:\n  current_sprint: 1\n")
        assert _orchestrator_enabled(f) == "false"


# ---------------------------------------------------------------------------
# Agent role checks
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAgentRoleCheck:
    @pytest.mark.parametrize("role_id", list(AGENT_ROLE_WORKFLOWS.values()))
    def test_global_disabled_blocks_role(self, tmp_path, role_id):
        f = tmp_path / "scraut.yml"
        f.write_text(f"agents:\n  enabled: false\n  roles:\n    - id: {role_id}\n      enabled: true\n")
        assert _agent_role_enabled(f, role_id) == "false"

    @pytest.mark.parametrize("role_id", list(AGENT_ROLE_WORKFLOWS.values()))
    def test_both_enabled(self, tmp_path, role_id):
        f = tmp_path / "scraut.yml"
        f.write_text(f"agents:\n  enabled: true\n  roles:\n    - id: {role_id}\n      enabled: true\n")
        assert _agent_role_enabled(f, role_id) == "true"

    @pytest.mark.parametrize("role_id", list(AGENT_ROLE_WORKFLOWS.values()))
    def test_role_disabled(self, tmp_path, role_id):
        f = tmp_path / "scraut.yml"
        f.write_text(f"agents:\n  enabled: true\n  roles:\n    - id: {role_id}\n      enabled: false\n")
        assert _agent_role_enabled(f, role_id) == "false"

    @pytest.mark.parametrize("role_id", list(AGENT_ROLE_WORKFLOWS.values()))
    def test_role_absent_from_list(self, tmp_path, role_id):
        f = tmp_path / "scraut.yml"
        f.write_text("agents:\n  enabled: true\n  roles: []\n")
        assert _agent_role_enabled(f, role_id) == "false"


# ---------------------------------------------------------------------------
# Regression: workflows must open workspace/scraut.yml, not scraut.yml
# ---------------------------------------------------------------------------

_AGENT_WORKFLOW_FILES = list(AGENT_ROLE_WORKFLOWS.keys()) + ["agent-orchestrator.yml"]


@pytest.mark.unit
@pytest.mark.parametrize("workflow_file", _AGENT_WORKFLOW_FILES)
def test_workflow_opens_workspace_scraut_yml(workflow_file):
    content = (WORKFLOWS_DIR / workflow_file).read_text()
    assert "open('workspace/scraut.yml')" in content, (
        f"{workflow_file} must open workspace/scraut.yml — "
        "scraut.yml was moved from repo root to workspace/ and workflows must reflect that"
    )
