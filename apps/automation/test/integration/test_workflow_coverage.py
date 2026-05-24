"""
Integration tests: verify every Python script referenced in .github/workflows/*.yml
exists on disk and exits cleanly when run with --help.

This catches two failure modes that unit tests miss:
  1. A workflow references a script path that was renamed or deleted.
  2. A script has a broken argument parser or top-level import error.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[4]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

_SCRIPT_RE = re.compile(r"python\s+(apps/automation/scraut/\S+?\.py)")


def _collect_workflow_scripts() -> list[str]:
    scripts: set[str] = set()
    for wf in WORKFLOWS_DIR.glob("*.yml"):
        for m in _SCRIPT_RE.finditer(wf.read_text()):
            scripts.add(m.group(1))
    return sorted(scripts)


_WORKFLOW_SCRIPTS = _collect_workflow_scripts()


@pytest.mark.integration
@pytest.mark.parametrize("script", _WORKFLOW_SCRIPTS)
def test_script_exists(script):
    assert (REPO_ROOT / script).is_file(), f"Script referenced in workflow not found: {script}"


@pytest.mark.integration
@pytest.mark.parametrize("script", _WORKFLOW_SCRIPTS)
def test_script_help(script):
    """Every workflow script must have a working --help (proves argparse is wired up)."""
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "apps" / "automation")}
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / script), "--help"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"`python {script} --help` exited {result.returncode}\n"
        f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
    )
