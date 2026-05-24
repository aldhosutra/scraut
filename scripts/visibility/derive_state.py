"""
scripts/visibility/derive_state.py
Infer issue state from text artifacts. Priority-ordered rules (applied in sequence):
  1. merged PR / closed issue → Done
  2. open PR → Review
  3. issue in Blockers section today → Blocked
  4. agent standup → In Progress
  5. issue in Today section → In Progress
  6. ambiguous (LLM) → classify
  7. in sprint roadmap, no signals → Ready
  8. default → Backlog
"""
import json
import logging
import re
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional

from scripts.utils.config import get_current_sprint, get_repo_root
from scripts.utils.file_utils import read_file, extract_section
from scripts.github.api import get_github_client

logger = logging.getLogger(__name__)

VALID_COLUMNS = ["Backlog", "Ready", "In Progress", "Review", "Testing", "Done", "Blocked"]


class IssueState(str, Enum):
    BACKLOG = "Backlog"
    READY = "Ready"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    TESTING = "Testing"
    DONE = "Done"
    BLOCKED = "Blocked"


def _load_today_standups(sprint_num: int, today: str) -> list[str]:
    root = get_repo_root()
    standup_dir = root / f"sprint-{sprint_num:02d}" / "standup" / today
    contents = []
    if standup_dir.exists():
        for f in standup_dir.glob("*.md"):
            contents.append(read_file(f))
    return contents


def _load_activity_json(sprint_num: int, today: str) -> dict:
    root = get_repo_root()
    activity_path = root / f"sprint-{sprint_num:02d}" / "code" / today / "activity.json"
    content = read_file(activity_path)
    if not content:
        return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


def _extract_issue_refs(text: str) -> set[int]:
    return {int(n) for n in re.findall(r"#(\d+)", text)}


def _get_issues_in_standups(section: str, standups: list[str]) -> set[int]:
    """Extract issue numbers from a specific section across all standup files."""
    issue_nums = set()
    for standup in standups:
        section_content = extract_section(standup, section)
        issue_nums |= _extract_issue_refs(section_content)
    return issue_nums


def _get_agent_standup_issues(standups: list[str]) -> set[int]:
    """Get issue numbers from Today sections in agent standups only."""
    issue_nums = set()
    for standup in standups:
        if "## Agent State" in standup:
            issue_nums |= _extract_issue_refs(extract_section(standup, "Today"))
    return issue_nums


def _get_merged_issue_numbers(activity: dict) -> set[int]:
    closed: set[int] = set()
    for member_data in activity.get("members", {}).values():
        for pr in member_data.get("prs_merged", []):
            for issue_num in pr.get("closes_issues", []):
                closed.add(issue_num)
    return closed


def _get_open_pr_issues(activity: dict) -> set[int]:
    """Extract issue numbers referenced in open PR titles."""
    nums: set[int] = set()
    for member_data in activity.get("members", {}).values():
        for pr in member_data.get("prs_opened", []):
            nums |= _extract_issue_refs(pr.get("title", ""))
    return nums


def _classify_via_llm(issue_number: int, issue_title: str, signals: dict) -> IssueState:
    try:
        from scripts.llm.client import complete_json
        from scripts.llm.prompts import STATE_CLASSIFICATION
        prompt = STATE_CLASSIFICATION.format(
            issue_number=issue_number,
            issue_title=issue_title,
            signals=json.dumps(signals, indent=2),
            valid_states=", ".join(VALID_COLUMNS),
        )
        result = complete_json(prompt)
        state_str = result.get("state", "Backlog")
        if state_str in VALID_COLUMNS:
            return IssueState(state_str)
    except Exception as e:
        logger.error(f"LLM classification failed for issue #{issue_number}: {e}")
    return IssueState.BACKLOG


def _issues_in_sprint_roadmap(sprint_num: int) -> set[int]:
    root = get_repo_root()
    meta_path = root / f"sprint-{sprint_num:02d}" / "meta.md"
    content = read_file(meta_path)
    if not content:
        return set()
    return {int(n) for n in re.findall(r"#(\d+)", content)}


