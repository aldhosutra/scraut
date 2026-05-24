# Phase 1: Foundation
*Scraut Implementation — Part of the master roadmap in `00-ROADMAP.md`*

## Goal
Scaffold the complete repository skeleton, configuration system, Python utility layer,
GitHub API wrappers, and issue templates. Everything subsequent phases depend on.

## Prerequisites
- Empty GitHub repository created for Scraut
- Python 3.11+ installed locally (for testing scripts)
- `pip install -r requirements.txt` will be runnable after this phase

## What to Build

---

### 1. `requirements.txt`

```
anthropic>=0.28.0
openai>=1.30.0
PyGitHub>=2.3.0
requests>=2.31.0
PyYAML>=6.0.1
matplotlib>=3.8.0
Pillow>=10.3.0
python-dotenv>=1.0.0
click>=8.1.7
jinja2>=3.1.4
```

---

### 2. `scraut.yml` (default config — copy of full schema from ROADMAP)

Create a minimal working `scraut.yml` at repo root with sensible defaults.
Use the full schema from `00-ROADMAP.md`. All fields must be present with defaults.
Fields marked with `""` are placeholders that humans fill in before first use.

---

### 3. `scripts/utils/config.py`

Load, validate, and expose scraut.yml globally.

```python
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
```

---

### 4. `scripts/utils/file_utils.py`

```python
"""
scripts/utils/file_utils.py
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


def sprint_folder_name(sprint_num: int) -> str:
    return f"sprint-{sprint_num:02d}"
```

---

### 5. `scripts/utils/date_utils.py`

```python
"""
scripts/utils/date_utils.py
Sprint date calculations and scheduling utilities.
"""
from datetime import date, timedelta, datetime
from typing import Optional
import pytz


def get_sprint_dates(sprint_num: int, config: dict) -> tuple[date, date]:
    """
    Calculate start and end dates for a given sprint number.
    Uses sprint.length_days and sprint.start_day from config.
    """
    # Sprint 1 starts at a configured epoch date
    # For simplicity, calculate from a known sprint-1 start
    # If sprint-1 start not configured, use today as sprint-1 start
    sprint_cfg = config["sprint"]
    length = sprint_cfg["length_days"]
    epoch = date.today()  # Fallback; actual epoch set in scraut.yml after first sprint

    start = epoch + timedelta(days=(sprint_num - 1) * length)
    end = start + timedelta(days=length - 1)
    return start, end


def working_days_remaining(end_date: date) -> int:
    """Count working days (Mon-Fri) between today and end_date."""
    today = date.today()
    count = 0
    current = today
    while current <= end_date:
        if current.weekday() < 5:  # Monday=0, Friday=4
            count += 1
        current += timedelta(days=1)
    return count


def working_days_elapsed(start_date: date) -> int:
    """Count working days from start_date to today."""
    today = date.today()
    count = 0
    current = start_date
    while current < today:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def is_weekday(d: Optional[date] = None) -> bool:
    if d is None:
        d = date.today()
    return d.weekday() < 5


def localize_time(naive_dt: datetime, timezone_str: str) -> datetime:
    tz = pytz.timezone(timezone_str)
    return tz.localize(naive_dt)
```

---

### 6. `scripts/github/api.py`

Complete GitHub REST API wrapper with retry logic.

