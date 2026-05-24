"""
scripts/utils/config.py
Load and validate scraut.yml. Provides a global CONFIG object.
"""
import os
import yaml
from pathlib import Path
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

_config: Optional[dict] = None
_config_path: Optional[Path] = None


def load_config(config_path: Optional[str] = None) -> dict:
    """Load scraut.yml from repo root or specified path."""
    global _config, _config_path

    if config_path:
        path = Path(config_path)
    else:
        # Search upward from cwd for scraut.yml
        cwd = Path.cwd()
        for parent in [cwd] + list(cwd.parents):
            candidate = parent / "scraut.yml"
            if candidate.exists():
                path = candidate
                break
        else:
            raise FileNotFoundError("scraut.yml not found in directory tree")

    with open(path) as f:
        config = yaml.safe_load(f)

    _config = config
    _config_path = path.parent
    logger.info(f"Loaded config from {path}")
    return config


def get_config() -> dict:
    """Return cached config, loading if necessary."""
    if _config is None:
        load_config()
    return _config


def get_repo_root() -> Path:
    """Return the repository root directory (where scraut.yml lives)."""
    if _config_path is None:
        load_config()
    return _config_path


def get_current_sprint() -> int:
    return get_config()["sprint"]["current_sprint"]


def get_team_members() -> list[dict]:
    return get_config()["team"]["members"]


def get_team_logins() -> list[str]:
    return [m["login"] for m in get_team_members()]


def get_display_name(login: str) -> str:
    for m in get_team_members():
        if m["login"] == login:
            return m["display"]
    return login


def get_sprint_folder(sprint_num: Optional[int] = None) -> Path:
    if sprint_num is None:
        sprint_num = get_current_sprint()
    return get_repo_root() / f"sprint-{sprint_num:02d}"


def get_llm_config() -> dict:
    return get_config().get("llm", {})


def validate_config(config: dict) -> list[str]:
    """Return list of validation errors. Empty = valid."""
    errors = []
    required = ["sprint", "team", "llm"]
    for field in required:
        if field not in config:
            errors.append(f"Missing required field: {field}")

    if "members" not in config.get("team", {}):
        errors.append("team.members must be a list")

    if not config.get("team", {}).get("members"):
        errors.append("team.members cannot be empty")

    return errors


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Path to scraut.yml")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.validate:
        errors = validate_config(cfg)
        if errors:
            for e in errors:
                print(f"ERROR: {e}")
            sys.exit(1)
        print("Config valid ✓")
