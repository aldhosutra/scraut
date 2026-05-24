"""
test/mocks/github_mocks.py
Mock classes that replicate the PyGitHub interface.
Use these instead of real GitHub API calls in all tests.
"""
from unittest.mock import MagicMock
from datetime import datetime, timezone


class MockLabel:
    def __init__(self, name: str, color: str = "ffffff"):
        self.name = name
        self.color = color


class MockUser:
    def __init__(self, login: str):
        self.login = login


class MockMilestone:
    def __init__(self, number: int, title: str, state: str = "open"):
        self.number = number
        self.title = title
        self.state = state

    def edit(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockComment:
    def __init__(self, body: str, author_login: str = "alice",
                 created_at: datetime = None):
        self.id = 1
        self.body = body
        self.user = MockUser(author_login)
        self.created_at = created_at or datetime(2026, 5, 23, 9, 0, 0,
                                                  tzinfo=timezone.utc)

    def delete(self):
        pass

    def get_reactions(self):
        return []


class MockIssue:
    def __init__(self, number: int, title: str, state: str = "open",
                 labels: list = None, body: str = "",
                 assignees: list = None, closed_at: datetime = None):
        self.number = number
        self.title = title
        self.state = state
        self.body = body
        self.labels = [MockLabel(l) for l in (labels or [])]
        self.assignees = [MockUser(a) for a in (assignees or [])]
        self.milestone = None
        self.html_url = f"https://github.com/test/repo/issues/{number}"
        self.closed_at = closed_at
        self._comments: list = []

    def get_comments(self):
        return iter(self._comments)

    def get_events(self):
        return iter([])

    def add_comment(self, body: str, author: str = "alice") -> MockComment:
        c = MockComment(body, author)
        self._comments.append(c)
        return c

    def add_to_labels(self, *labels):
        for label in labels:
            name = label if isinstance(label, str) else label.name
            if not any(l.name == name for l in self.labels):
                self.labels.append(MockLabel(name))

    def remove_from_labels(self, label):
        name = label if isinstance(label, str) else label.name
        self.labels = [l for l in self.labels if l.name != name]

    def create_comment(self, body: str) -> MockComment:
        return self.add_comment(body)

    def edit(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockPullRequest:
    def __init__(self, number: int, title: str, body: str = "",
                 state: str = "open", merged: bool = False,
                 author_login: str = "alice",
                 created_at: datetime = None,
                 merged_at: datetime = None,
                 updated_at: datetime = None,
                 head_ref: str = "feature/test"):
        self.number = number
        self.title = title
        self.body = body
        self.state = state
        self.merged = merged
        self.user = MockUser(author_login)
        self.html_url = f"https://github.com/test/repo/pulls/{number}"
        self.created_at = created_at or datetime(2026, 5, 23, tzinfo=timezone.utc)
        self.merged_at = merged_at
        self.updated_at = updated_at or datetime(2026, 5, 23, tzinfo=timezone.utc)
        self.head = MagicMock()
        self.head.ref = head_ref
        self._reviews = []
        self._files = []

    def get_reviews(self):
        return iter(self._reviews)

    def get_files(self):
        return iter(self._files)

    def get_review_comments(self):
        return iter([])

    def edit(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def add_to_labels(self, label):
        pass

    def create_review(self, body: str, event: str = "COMMENT"):
        pass


class MockRepository:
    def __init__(self, full_name: str = "test-org/test-repo"):
        self.full_name = full_name
        self.name = full_name.split("/")[-1]
        self._issues: dict = {}
        self._prs: dict = {}
        self._milestones: dict = {}
        self._labels: dict = {}
        self._files: dict = {}
        self._branches: dict = {}
        self._next_issue = 1
        self._next_milestone = 1

    def add_issue(self, issue: MockIssue) -> MockIssue:
        self._issues[issue.number] = issue
        return issue

    def add_pr(self, pr: MockPullRequest) -> MockPullRequest:
        self._prs[pr.number] = pr
        return pr

    def get_issue(self, number: int) -> MockIssue:
        if number not in self._issues:
            raise Exception(f"Issue #{number} not found")
        return self._issues[number]

    def get_pull(self, number: int) -> MockPullRequest:
        if number not in self._prs:
            raise Exception(f"PR #{number} not found")
        return self._prs[number]

    def get_issues(self, state: str = "open", labels=None) -> list:
        issues = list(self._issues.values())
        if state != "all":
            issues = [i for i in issues if i.state == state]
        if labels:
            label_names = [l if isinstance(l, str) else l.name for l in labels]
            issues = [i for i in issues
                      if all(any(l.name == ln for l in i.labels) for ln in label_names)]
        return issues

    def get_pulls(self, state: str = "open", **kwargs) -> list:
        prs = list(self._prs.values())
        if state != "all":
            prs = [p for p in prs if p.state == state]
        return prs

    def get_milestones(self, state: str = "open") -> list:
        ms = list(self._milestones.values())
        if state != "all":
            ms = [m for m in ms if m.state == state]
        return ms

    def get_label(self, name: str) -> MockLabel:
        if name not in self._labels:
            raise Exception(f"Label '{name}' not found")
        return self._labels[name]

    def create_label(self, name: str, color: str = "ffffff",
                     description: str = "") -> MockLabel:
        label = MockLabel(name, color)
        self._labels[name] = label
        return label

    def create_issue(self, title: str, body: str = "", labels=None,
                     milestone=None, assignees=None) -> MockIssue:
        issue = MockIssue(
            number=self._next_issue,
            title=title,
            body=body,
            labels=[l if isinstance(l, str) else l.name for l in (labels or [])],
        )
        self._issues[self._next_issue] = issue
        self._next_issue += 1
        return issue

    def create_milestone(self, title: str, description: str = "") -> MockMilestone:
        ms = MockMilestone(self._next_milestone, title)
        self._milestones[self._next_milestone] = ms
        self._next_milestone += 1
        return ms

    def get_commits(self, since=None, **kwargs) -> list:
        return []

    def get_contents(self, path: str, ref: str = "main"):
        if path not in self._files:
            raise Exception(f"File not found: {path}")
        content = MagicMock()
        content.decoded_content = self._files[path].encode()
        content.sha = "test-sha"
        return content

    def create_file(self, path: str, message: str, content: str,
                    branch: str = "main") -> None:
        self._files[path] = content

    def update_file(self, path: str, message: str, content: str,
                    sha: str, branch: str = "main") -> None:
        self._files[path] = content

    def get_branch(self, name: str):
        branch = MagicMock()
        branch.commit.sha = "test-sha"
        return branch

    def create_git_ref(self, ref: str, sha: str) -> None:
        self._branches[ref] = sha

    def create_pull(self, title: str, body: str, head: str,
                    base: str) -> MockPullRequest:
        pr = MockPullRequest(
            number=max(self._prs.keys(), default=0) + 1,
            title=title,
            body=body,
            head_ref=head,
        )
        self._prs[pr.number] = pr
        return pr