```python
"""
scripts/github/api.py
GitHub REST API wrapper using PyGitHub + raw requests.
All calls include retry logic and rate limit handling.
"""
import os
import time
import logging
from typing import Optional, Any
from github import Github, GithubException
from github.Repository import Repository
from github.Issue import Issue
from github.PullRequest import PullRequest
import requests

logger = logging.getLogger(__name__)


def get_github_client(token: Optional[str] = None) -> Github:
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("SCRAUT_GITHUB_TOKEN")
    if not token:
        raise ValueError("GitHub token not found. Set GITHUB_TOKEN or SCRAUT_GITHUB_TOKEN env var.")
    return Github(token)


def get_repo(repo_name: str, token: Optional[str] = None) -> Repository:
    """Get a GitHub repository by 'org/repo' name."""
    g = get_github_client(token)
    return g.get_repo(repo_name)


def get_issues(repo: Repository, milestone_title: Optional[str] = None,
               labels: Optional[list] = None, state: str = "open") -> list[Issue]:
    """Get issues filtered by milestone and/or labels."""
    kwargs = {"state": state}
    if labels:
        kwargs["labels"] = labels
    issues = list(repo.get_issues(**kwargs))
    if milestone_title:
        issues = [i for i in issues
                  if i.milestone and i.milestone.title == milestone_title]
    return issues


def create_issue(repo: Repository, title: str, body: str,
                 labels: Optional[list] = None,
                 milestone_number: Optional[int] = None,
                 assignees: Optional[list] = None) -> Issue:
    """Create a GitHub issue."""
    kwargs = {"title": title, "body": body}
    if labels:
        kwargs["labels"] = labels
    if milestone_number:
        kwargs["milestone"] = repo.get_milestone(milestone_number)
    if assignees:
        kwargs["assignees"] = assignees
    return repo.create_issue(**kwargs)


def create_milestone(repo: Repository, title: str, description: str = "") -> Any:
    return repo.create_milestone(title=title, description=description)


def close_milestone(repo: Repository, title: str) -> None:
    for ms in repo.get_milestones(state="open"):
        if ms.title == title:
            ms.edit(state="closed")
            return
    logger.warning(f"Milestone '{title}' not found to close")


def add_label_to_issue(issue: Issue, label_name: str) -> None:
    try:
        issue.add_to_labels(label_name)
    except GithubException as e:
        logger.error(f"Failed to add label {label_name}: {e}")


def remove_label_from_issue(issue: Issue, label_name: str) -> None:
    try:
        issue.remove_from_labels(label_name)
    except GithubException:
        pass  # Label wasn't applied, ignore


def post_comment(issue: Issue, body: str) -> Any:
    return issue.create_comment(body)


def get_sp_from_issue(issue: Issue) -> int:
    """Extract story points from issue labels (sp:N)."""
    for label in issue.labels:
        if label.name.startswith("sp:"):
            try:
                return int(label.name.split(":")[1])
            except ValueError:
                pass
    return 0


def set_sp_on_issue(repo: Repository, issue: Issue, points: int) -> None:
    """Remove all sp: labels and add the correct one."""
    valid_sp = [1, 2, 3, 5, 8, 13]
    points = min(valid_sp, key=lambda x: abs(x - points))
    for label in issue.labels:
        if label.name.startswith("sp:"):
            issue.remove_from_labels(label.name)
    ensure_label_exists(repo, f"sp:{points}", color="0075ca")
    issue.add_to_labels(f"sp:{points}")


def ensure_label_exists(repo: Repository, name: str,
                        color: str = "ededed", description: str = "") -> None:
    """Create label if it doesn't exist."""
    try:
        repo.get_label(name)
    except GithubException:
        repo.create_label(name=name, color=color, description=description)


def commit_file(repo: Repository, path: str, content: str, message: str,
                branch: str = "main") -> None:
    """Create or update a file in the repository via API."""
    try:
        existing = repo.get_contents(path, ref=branch)
        repo.update_file(path, message, content, existing.sha, branch=branch)
    except GithubException:
        repo.create_file(path, message, content, branch=branch)


def get_file_content(repo: Repository, path: str, ref: str = "main") -> Optional[str]:
    """Get file content from repository, return None if not found."""
    try:
        content = repo.get_contents(path, ref=ref)
        return content.decoded_content.decode("utf-8")
    except GithubException:
        return None


def file_exists(repo: Repository, path: str, ref: str = "main") -> bool:
    try:
        repo.get_contents(path, ref=ref)
        return True
    except GithubException:
        return False


def with_retry(func, max_attempts: int = 3, base_delay: float = 1.0):
    """Execute func with exponential backoff retry."""
    for attempt in range(max_attempts):
        try:
            return func()
        except GithubException as e:
            if e.status == 403 and "rate limit" in str(e).lower():
                wait = base_delay * (2 ** attempt)
                logger.warning(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            elif attempt == max_attempts - 1:
                raise
            else:
                time.sleep(base_delay * (2 ** attempt))
```

