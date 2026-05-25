"""
lib/utils/file_utils.py
Atomic file operations, markdown parsing, template rendering.
"""
import os
import tempfile
import shutil
from pathlib import Path
from datetime import date
from typing import Optional
import re
import logging

logger = logging.getLogger(__name__)


def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write content atomically: write to temp file, then rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding=encoding, dir=path.parent,
        delete=False, suffix=".tmp"
    ) as f:
        f.write(content)
        tmp_path = f.name
    os.replace(tmp_path, path)
    logger.debug(f"Wrote {path}")


def create_if_not_exists(path: Path, content: str) -> bool:
    """Create file only if it does not already exist. Returns True if created."""
    path = Path(path)
    if path.exists():
        logger.debug(f"Skipped (exists): {path}")
        return False
    atomic_write(path, content)
    logger.info(f"Created: {path}")
    return True


def read_file(path: Path) -> str:
    """Read a file, return empty string if not found."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def extract_section(markdown: str, section_header: str) -> str:
    """
    Extract content of a markdown section by header name.
    e.g., extract_section(text, "Blockers") returns everything under ## Blockers
    until the next ## header.
    """
    pattern = rf"##\s+{re.escape(section_header)}\s*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, markdown, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_all_sections(markdown: str) -> dict[str, str]:
    """Extract all ## sections from a markdown file as a dict."""
    sections = {}
    pattern = r"##\s+(.+?)\s*\n(.*?)(?=\n##\s|\Z)"
    for match in re.finditer(pattern, markdown, re.DOTALL):
        header = match.group(1).strip()
        content = match.group(2).strip()
        sections[header] = content
    return sections


def extract_issue_numbers(text: str) -> list[int]:
    """Extract all #NNN issue references from text."""
    return [int(n) for n in re.findall(r"#(\d+)", text)]


def render_template(template_str: str, **kwargs) -> str:
    """Simple template rendering using {variable} substitution."""
    from jinja2 import Template
    return Template(template_str).render(**kwargs)


def today_str() -> str:
    return date.today().isoformat()


def format_sprint_num(sprint_num: int, padding: int = 3) -> str:
    """Return the canonical zero-padded sprint number string.

    `padding` is the minimum field width (default 3). Pass `get_folder_padding()`
    from config.py at every call site so the width tracks the configured value.
    """
    return f"{sprint_num:0{padding}d}"


def sprint_folder_name(sprint_num: int, padding: int = 3) -> str:
    return f"sprint/{format_sprint_num(sprint_num, padding)}"
