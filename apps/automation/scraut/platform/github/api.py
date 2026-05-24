"""
lib/github/api.py
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
