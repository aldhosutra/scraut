"""tests/unit/test_file_utils.py"""
import pytest
from pathlib import Path
from scripts.utils.file_utils import (
    atomic_write, create_if_not_exists, read_file,
    extract_section, extract_all_sections, extract_issue_numbers,
)


@pytest.mark.unit
def test_atomic_write_creates_file(tmp_path):
    path = tmp_path / "test.md"
    atomic_write(path, "# Hello\nWorld")
    assert path.exists()
    assert path.read_text() == "# Hello\nWorld"


@pytest.mark.unit
def test_atomic_write_overwrites_existing(tmp_path):
    path = tmp_path / "test.md"
    atomic_write(path, "original")
    atomic_write(path, "updated")
    assert path.read_text() == "updated"


@pytest.mark.unit
def test_create_if_not_exists_creates_new_file(tmp_path):
    path = tmp_path / "new.md"
    result = create_if_not_exists(path, "content")
    assert result is True
    assert path.read_text() == "content"


@pytest.mark.unit
def test_create_if_not_exists_skips_existing_file(tmp_path):
    path = tmp_path / "existing.md"
    path.write_text("original")
    result = create_if_not_exists(path, "new content")
    assert result is False
    assert path.read_text() == "original"  # not overwritten


@pytest.mark.unit
def test_read_file_returns_content(tmp_path):
    path = tmp_path / "file.md"
    path.write_text("test content")
    assert read_file(path) == "test content"


@pytest.mark.unit
def test_read_file_returns_empty_string_for_missing_file(tmp_path):
    path = tmp_path / "missing.md"
    assert read_file(path) == ""


@pytest.mark.unit
@pytest.mark.parametrize("markdown,section,expected", [
    ("## Yesterday\nMerged PR #89\n\n## Today\nWork on #46", "Yesterday", "Merged PR #89"),
    ("## Today\nIssue #46\n\n## Blockers\nNone", "Blockers", "None"),
    ("## Yesterday\nDone stuff\n## Today\n## Blockers\n- Waiting", "Blockers", "- Waiting"),
    ("No sections here", "Yesterday", ""),
    ("## Today\nWork", "Blockers", ""),
])
def test_extract_section(markdown, section, expected):
    result = extract_section(markdown, section)
    assert expected in result or result == expected


@pytest.mark.unit
def test_extract_all_sections_returns_dict():
    markdown = "## Yesterday\nContent A\n## Today\nContent B\n## Blockers\nNone"
    sections = extract_all_sections(markdown)
    assert "Yesterday" in sections
    assert "Today" in sections
    assert "Blockers" in sections
    assert "Content A" in sections["Yesterday"]


@pytest.mark.unit
@pytest.mark.parametrize("text,expected", [
    ("Working on #42 and #46", [42, 46]),
    ("Closes #89", [89]),
    ("No issues here", []),
    ("PR #91 closes #42 and #44", [91, 42, 44]),
])
def test_extract_issue_numbers(text, expected):
    result = extract_issue_numbers(text)
    assert sorted(result) == sorted(expected)