---

### 7. `scripts/github/projects.py`

GitHub Projects v2 GraphQL API wrapper.

```python
"""
scripts/github/projects.py
GitHub Projects v2 GraphQL API wrapper.
Used by the visibility engine to sync board state from text artifacts.
"""
import os
import requests
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.github.com/graphql"


def graphql_request(query: str, variables: dict = None,
                    token: Optional[str] = None) -> dict:
    """Execute a GitHub GraphQL query."""
    token = token or os.environ.get("GITHUB_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    resp = requests.post(GRAPHQL_URL, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def get_project_id(owner: str, project_number: int, token: Optional[str] = None) -> str:
    """Get the node ID of a GitHub Project."""
    query = """
    query($owner: String!, $number: Int!) {
      organization(login: $owner) {
        projectV2(number: $number) { id }
      }
    }
    """
    data = graphql_request(query, {"owner": owner, "number": project_number}, token)
    return data["organization"]["projectV2"]["id"]


def get_project_items(project_id: str, token: Optional[str] = None) -> list[dict]:
    """Get all items in a GitHub Project."""
    query = """
    query($projectId: ID!, $cursor: String) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id
              content {
                ... on Issue {
                  number title state
                  assignees(first: 5) { nodes { login } }
                  labels(first: 10) { nodes { name } }
                }
              }
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field { ... on ProjectV2SingleSelectField { name } }
                  }
                  ... on ProjectV2ItemFieldTextValue {
                    text
                    field { ... on ProjectV2Field { name } }
                  }
                  ... on ProjectV2ItemFieldNumberValue {
                    number
                    field { ... on ProjectV2Field { name } }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    items = []
    cursor = None
    while True:
        data = graphql_request(query, {"projectId": project_id, "cursor": cursor}, token)
        page = data["node"]["items"]
        items.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return items


def update_item_status(project_id: str, item_id: str, status_field_id: str,
                       option_id: str, token: Optional[str] = None) -> None:
    """Move a project item to a different status column."""
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId
        itemId: $itemId
        fieldId: $fieldId
        value: { singleSelectOptionId: $optionId }
      }) { projectV2Item { id } }
    }
    """
    graphql_request(mutation, {
        "projectId": project_id, "itemId": item_id,
        "fieldId": status_field_id, "optionId": option_id
    }, token)


def update_item_text_field(project_id: str, item_id: str, field_id: str,
                           value: str, token: Optional[str] = None) -> None:
    """Update a text custom field on a project item."""
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId
        itemId: $itemId
        fieldId: $fieldId
        value: { text: $value }
      }) { projectV2Item { id } }
    }
    """
    graphql_request(mutation, {
        "projectId": project_id, "itemId": item_id,
        "fieldId": field_id, "value": value
    }, token)


def get_field_ids(project_id: str, token: Optional[str] = None) -> dict[str, dict]:
    """Get all field IDs and option IDs for a project."""
    query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 30) {
            nodes {
              ... on ProjectV2Field { id name }
              ... on ProjectV2SingleSelectField {
                id name
                options { id name }
              }
            }
          }
        }
      }
    }
    """
    data = graphql_request(query, {"projectId": project_id}, token)
    fields = {}
    for field in data["node"]["fields"]["nodes"]:
        if not field:
            continue
        name = field.get("name")
        fields[name] = {
            "id": field["id"],
            "options": {opt["name"]: opt["id"]
                        for opt in field.get("options", [])}
        }
    return fields
```

---

### 8. `scripts/setup/create_labels.py`