class StateDeriver:
    """Derives issue states from text artifacts using priority-ordered rules."""

    def __init__(self, sprint_num: Optional[int] = None, today: Optional[str] = None):
        self.sprint_num = sprint_num or get_current_sprint()
        self.today = today or date.today().isoformat()

        self.standups = _load_today_standups(self.sprint_num, self.today)
        self.activity = _load_activity_json(self.sprint_num, self.today)

        self.merged_issues = _get_merged_issue_numbers(self.activity)
        self.open_pr_issues = _get_open_pr_issues(self.activity)
        self.blocked_issues = _get_issues_in_standups("Blockers", self.standups)
        self.agent_issues = _get_agent_standup_issues(self.standups)
        self.today_issues = _get_issues_in_standups("Today", self.standups)
        self.roadmap_issues = _issues_in_sprint_roadmap(self.sprint_num)

        logger.info(
            f"StateDeriver: {len(self.standups)} standups, "
            f"{len(self.merged_issues)} merged, {len(self.blocked_issues)} blocked, "
            f"{len(self.today_issues)} in-progress"
        )

    def derive(self, issue_number: int, issue_title: str = "",
               issue_state: str = "open", use_llm: bool = True) -> IssueState:
        """Apply priority-ordered rules to infer state for one issue."""

        # Rule 1: closed issue or merged PR → Done
        if issue_state == "closed" or issue_number in self.merged_issues:
            return IssueState.DONE

        # Rule 2: open PR referencing this issue → Review
        if issue_number in self.open_pr_issues:
            return IssueState.REVIEW

        # Rule 3: in Blockers section of any standup today → Blocked
        if issue_number in self.blocked_issues:
            return IssueState.BLOCKED

        # Rule 4: in agent standup Today section → In Progress
        if issue_number in self.agent_issues:
            return IssueState.IN_PROGRESS

        # Rule 5: in human standup Today section → In Progress
        if issue_number in self.today_issues:
            return IssueState.IN_PROGRESS

        # Rule 6: in sprint but ambiguous — use LLM to classify
        if issue_number in self.roadmap_issues and use_llm and issue_title:
            signals = {
                "in_standup_today": issue_number in self.today_issues,
                "in_blockers": issue_number in self.blocked_issues,
                "in_merged_prs": issue_number in self.merged_issues,
                "in_open_prs": issue_number in self.open_pr_issues,
                "standup_count": len(self.standups),
            }
            return _classify_via_llm(issue_number, issue_title, signals)

        # Rule 7: in sprint roadmap, no signals → Ready
        if issue_number in self.roadmap_issues:
            return IssueState.READY

        # Rule 8: default → Backlog
        return IssueState.BACKLOG

    def derive_batch(self, issues: list[dict], use_llm: bool = True) -> dict[int, IssueState]:
        """Derive state for a batch of issues. issues: list of {number, title, state}."""
        return {
            issue["number"]: self.derive(
                issue["number"],
                issue.get("title", ""),
                issue.get("state", "open"),
                use_llm=use_llm,
            )
            for issue in issues
        }


class StateResult:
    """Result of state derivation for a single issue."""

    def __init__(self, column: str, confidence: float, health: str = "on-track"):
        self.column = column
        self.confidence = confidence
        self.health = health

    def __repr__(self):
        return (f"StateResult(column={self.column!r}, "
                f"confidence={self.confidence}, health={self.health!r})")


def get_pr_issue_map(repo) -> dict:
    """Return {issue_num: {pr_number, state}} from recent PRs."""
    result = {}
    try:
        for pr in repo.get_pulls(state="all"):
            text = (pr.title or "") + " " + (pr.body or "")
            nums = _extract_issue_refs(text)
            for num in nums:
                if num not in result or pr.state == "open":
                    result[num] = {"pr_number": pr.number, "state": pr.state}
    except Exception as e:
        logger.warning(f"Could not fetch PRs: {e}")
    return result


def get_sprint_roadmap_issues(repo, sprint_num: int) -> set:
    """Get set of issue numbers with the sprint label from GitHub."""
    sprint_label = f"sprint-{sprint_num:02d}"
    try:
        issues = repo.get_issues(state="all", labels=[sprint_label])
        return {i.number for i in issues}
    except Exception as e:
        logger.warning(f"Could not fetch sprint issues: {e}")
        return set()


def scan_standup_files(sprint_num: int, target_date: str) -> dict:
    """Scan standup files. Returns {section: set(issue_nums)}."""
    standups = _load_today_standups(sprint_num, target_date)
    return {
        "Today": _get_issues_in_standups("Today", standups),
        "Blockers": _get_issues_in_standups("Blockers", standups),
        "Yesterday": _get_issues_in_standups("Yesterday", standups),
    }


def derive_all_states(repo_name: str, config: dict,
                      target_date: str = None) -> dict:
    """Derive states for all issues in the current sprint roadmap."""
    if target_date is None:
        target_date = date.today().isoformat()

    sprint_num = get_current_sprint()

    g = get_github_client()
    repo = g.get_repo(repo_name)

    pr_map = get_pr_issue_map(repo)
    roadmap_issues = get_sprint_roadmap_issues(repo, sprint_num)

    standups = _load_today_standups(sprint_num, target_date)
    blocked_issues = _get_issues_in_standups("Blockers", standups)
    today_issues = _get_issues_in_standups("Today", standups)
    agent_issues = _get_agent_standup_issues(standups)

    results = {}
    for issue_num in roadmap_issues:
        try:
            issue = repo.get_issue(issue_num)
            issue_state = issue.state
        except Exception:
            issue_state = "open"

        if issue_state == "closed":
            results[issue_num] = StateResult("Done", 1.0)
        elif issue_num in pr_map and pr_map[issue_num].get("state") == "open":
            results[issue_num] = StateResult("Review", 1.0)
        elif issue_num in blocked_issues:
            results[issue_num] = StateResult("In Progress", 0.9, "blocked")
        elif issue_num in agent_issues or issue_num in today_issues:
            results[issue_num] = StateResult("In Progress", 0.85)
        else:
            results[issue_num] = StateResult("Ready", 0.7)

    return results


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Path to scraut.yml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sprint", type=int)
    parser.add_argument("--date")
    args = parser.parse_args()

    if args.config:
        from scripts.utils.config import load_config
        load_config(args.config)

    deriver = StateDeriver(sprint_num=args.sprint, today=args.date)
    print(f"VALID_COLUMNS: {VALID_COLUMNS}")
    print(f"Sprint: {deriver.sprint_num}, Date: {deriver.today}")
    print(f"Standups loaded: {len(deriver.standups)}")
    print(f"Merged (Done): {deriver.merged_issues}")
    print(f"Blocked: {deriver.blocked_issues}")
    print(f"In-progress: {deriver.today_issues | deriver.agent_issues}")
    print(f"Roadmap issues: {deriver.roadmap_issues}")
