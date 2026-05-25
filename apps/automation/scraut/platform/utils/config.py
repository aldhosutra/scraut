"""
lib/utils/config.py
Load and validate scraut.yml. Provides a global CONFIG object.
"""
import os
import yaml
from pathlib import Path
from typing import Any, Optional
import logging

from scraut.platform.utils.file_utils import format_sprint_num  # noqa: F401 — re-exported for callers

logger = logging.getLogger(__name__)

_config: Optional[dict] = None
_repo_root: Optional[Path] = None
_config_path: Optional[Path] = None


def _resolve_repo_root(config_file: Path) -> Path:
    """Return the repo root given the resolved path to scraut.yml.

    When scraut.yml lives inside workspace/ the repo root is one level up;
    otherwise the repo root is the directory that contains scraut.yml.
    """
    if config_file.parent.name == "workspace":
        return config_file.parent.parent
    return config_file.parent


def _find_config() -> tuple[Path, Path]:
    """Search upward from CWD for scraut.yml.

    Checks workspace/scraut.yml before scraut.yml at each level so that
    repos which store the config inside workspace/ are found correctly.
    Returns (config_path, repo_root).
    """
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        ws_candidate = parent / "workspace" / "scraut.yml"
        if ws_candidate.exists():
            return ws_candidate, parent
        candidate = parent / "scraut.yml"
        if candidate.exists():
            return candidate, parent
    raise FileNotFoundError("scraut.yml not found in directory tree")


def load_config(config_path: Optional[str] = None) -> dict:
    """Load scraut.yml from repo root (or workspace/) or a specified path."""
    global _config, _repo_root, _config_path

    if config_path:
        path = Path(config_path).resolve()
        root = _resolve_repo_root(path)
    else:
        path, root = _find_config()

    with open(path) as f:
        config = yaml.safe_load(f)

    _config = config
    _repo_root = root
    _config_path = path
    logger.info(f"Loaded config from {path}")
    return config


def get_config() -> dict:
    """Return cached config, loading if necessary."""
    if _config is None:
        load_config()
    return _config


def get_config_path() -> Path:
    """Return the path to the loaded scraut.yml."""
    if _config_path is None:
        load_config()
    return _config_path


def get_repo_root() -> Path:
    """Return the repository root directory (parent of workspace/, or where scraut.yml lives)."""
    if _repo_root is None:
        load_config()
    return _repo_root


def get_workspace_root() -> Path:
    """Return the human-editable Scraut workspace directory.

    Files under this root are source-of-truth inputs owned by the team.
    Older/test fixtures without a workspace directory continue to work from
    the repo root.
    """
    root = get_repo_root()
    workspace_name = get_config().get("paths", {}).get("workspace", "workspace")
    workspace = root / workspace_name
    return workspace if workspace.exists() else root


def get_scraut_root() -> Path:
    """Return the generated Scraut artifact/state directory."""
    root = get_repo_root()
    scraut_name = get_config().get("paths", {}).get("scraut", ".scraut")
    return root / scraut_name


def get_portal_root() -> Path:
    """Return the deployable portal app directory."""
    root = get_repo_root()
    portal_path = get_config().get("paths", {}).get("portal", "apps/portal")
    portal = root / portal_path
    return portal if portal.exists() else root / "portal"


def get_current_sprint() -> int:
    return get_config()["sprint"]["current_sprint"]


def get_folder_padding() -> int:
    """Return the sprint folder zero-padding width from config (default 3)."""
    return int(get_config().get("sprint", {}).get("folder_padding", 3))


_DAY_NAME_TO_INT: dict[str, int] = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
_DEFAULT_WORK_DAYS: frozenset[int] = frozenset({0, 1, 2, 3, 4})  # Mon–Fri


def get_work_days(config: Optional[dict] = None) -> frozenset[int]:
    """Return the set of working weekday integers (0=Mon … 6=Sun).

    Reads sprint.work_days from config (list of lowercase day names).
    Defaults to Monday–Friday if the field is absent or empty.
    """
    cfg = config or get_config()
    raw = cfg.get("sprint", {}).get("work_days") or []
    if not raw:
        return _DEFAULT_WORK_DAYS
    result: set[int] = set()
    for name in raw:
        key = str(name).strip().lower()
        if key in _DAY_NAME_TO_INT:
            result.add(_DAY_NAME_TO_INT[key])
        else:
            logger.warning(f"Unknown work_day value {name!r} — expected a weekday name")
    return frozenset(result) if result else _DEFAULT_WORK_DAYS


def get_team_members() -> list[dict]:
    return get_config()["team"]["members"]


def get_team_logins() -> list[str]:
    return [m["login"] for m in get_team_members()]


def get_sprint_folder(sprint_num: Optional[int] = None) -> Path:
    """Return the human-editable sprint input folder."""
    if sprint_num is None:
        sprint_num = get_current_sprint()
    return get_workspace_root() / "sprint" / format_sprint_num(sprint_num, get_folder_padding())


def get_sprint_output_folder(sprint_num: Optional[int] = None) -> Path:
    """Return the generated sprint output folder."""
    if sprint_num is None:
        sprint_num = get_current_sprint()
    return get_scraut_root() / "sprint" / format_sprint_num(sprint_num, get_folder_padding())


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