```python
"""
scripts/setup/create_labels.py
Create all Scraut labels in the repository.
Run once during initial setup.
"""
import argparse
import logging
from scripts.github.api import get_github_client, ensure_label_exists
from scripts.utils.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LABELS = [
    # Story points
    ("sp:1",  "0075ca", "1 story point"),
    ("sp:2",  "0075ca", "2 story points"),
    ("sp:3",  "0075ca", "3 story points"),
    ("sp:5",  "0075ca", "5 story points"),
    ("sp:8",  "0075ca", "8 story points"),
    ("sp:13", "0075ca", "13 story points"),
    # Type
    ("story",  "bfd4f2", "User story"),
    ("bug",    "d73a4a", "Something isn't working"),
    ("task",   "e4e669", "Technical task"),
    ("spike",  "fbca04", "Research/investigation"),
    ("chore",  "fef2c0", "Maintenance"),
    # Status
    ("in-sprint",      "0052cc", "In current sprint"),
    ("in-review",      "5319e7", "Under review"),
    ("blocked",        "b60205", "Blocked by dependency"),
    ("escalate:human", "e11d48", "Needs human intervention"),
    # Priority
    ("p:high",   "b60205", "High priority"),
    ("p:medium", "e4e669", "Medium priority"),
    ("p:low",    "0e8a16", "Low priority"),
    # Ceremony
    ("standup",         "c5def5", "Daily standup"),
    ("retrospective",   "bfd4f2", "Sprint retrospective"),
    ("sprint-review",   "d4c5f9", "Sprint review"),
    ("sprint-planning", "f9d0c4", "Sprint planning"),
    # Agent
    ("agent-assigned", "f9ca24", "Assigned to AI agent"),
    ("agent-blocked",  "f0932b", "Agent is blocked"),
    # DoD
    ("dod:pending",  "ffeaa7", "Definition of Done check pending"),
    ("dod:approved", "00b894", "Definition of Done approved"),
    # Milestone-related
    ("milestone-risk", "d63031", "Milestone at risk"),
]


def main(repo_name: str, config_path: str = None):
    config = load_config(config_path)
    g = get_github_client()
    repo = g.get_repo(repo_name)

    for name, color, description in LABELS:
        ensure_label_exists(repo, name, color, description)
        logger.info(f"✓ {name}")

    logger.info(f"Created {len(LABELS)} labels in {repo_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Scraut labels")
    parser.add_argument("repo", help="org/repo format")
    parser.add_argument("--config", help="Path to scraut.yml")
    args = parser.parse_args()
    main(args.repo, args.config)
```

---

### 9. `.github/ISSUE_TEMPLATE/user-story.md`

```markdown
---
name: User Story
about: A user-facing feature or improvement
title: 'Story: '
labels: story
assignees: ''
---

## User story
As a **[type of user]**, I want **[action]** so that **[benefit]**.

## Acceptance criteria
- [ ] [Criterion 1 — specific, testable]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

## Out of scope
- [What this issue explicitly does NOT include]

## Notes
[Technical notes, design links, relevant context]

## Story points
<!-- Scraut will suggest an estimate. Team votes via emoji reactions on the bot comment. -->
_To be estimated_
```

---

### 10. `.github/ISSUE_TEMPLATE/bug.md`

```markdown
---
name: Bug Report
about: Something is not working correctly
title: 'Bug: '
labels: bug
assignees: ''
---

## Describe the bug
[Clear description of what is wrong]

## Steps to reproduce
1. [Step 1]
2. [Step 2]
3. [Result observed]

## Expected behaviour
[What should happen instead]

## Environment
- OS: 
- Browser/Runtime: 
- Version: 

## Logs / screenshots
[Paste relevant logs or attach screenshots]

## Acceptance criteria (for fix)
- [ ] [The bug no longer reproduces via steps above]
- [ ] [Regression test added]
```

---

### 11. `.github/ISSUE_TEMPLATE/task.md`

```markdown
---
name: Technical Task
about: Technical work with no direct user-facing outcome
title: 'Task: '
labels: task
assignees: ''
---

## Goal
[What technical outcome this task achieves]

## Details
[Implementation notes, approach, any constraints]

## Acceptance criteria
- [ ] [Specific done condition]
- [ ] [Tests pass / CI green]

## Notes
[Links to ADRs, design decisions, blockers]
```

---

### 12. `.github/ISSUE_TEMPLATE/spike.md`

```markdown
---
name: Spike / Research
about: Time-boxed investigation to reduce uncertainty
title: 'Spike: '
labels: spike
assignees: ''
---

## Question to answer
[The specific uncertainty this spike resolves]

## Time box
[Maximum time: e.g., 2 days = 3 story points]

## Output
[What will be produced: a document, a prototype, an ADR, a recommendation]

## Acceptance criteria
- [ ] Question is answered (documented in output)
- [ ] Findings are shared with the team
- [ ] Next steps are clear
```

---

### 13. `.github/ISSUE_TEMPLATE/config.yml`

```yaml
blank_issues_enabled: true
contact_links:
  - name: Scraut Documentation
    url: https://github.com/[org]/[repo]/blob/main/00-ROADMAP.md
    about: How Scraut works
```

---

### 14. `.github/pull_request_template.md`

```markdown
## Summary
<!-- What does this PR do? One sentence. -->

## Linked issues
<!-- Closes #NNN (Scraut auto-detects this to update burndown) -->
Closes #

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation
- [ ] Configuration change

## Testing
<!-- How was this tested? -->
- [ ] Unit tests added/updated
- [ ] Tested manually (describe how)
- [ ] No testing required (explain why)

## Acceptance criteria check
<!-- Copy the acceptance criteria from the linked issue and verify each one -->

## Screenshots / recordings
<!-- For UI changes -->

## Notes for reviewers
<!-- Anything the reviewer should pay special attention to -->
```

---

### 15. `.gitignore`

```
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.env
.env.local
venv/
.venv/
env/
node_modules/
.DS_Store
*.log
portal/data.json
portal/index.html
```

---

### 16. `scripts/setup/init_project.py`

A script that runs all initial setup steps.

```python
"""
scripts/setup/init_project.py
Run after cloning: sets up labels, creates first sprint folder structure,
validates config, and prints a checklist of secrets to set.
"""
import argparse
import logging
import os
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import atomic_write, today_str

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REQUIRED_SECRETS = [
    "ANTHROPIC_API_KEY (or OPENAI_API_KEY)",
    "SLACK_WEBHOOK (for channel posts)",
    "SLACK_BOT_TOKEN (for personal DMs)",
    "SCRAUT_GITHUB_TOKEN (for repo sync)",
]

INITIAL_TEAM_CAPACITY = """# Team Capacity
<!-- Update this file when team members are OOO or have reduced availability -->
<!-- Format: name: description of availability -->

# Current sprint availability
<!-- Example: Alice: OOO May 27-29 -->
```

INITIAL_FEEDBACK = """# Customer Feedback
<!-- Weekly digest from support/sales. Append new entries at the bottom. -->
<!-- Format: YYYY-MM-DD: [feedback item] -->
```


def main(repo_name: str, config_path: str = None):
    config = load_config(config_path)
    root = get_repo_root()

    logger.info("=== Scraut Initial Setup ===")

    # Create essential directories
    dirs = [
        "suggestions/active",
        "suggestions/implemented",
        "suggestions/resolved",
        "insights",
        "team",
        "okr",
        "customer",
        "knowledge",
        "milestones",
        "portal",
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Created directory: {d}")

    # Create initial files
    team_cap = root / "team" / "capacity.md"
    if not team_cap.exists():
        atomic_write(team_cap, INITIAL_TEAM_CAPACITY)

    feedback = root / "customer" / "feedback.md"
    if not feedback.exists():
        atomic_write(feedback, INITIAL_FEEDBACK)

    # Print secrets checklist
    logger.info("\n=== Required GitHub Secrets ===")
    logger.info("Set these in: Settings → Secrets → Actions")
    for secret in REQUIRED_SECRETS:
        logger.info(f"  □ {secret}")

    logger.info("\n=== Next Steps ===")
    logger.info("1. Set all required secrets in GitHub")
    logger.info("2. Run: python scripts/setup/create_labels.py [org/repo]")
    logger.info("3. Create first sprint: python scripts/sprint/create_sprint.py --sprint 1")
    logger.info("4. Proceed to Phase 2: 02-CEREMONIES.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", help="org/repo format")
    parser.add_argument("--config")
    args = parser.parse_args()
    main(args.repo, args.config)
```

---

### 17. `scripts/sprint/create_sprint.py` (partial — full implementation in Phase 2)

Create this file now with the skeleton; Phase 2 fills in the ceremony logic.

```python
"""
scripts/sprint/create_sprint.py
Create a new sprint: folder structure, meta.md, GitHub milestone.
"""
import argparse
import logging
from datetime import date, timedelta
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_sprint_folder
from scripts.utils.file_utils import create_if_not_exists, atomic_write, today_str
from scripts.utils.date_utils import get_sprint_dates
from scripts.github.api import get_github_client, create_milestone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

META_TEMPLATE = """# Sprint {sprint_num}
- Period: {start_date} → {end_date} ({work_days} working days)
- Goal: [Set during sprint planning — see planning PR]
- Team: {team_names}
- Committed: TBD story points across TBD issues
- Milestone: https://github.com/{repo}/milestone/{milestone_number}
- Capacity note: [Check team/capacity.md for OOO]

## Issues in sprint
| Issue | Title | Epic | SP | Assignee |
|-------|-------|------|----|---------|
"""


def create_sprint(sprint_num: int, repo_name: str, config: dict) -> None:
    root = get_repo_root()
    sprint_folder = root / f"sprint-{sprint_num:02d}"

    # Create folder structure
    subdirs = [
        "standup",
        "retrospective",
        "review",
        "grooming",
        "decisions",
        "incidents",
        "adr",
        "code",
    ]
    for subdir in subdirs:
        (sprint_folder / subdir).mkdir(parents=True, exist_ok=True)

    # Create summary subdirectory under standup
    (sprint_folder / "standup" / "summary").mkdir(parents=True, exist_ok=True)

    # Calculate sprint dates
    start, end = get_sprint_dates(sprint_num, config)
    team_names = ", ".join(m["display"] for m in config["team"]["members"])

    # Create GitHub milestone
    g = get_github_client()
    repo = g.get_repo(repo_name)
    ms = create_milestone(repo, f"Sprint {sprint_num:02d}",
                          f"Sprint {sprint_num}: {start} → {end}")

    # Write meta.md
    meta_content = META_TEMPLATE.format(
        sprint_num=sprint_num,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        work_days=10,  # approximate
        team_names=team_names,
        repo=repo_name,
        milestone_number=ms.number,
    )
    meta_path = sprint_folder / "meta.md"
    create_if_not_exists(meta_path, meta_content)

    # Create grooming backlog file
    grooming_path = sprint_folder / "grooming" / "backlog-ideas.md"
    create_if_not_exists(grooming_path,
        "# Backlog Ideas\n<!-- Append new ideas below. Anyone can add. -->\n\n")

    logger.info(f"✓ Created sprint-{sprint_num:02d} folder structure")
    logger.info(f"✓ Created GitHub milestone: Sprint {sprint_num:02d} (#{ms.number})")

    # Update scraut.yml current_sprint
    # (handled by caller after this function returns)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True, help="org/repo")
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    create_sprint(args.sprint, args.repo, config)
```

---

## Done Criteria for Phase 1

Before proceeding to Phase 2, verify:

- [ ] `requirements.txt` exists and `pip install -r requirements.txt` succeeds
- [ ] `scraut.yml` exists at repo root with all required fields populated
- [ ] `scripts/utils/config.py` loads `scraut.yml` without errors
- [ ] `scripts/utils/file_utils.py` — `atomic_write` and `create_if_not_exists` work
- [ ] `scripts/github/api.py` — can authenticate to GitHub API with `GITHUB_TOKEN`
- [ ] `scripts/github/projects.py` — GraphQL query executes without errors
- [ ] `scripts/setup/create_labels.py` — all labels created in the repo
- [ ] All 4 issue templates exist in `.github/ISSUE_TEMPLATE/`
- [ ] `.github/pull_request_template.md` exists
- [ ] `scripts/setup/init_project.py` runs and creates all directory structure
- [ ] `scripts/sprint/create_sprint.py --sprint 1 --repo [org/repo]` creates `sprint-01/` with all subdirectories and `meta.md`
- [ ] `.gitignore` committed

*Proceed to `02-CEREMONIES.md`*
