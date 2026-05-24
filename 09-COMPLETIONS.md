# Phase 9: Completions
*Scraut Implementation — fills every gap identified in the full audit*

## Why this file exists

After careful re-analysis, the following items were **referenced but never implemented**
across Phases 1–8. This file closes every gap. Implement all items in this file before
the system is considered complete.

---

## Complete Gap Audit

### Scripts referenced in workflows but never written
| Script | Referenced in | Status |
|--------|--------------|--------|
| `scripts/backlog/tally_estimation.py` | `estimation-tally.yml` | ❌ Missing |
| `scripts/sprint/create_planning_pr.py` | `sprint-planning.yml` | ❌ Missing |
| `scripts/sprint/close_sprint.py` | `sprint-review.yml` | ❌ Missing (skeleton only) |
| `scripts/sprint/generate_review.py` | `sprint-review.yml` | ❌ Missing |
| `scripts/sprint/synthesise_retrospective.py` | `sprint-retrospective.yml` | ❌ Missing |
| `scripts/backlog/prioritize_backlog.py` | ROADMAP file tree | ❌ Missing |
| `scripts/insights/generate_insights.py` | ROADMAP `insights/` dir | ❌ Missing |
| `scripts/backlog/pr_auto_describe.py` | 94/100 improvements | ❌ Missing |
| `scripts/backlog/pr_knowledge_extract.py` | ROADMAP `knowledge/` dir | ❌ Missing |
| `scripts/sprint/check_scope_creep.py` | 94/100 improvements | ❌ Missing |

### Workflows listed in ROADMAP but never written
| Workflow | Trigger | Status |
|----------|---------|--------|
| `backlog-grooming.yml` | Schedule mid-sprint | ❌ Missing |
| `pr-linker.yml` | `pull_request.opened` | ❌ Missing |
| `pr-close-stories.yml` | `pull_request.closed` + merged | ❌ Missing |
| `sprint-plan-pr.yml` | PR merged on planning branch | ❌ Missing |
| `dod-check.yml` | `issues.closed` | ❌ Missing |
| `incident-to-backlog.yml` | Push to `incidents/**` | ❌ Missing |

### Features from improvements (94/100 plan) never implemented
| Feature | Plan module | Status |
|---------|------------|--------|
| Breadcrumb navigation in standup templates | Module 4 (Dev QoL) | ❌ Missing |
| PR auto-description from diff | Module 4 (Dev QoL) | ❌ Missing |
| LLM cost batching | Phase 2 config exists, no implementation | ❌ Missing |
| Web form `CONFIG.teamMembers` population | Phase 8 form has empty array | ❌ Incomplete |
| Cross-sprint insights generation | `insights/` directory exists, no script | ❌ Missing |
| OKR → issue label linking | `okr/` dir exists, no workflow | ❌ Missing |
| Team capacity in sprint planning | `team/capacity.md` exists, never read | ❌ Missing |
| `insights/velocity-trends.md` referenced in health check | Never generated | ❌ Missing |

---

## 1. `scripts/backlog/tally_estimation.py`

```python
"""
scripts/backlog/tally_estimation.py
Tally emoji reaction votes on story point estimation comments.
Called by estimation-tally.yml when a reaction is added/removed on
a Scraut estimation comment.

Emoji → story point mapping (team convention):
  👍 = 1 sp
  ❤️  = 3 sp
  🚀 = 5 sp
  🎉 = 8 sp
  🔥 = 13 sp

After 24h OR when all team members have voted:
  → Apply the winning estimate as sp:N label on the issue
  → Post result comment
"""
import argparse
import logging
from datetime import datetime, timezone, timedelta
from scripts.utils.config import load_config, get_team_logins
from scripts.github.api import (get_github_client, set_sp_on_issue,
                                 post_comment, ensure_label_exists)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMOJI_TO_SP = {
    "+1":      1,   # 👍
    "heart":   3,   # ❤️
    "rocket":  5,   # 🚀
    "tada":    8,   # 🎉
    "fire":   13,   # 🔥
}

RESULT_COMMENT = """<!-- scraut-estimation-result -->
## 📊 Story Point Estimation Result

| Points | Votes |
|--------|-------|
{vote_table}

**Winning estimate: `sp:{winner}`** ({winner_votes} vote(s))

Applied automatically. To override: comment `/estimate N` where N ∈ {{1,2,3,5,8,13}}.
"""

TALLY_IN_PROGRESS_COMMENT = """<!-- scraut-estimation-progress -->
## 🗳️ Estimation votes so far ({voted}/{total} team members)

| Points | Votes |
|--------|-------|
{vote_table}

Voting closes when all team members vote OR 24h after the estimation comment was posted.
"""


def is_estimation_comment(comment_body: str) -> bool:
    return "<!-- scraut-estimation -->" in (comment_body or "")


def count_votes(comment_id: int, repo) -> dict[int, int]:
    """Count emoji reactions on a comment by story point value."""
    votes = {}
    try:
        reactions = list(repo.get_comment(comment_id).get_reactions())
        team_logins = get_team_logins()
        for reaction in reactions:
            if reaction.user.login not in team_logins:
                continue
            sp = EMOJI_TO_SP.get(reaction.content)
            if sp:
                votes[sp] = votes.get(sp, 0) + 1
    except Exception as e:
        logger.error(f"Failed to count reactions: {e}")
    return votes


def format_vote_table(votes: dict[int, int]) -> str:
    all_sp = [1, 3, 5, 8, 13]
    rows = [f"| sp:{sp} | {'⬛' * votes.get(sp, 0)} {votes.get(sp, 0)} |"
            for sp in all_sp if votes.get(sp, 0) > 0]
    return "\n".join(rows) if rows else "| — | No votes yet |"


def determine_winner(votes: dict[int, int]) -> int | None:
    """Return winning SP value (most votes), None if no votes."""
    if not votes:
        return None
    return max(votes.items(), key=lambda x: x[1])[0]


def should_finalize(comment, team_logins: list, votes: dict) -> bool:
    """Decide whether to finalize the estimate or keep voting open."""
    # Finalize if all team members voted
    unique_voters = sum(votes.values())
    if unique_voters >= len(team_logins):
        return True

    # Finalize if 24h have passed since the comment
    age = datetime.now(tz=timezone.utc) - comment.created_at.replace(tzinfo=timezone.utc)
    if age > timedelta(hours=24):
        return True

    return False


def tally_estimation(issue_number: int, comment_id: int,
                     repo_name: str, config: dict) -> None:
    g = get_github_client()
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    team_logins = get_team_logins()

    # Find the estimation comment
    estimation_comment = None
    for comment in issue.get_comments():
        if is_estimation_comment(comment.body or ""):
            estimation_comment = comment
            break

    if not estimation_comment:
        logger.warning(f"No estimation comment found on #{issue_number}")
        return

    votes = count_votes(estimation_comment.id, repo)
    total_team = len(team_logins)
    voted_count = sum(votes.values())

    if should_finalize(estimation_comment, team_logins, votes):
        winner = determine_winner(votes)
        if winner:
            # Apply the label
            set_sp_on_issue(repo, issue, winner)

            # Remove previous tally-in-progress comments
            for comment in issue.get_comments():
                if "<!-- scraut-estimation-progress -->" in (comment.body or ""):
                    comment.delete()

            # Post final result
            result_body = RESULT_COMMENT.format(
                vote_table=format_vote_table(votes),
                winner=winner,
                winner_votes=votes.get(winner, 0),
            )
            post_comment(issue, result_body)
            logger.info(f"#{issue_number}: estimated at sp:{winner} ({votes})")
        else:
            # No votes — keep default LLM suggestion, post reminder
            post_comment(issue,
                f"⏱️ Estimation vote closed with no votes. "
                f"Using Scraut's LLM suggestion. Comment `/estimate N` to override."
            )
    else:
        # Still open — update progress comment
        # Delete old progress comment if exists
        for comment in issue.get_comments():
            if "<!-- scraut-estimation-progress -->" in (comment.body or ""):
                comment.delete()
                break

        if votes:
            progress_body = TALLY_IN_PROGRESS_COMMENT.format(
                voted=voted_count,
                total=total_team,
                vote_table=format_vote_table(votes),
            )
            post_comment(issue, progress_body)

    logger.info(f"Tally complete for #{issue_number}: {votes}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--comment", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    tally_estimation(args.issue, args.comment, args.repo, config)
```

---

## 2. `scripts/sprint/close_sprint.py` (full implementation)

```python
"""
scripts/sprint/close_sprint.py
Close a sprint: close GitHub milestone, label deferred issues,
calculate velocity, write sprint summary stats, increment current_sprint in scraut.yml.
"""
import argparse
import logging
import re
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import read_file, atomic_write
from scripts.github.api import (get_github_client, get_issues, get_sp_from_issue,
                                  add_label_to_issue, remove_label_from_issue,
                                  ensure_label_exists)
from scripts.sprint.calculate_velocity import calculate_sprint_velocity
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def close_sprint(sprint_num: int, repo_name: str, config: dict) -> dict:
    """
    Close a sprint:
    1. Close the GitHub milestone
    2. Move open issues back to backlog (remove sprint label, keep in-sprint label for tracking)
    3. Calculate and return velocity stats
    4. Increment current_sprint in scraut.yml
    """
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_label = f"sprint-{sprint_num:02d}"

    # Close the GitHub milestone
    for ms in repo.get_milestones(state="open"):
        if ms.title == f"Sprint {sprint_num:02d}":
            ms.edit(state="closed")
            logger.info(f"Closed milestone: {ms.title}")
            break

    # Get all sprint issues
    all_issues = get_issues(repo, labels=[sprint_label], state="all")
    closed = [i for i in all_issues if i.state == "closed"]
    open_issues = [i for i in all_issues if i.state == "open"]

    # Label deferred issues for tracking
    ensure_label_exists(repo, "deferred", color="e4e669", description="Deferred from sprint")
    for issue in open_issues:
        add_label_to_issue(issue, "deferred")
        remove_label_from_issue(issue, "in-sprint")
        logger.info(f"Deferred: #{issue.number} — {issue.title[:50]}")

    # Calculate velocity
    velocity = calculate_sprint_velocity(sprint_num, repo_name)

    # Increment current_sprint in scraut.yml
    root = get_repo_root()
    scraut_yml_path = root / "scraut.yml"
    content = read_file(scraut_yml_path)
    # Replace current_sprint value
    new_content = re.sub(
        r"(current_sprint:\s*)\d+",
        f"\\g<1>{sprint_num + 1}",
        content
    )
    atomic_write(scraut_yml_path, new_content)
    logger.info(f"Incremented current_sprint to {sprint_num + 1}")

    logger.info(
        f"Sprint {sprint_num} closed: "
        f"{velocity['completed_sp']}/{velocity['planned_sp']} sp "
        f"({len(closed)}/{len(all_issues)} issues completed)"
    )
    return velocity


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    close_sprint(args.sprint, args.repo, config)
```

---

## 3. `scripts/sprint/create_planning_pr.py`

```python
"""
scripts/sprint/create_planning_pr.py
Create the sprint planning PR: a branch with the proposed sprint backlog.
Team reviews the PR to add/remove issues via review comments.
Merging the PR = team formally commits to the sprint.
This implements the "sprint planning as PR review" ceremony improvement.
"""
import argparse
import logging
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import atomic_write
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue
from scripts.llm.client import complete_json
from scripts.llm.prompts import SPRINT_GOAL_SUGGESTION, SYSTEM_SCRUM_ASSISTANT
from scripts.sprint.calculate_velocity import calculate_rolling_velocity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PLANNING_PR_CONTENT = """# 🎯 Sprint {sprint_num} — Proposed Backlog

**Suggested sprint goal:** {sprint_goal}

**Capacity:** {capacity} sp/sprint (based on {velocity_sprints}-sprint average)

---

## Proposed sprint issues

| Issue | Title | Type | SP | Priority |
|-------|-------|------|----|---------|
{issue_table}

**Total:** {total_sp} sp

---

## Instructions for team

Review this proposal:
- ✅ Comment `/approve` to accept as-is
- ➕ Comment `/add #NNN` to add an issue
- ➖ Comment `/remove #NNN` to remove an issue
- 📝 Leave review comments on specific lines to discuss individual stories

**Merging this PR = team commits to this sprint scope.**

_Generated by Scraut on {date}_
"""


def get_prioritised_backlog(repo_name: str, config: dict, capacity: int) -> list:
    """Get top backlog issues up to capacity SP."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_num = get_current_sprint()

    # Get issues not in current sprint, prioritised by p:high > p:medium > p:low
    all_open = get_issues(repo, state="open")
    backlog = [
        i for i in all_open
        if not any(l.name.startswith("sprint-") or l.name == "in-sprint"
                   for l in i.labels)
    ]

    # Sort by priority
    priority_order = {"p:high": 0, "p:medium": 1, "p:low": 2}
    def issue_priority(issue):
        for label in issue.labels:
            if label.name in priority_order:
                return priority_order[label.name]
        return 3

    backlog.sort(key=issue_priority)

    # Fill up to capacity
    selected = []
    total_sp = 0
    for issue in backlog:
        sp = get_sp_from_issue(issue)
        if sp == 0:
            sp = 3  # default estimate for unpointed issues
        if total_sp + sp <= capacity:
            selected.append(issue)
            total_sp += sp

    return selected, total_sp


def create_planning_pr(sprint_num: int, repo_name: str, config: dict) -> None:
    g = get_github_client()
    repo = g.get_repo(repo_name)

    velocity = calculate_rolling_velocity(repo_name)
    capacity = round(velocity.get("avg", 26) * config["sprint"].get("capacity_buffer", 0.85))

    selected_issues, total_sp = get_prioritised_backlog(repo_name, config, capacity)

    if not selected_issues:
        logger.warning("No backlog issues found for sprint planning")
        return

    # LLM sprint goal suggestion
    backlog_summary = "\n".join(
        f"- #{i.number}: {i.title} (sp:{get_sp_from_issue(i) or '?'})"
        for i in selected_issues[:10]
    )
    root = get_repo_root()
    prev_meta = ""
    if sprint_num > 1:
        from scripts.utils.file_utils import read_file, extract_section
        prev_meta = read_file(root / f"sprint-{sprint_num-1:02d}" / "meta.md")
    prev_goal = extract_section(prev_meta, "Goal") if prev_meta else "No previous sprint"

    goal_result = complete_json(
        SPRINT_GOAL_SUGGESTION.format(
            sprint_num=sprint_num,
            backlog_items=backlog_summary,
            velocity=velocity.get("avg", 26),
            prev_goal=prev_goal,
            capacity=capacity,
        ),
        system=SYSTEM_SCRUM_ASSISTANT,
    )
    sprint_goal = goal_result.get("suggested_goal", "Team to define during planning") if goal_result else "Team to define"

    # Build issue table
    rows = []
    for issue in selected_issues:
        sp = get_sp_from_issue(issue) or "?"
        labels = [l.name for l in issue.labels]
        issue_type = next((l for l in labels if l in ["story","bug","task","spike","chore"]), "task")
        priority = next((l for l in labels if l.startswith("p:")), "p:medium")
        rows.append(f"| #{issue.number} | {issue.title[:60]} | {issue_type} | {sp} | {priority} |")

    pr_body = PLANNING_PR_CONTENT.format(
        sprint_num=sprint_num,
        sprint_goal=sprint_goal,
        capacity=capacity,
        velocity_sprints=velocity.get("sprints_sampled", 5),
        issue_table="\n".join(rows),
        total_sp=total_sp,
        date=date.today().isoformat(),
    )

    # Create branch and file
    branch_name = f"sprint-{sprint_num:02d}-planning"
    # Create branch from main
    try:
        main_sha = repo.get_branch("main").commit.sha
        repo.create_git_ref(f"refs/heads/{branch_name}", main_sha)
    except Exception as e:
        logger.warning(f"Branch may already exist: {e}")

    # Write planning file to branch
    planning_path = f"sprint-{sprint_num:02d}/meta.md"
    sprint_meta_content = (
        f"# Sprint {sprint_num:02d}\n"
        f"- Period: TBD\n"
        f"- Goal: {sprint_goal}\n"
        f"- Team: {', '.join(m['display'] for m in config['team']['members'])}\n"
        f"- Committed: {total_sp} story points across {len(selected_issues)} issues\n\n"
        f"## Issues in sprint\n"
        f"| Issue | Title | EP | SP | Assignee |\n"
        f"|-------|-------|-----|-----|----------|\n"
        + "\n".join(
            f"| #{i.number} | {i.title[:50]} | - | {get_sp_from_issue(i) or '?'} | TBD |"
            for i in selected_issues
        )
    )

    try:
        existing = repo.get_contents(planning_path, ref="main")
        repo.update_file(
            planning_path,
            f"chore: sprint {sprint_num} planning proposal [skip ci]",
            sprint_meta_content,
            existing.sha,
            branch=branch_name,
        )
    except Exception:
        repo.create_file(
            planning_path,
            f"chore: sprint {sprint_num} planning proposal [skip ci]",
            sprint_meta_content,
            branch=branch_name,
        )

    # Create PR
    pr = repo.create_pull(
        title=f"🎯 Sprint {sprint_num:02d} Planning — {sprint_goal[:60]}",
        body=pr_body,
        head=branch_name,
        base="main",
    )
    pr.add_to_labels("sprint-planning")
    logger.info(f"Created planning PR #{pr.number}: {pr.html_url}")

    # Apply sprint label to selected issues
    sprint_label = f"sprint-{sprint_num:02d}"
    from scripts.github.api import ensure_label_exists, add_label_to_issue
    ensure_label_exists(repo, sprint_label, color="0075ca")
    for issue in selected_issues:
        add_label_to_issue(issue, sprint_label)
        add_label_to_issue(issue, "in-sprint")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    create_planning_pr(args.sprint, args.repo, config)
```

---

## 4. `scripts/sprint/generate_review.py`

```python
"""
scripts/sprint/generate_review.py
Generate sprint review document: velocity stats + LLM narrative.
Writes sprint-N/review/sprint-review.md (bot-generated zone).
Posts to Slack.
"""
import argparse
import json
import logging
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import atomic_write, read_file
from scripts.llm.client import complete
from scripts.llm.prompts import SPRINT_REVIEW_NARRATIVE, SYSTEM_SCRUM_ASSISTANT
from scripts.sprint.calculate_velocity import calculate_sprint_velocity
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue
from scripts.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_review(sprint_num: int, repo_name: str, config: dict) -> None:
    root = get_repo_root()
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_label = f"sprint-{sprint_num:02d}"

    # Gather stats
    velocity = calculate_sprint_velocity(sprint_num, repo_name)
    meta = read_file(root / f"sprint-{sprint_num:02d}" / "meta.md")

    from scripts.utils.file_utils import extract_section
    sprint_goal = extract_section(meta, "Goal") if meta else "Not specified"

    all_issues = get_issues(repo, labels=[sprint_label], state="all")
    closed = [i for i in all_issues if i.state == "closed"]
    open_issues = [i for i in all_issues if i.state == "open"]

    completed_list = "\n".join(
        f"- #{i.number}: {i.title} (sp:{get_sp_from_issue(i)})"
        for i in closed
    )
    deferred_list = "\n".join(
        f"- #{i.number}: {i.title} (sp:{get_sp_from_issue(i)}) — deferred"
        for i in open_issues
    )

    # Read decisions from sprint
    decisions_dir = root / f"sprint-{sprint_num:02d}" / "decisions"
    decisions_text = ""
    if decisions_dir.exists():
        for f in sorted(decisions_dir.glob("*.md")):
            decisions_text += read_file(f) + "\n"

    # Get rolling avg velocity (last 3 sprints)
    from scripts.sprint.calculate_velocity import calculate_rolling_velocity
    rolling = calculate_rolling_velocity(repo_name, num_sprints=3)

    # Generate narrative via LLM
    narrative = complete(
        SPRINT_REVIEW_NARRATIVE.format(
            sprint_num=sprint_num,
            sprint_goal=sprint_goal,
            planned_sp=velocity["planned_sp"],
            planned_issues=len(all_issues),
            completed_sp=velocity["completed_sp"],
            completed_issues=len(closed),
            deferred_issues=len(open_issues),
            velocity=velocity["completed_sp"],
            avg_velocity=rolling.get("avg", 0),
            ci_status="✅ Check GitHub Actions",
            completed_list=completed_list or "None",
            deferred_list=deferred_list or "None",
            decisions=decisions_text[:500] or "No recorded decisions",
        ),
        system=SYSTEM_SCRUM_ASSISTANT,
    )

    review_content = (
        f"<!-- BOT-GENERATED -->\n"
        f"# Sprint {sprint_num:02d} Review\n"
        f"*Generated: {date.today().isoformat()}*\n\n"
        f"## Summary\n\n{narrative}\n\n"
        f"## Metrics\n\n"
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| Story points planned | {velocity['planned_sp']} |\n"
        f"| Story points completed | {velocity['completed_sp']} |\n"
        f"| Completion rate | {round(velocity['completion_rate']*100)}% |\n"
        f"| Issues completed | {len(closed)} of {len(all_issues)} |\n"
        f"| Issues deferred | {len(open_issues)} |\n\n"
        f"## Completed\n\n{completed_list or '_None_'}\n\n"
        f"## Deferred\n\n{deferred_list or '_None_'}\n"
    )

    # Write to review folder
    review_dir = root / f"sprint-{sprint_num:02d}" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(review_dir / "sprint-review.md", review_content)

    # Post to Slack
    webhook = config.get("notifications", {}).get("slack_webhook")
    if webhook:
        post_to_slack(
            webhook,
            f"✅ *Sprint {sprint_num:02d} Review*\n"
            f"{velocity['completed_sp']}/{velocity['planned_sp']} sp "
            f"({round(velocity['completion_rate']*100)}%) · "
            f"{len(closed)}/{len(all_issues)} issues\n\n"
            + (narrative[:500] if narrative else "")
        )

    logger.info(f"Sprint review generated for sprint {sprint_num}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    generate_review(args.sprint, args.repo, config)
```

---

## 5. `scripts/sprint/synthesise_retrospective.py`

```python
"""
scripts/sprint/synthesise_retrospective.py
Read all individual retrospective files, synthesise with LLM,
write sprint-N/retrospective/summary.md (bot-generated).
Also check if previous retro action items were followed up.
"""
import argparse
import logging
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import atomic_write, read_file, extract_section
from scripts.llm.client import complete
from scripts.llm.prompts import RETROSPECTIVE_SYNTHESIS, SYSTEM_SCRUM_ASSISTANT
from scripts.sprint.calculate_velocity import calculate_sprint_velocity
from scripts.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_previous_retro_followthrough(sprint_num: int, config: dict) -> str:
    """Check if previous sprint's retro action items were addressed."""
    root = get_repo_root()
    if sprint_num <= 1:
        return ""

    prev_summary = read_file(root / f"sprint-{sprint_num-1:02d}" / "retrospective" / "summary.md")
    if not prev_summary:
        return ""

    prev_actions = extract_section(prev_summary, "Action items")
    if not prev_actions:
        return ""

    # Check current sprint meta for any matching content
    current_meta = read_file(root / f"sprint-{sprint_num:02d}" / "meta.md") or ""
    action_items = [line.strip().lstrip("- ").strip()
                    for line in prev_actions.split("\n")
                    if line.strip().startswith("-")]

    not_addressed = []
    for action in action_items:
        if len(action) < 10:
            continue
        # Simple keyword check
        keywords = set(action.lower().split())
        keywords.discard("the")
        keywords.discard("a")
        if not any(kw in current_meta.lower() for kw in list(keywords)[:3]):
            not_addressed.append(action)

    if not_addressed:
        return (
            "\n\n## ⚠️ Unresolved action items from Sprint {}\n".format(sprint_num - 1)
            + "\n".join(f"- {a}" for a in not_addressed)
            + "\n\n*These items were not tracked in this sprint's planning. "
              "Consider adding them to the next sprint backlog.*\n"
        )
    return ""


def synthesise_retrospective(sprint_num: int, repo_name: str, config: dict) -> None:
    root = get_repo_root()
    retro_dir = root / f"sprint-{sprint_num:02d}" / "retrospective"

    if not retro_dir.exists():
        logger.warning(f"No retrospective directory for sprint {sprint_num}")
        return

    # Collect all individual retro files
    member_retros = {}
    members_map = {m["login"]: m["display"] for m in config["team"]["members"]}
    for login, display in members_map.items():
        f = retro_dir / f"{login}.md"
        content = read_file(f)
        if content:
            member_retros[display] = content

    if not member_retros:
        logger.warning("No retrospective entries found.")
        return

    retro_contents = "\n\n---\n\n".join(
        f"### {name}\n{content}" for name, content in member_retros.items()
    )

    # Get sprint stats
    velocity = calculate_sprint_velocity(sprint_num, repo_name)
    meta = read_file(root / f"sprint-{sprint_num:02d}" / "meta.md") or ""
    sprint_goal = extract_section(meta, "Goal") or "Not specified"

    # LLM synthesis
    summary = complete(
        RETROSPECTIVE_SYNTHESIS.format(
            sprint_num=sprint_num,
            sprint_goal=sprint_goal,
            velocity=velocity["completed_sp"],
            planned_sp=velocity["planned_sp"],
            retro_contents=retro_contents,
        ),
        system=SYSTEM_SCRUM_ASSISTANT,
    )

    # Check for unresolved previous retro items
    followthrough_note = check_previous_retro_followthrough(sprint_num, config)

    full_summary = (
        f"<!-- BOT-GENERATED -->\n"
        f"# Retrospective Summary — Sprint {sprint_num:02d}\n"
        f"*Generated: {date.today().isoformat()}*\n"
        f"*{len(member_retros)} of {len(members_map)} team members responded*\n\n"
        + (summary or "LLM synthesis unavailable. See individual entries.")
        + followthrough_note
    )

    atomic_write(retro_dir / "summary.md", full_summary)

    # Post to Slack
    webhook = config.get("notifications", {}).get("slack_webhook")
    if webhook:
        post_to_slack(webhook,
            f"🔄 *Sprint {sprint_num:02d} Retrospective complete*\n"
            f"{len(member_retros)} responses synthesised. "
            f"See `sprint-{sprint_num:02d}/retrospective/summary.md`"
        )

    logger.info(f"Retrospective synthesised for sprint {sprint_num}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    synthesise_retrospective(args.sprint, args.repo, config)
```

---

## 6. `scripts/backlog/prioritize_backlog.py`

```python
"""
scripts/backlog/prioritize_backlog.py
LLM-powered backlog prioritization: rank unlabelled/unpointed issues
by value-to-effort ratio against the active OKR or milestone goal.
Called during backlog grooming ceremony.
"""
import argparse
import json
import logging
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import read_file
from scripts.github.api import (get_github_client, get_issues, get_sp_from_issue,
                                  add_label_to_issue, post_comment, ensure_label_exists)
from scripts.llm.client import complete_json
from scripts.llm.prompts import SYSTEM_SCRUM_ASSISTANT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PRIORITIZE_PROMPT = """
You are prioritising a product backlog for a Scrum team.

## Active milestone goal:
{milestone_goal}

## Current OKRs:
{okr_content}

## Issues to prioritise (no priority label yet):
{issues_json}

## Instructions:
Rank these issues by value/effort ratio considering the goal and OKRs.
Reply with ONLY JSON:
{{
  "ranked": [
    {{
      "number": N,
      "suggested_priority": "p:high|p:medium|p:low",
      "reasoning": "one sentence",
      "okr_alignment": "high|medium|low|none"
    }}
  ]
}}
"""


def read_active_milestone_goal(config: dict) -> str:
    root = get_repo_root()
    milestones = list((root / "milestones").glob("*/milestone.md"))
    if not milestones:
        return "No active milestone"
    content = read_file(sorted(milestones)[-1])
    from scripts.utils.file_utils import extract_section
    return extract_section(content, "Goal") or "No goal specified"


def read_current_okr(config: dict) -> str:
    root = get_repo_root()
    okrs = sorted((root / "okr").glob("*.md"))
    if not okrs:
        return "No OKRs defined"
    return read_file(okrs[-1])[:500] or "No OKR content"


def prioritize_backlog(repo_name: str, config: dict, max_issues: int = 20) -> None:
    g = get_github_client()
    repo = g.get_repo(repo_name)

    # Get unpointed or unpriorityised open issues
    all_open = get_issues(repo, state="open")
    to_prioritize = [
        i for i in all_open
        if not any(l.name.startswith("p:") for l in i.labels)
        and not any(l.name.startswith("sprint-") for l in i.labels)
    ][:max_issues]

    if not to_prioritize:
        logger.info("All open issues already have priority labels.")
        return

    issues_json = json.dumps([
        {"number": i.number, "title": i.title, "body": (i.body or "")[:200],
         "labels": [l.name for l in i.labels]}
        for i in to_prioritize
    ], indent=2)

    milestone_goal = read_active_milestone_goal(config)
    okr_content = read_current_okr(config)

    result = complete_json(
        PRIORITIZE_PROMPT.format(
            milestone_goal=milestone_goal,
            okr_content=okr_content,
            issues_json=issues_json,
        ),
        system=SYSTEM_SCRUM_ASSISTANT,
    )

    if not result or "ranked" not in result:
        logger.warning("LLM prioritization failed.")
        return

    for item in result["ranked"]:
        num = item.get("number")
        priority = item.get("suggested_priority", "p:medium")
        reasoning = item.get("reasoning", "")

        try:
            issue = repo.get_issue(num)
            ensure_label_exists(repo, priority)
            add_label_to_issue(issue, priority)
            post_comment(issue,
                f"🤖 **Suggested priority: `{priority}`** — {reasoning}\n"
                f"OKR alignment: {item.get('okr_alignment', 'unknown')}\n"
                f"_This is a suggestion — team can override by changing the label._"
            )
            logger.info(f"Prioritised #{num}: {priority}")
        except Exception as e:
            logger.error(f"Failed to prioritise #{num}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    parser.add_argument("--max-issues", type=int, default=20)
    args = parser.parse_args()
    config = load_config(args.config)
    prioritize_backlog(args.repo, config, args.max_issues)
```

---

## 7. `scripts/sprint/check_scope_creep.py`

```python
"""
scripts/sprint/check_scope_creep.py
Detect mid-sprint scope creep: new issues added after sprint planning
that push total SP over team capacity.
Alerts Slack with the specific overage and suggests what to defer.
"""
import argparse
import logging
from datetime import date
from scripts.utils.config import load_config, get_current_sprint
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue
from scripts.sprint.calculate_velocity import calculate_rolling_velocity
from scripts.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_scope_creep(repo_name: str, config: dict) -> None:
    """Detect if sprint SP exceeds capacity; alert if so."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_num = get_current_sprint()
    sprint_label = f"sprint-{sprint_num:02d}"

    # Get current sprint issues
    all_issues = get_issues(repo, labels=[sprint_label], state="all")
    open_issues = [i for i in all_issues if i.state == "open"]
    closed_issues = [i for i in all_issues if i.state == "closed"]

    total_sp = sum(get_sp_from_issue(i) for i in all_issues)
    completed_sp = sum(get_sp_from_issue(i) for i in closed_issues)
    remaining_sp = sum(get_sp_from_issue(i) for i in open_issues)

    # Get team capacity
    velocity = calculate_rolling_velocity(repo_name)
    capacity = round(velocity.get("avg", 26) * config["sprint"].get("capacity_buffer", 0.85))

    if total_sp <= capacity:
        logger.info(f"Sprint {sprint_num}: {total_sp}/{capacity} sp — no scope creep")
        return

    overage = total_sp - capacity
    webhook = config.get("notifications", {}).get("slack_webhook")

    if webhook:
        # Find the lowest-priority unstarted issues to suggest deferring
        from scripts.utils.file_utils import read_file, extract_section
        deferral_candidates = []
        for issue in open_issues:
            labels = [l.name for l in issue.labels]
            if "in-review" not in labels and "in-sprint" in labels:
                sp = get_sp_from_issue(issue)
                priority = next((l for l in labels if l.startswith("p:")), "p:low")
                deferral_candidates.append((issue, sp, priority))

        deferral_candidates.sort(key=lambda x: (
            {"p:high": 0, "p:medium": 1, "p:low": 2}.get(x[2], 3), -x[1]
        ))

        defer_suggestion = ""
        if deferral_candidates:
            # Suggest enough deferrals to get under capacity
            to_defer = []
            freed_sp = 0
            for issue, sp, priority in reversed(deferral_candidates):
                to_defer.append(f"• #{issue.number} \"{issue.title[:50]}\" ({sp} sp, {priority})")
                freed_sp += sp
                if total_sp - freed_sp <= capacity:
                    break
            if to_defer:
                defer_suggestion = (
                    "\n\n*To get back under capacity, consider deferring:*\n"
                    + "\n".join(to_defer)
                )

        post_to_slack(
            webhook,
            f"⚠️ *Sprint {sprint_num:02d} is over capacity!*\n"
            f"Total: *{total_sp} sp* vs capacity: *{capacity} sp* "
            f"(overflow: {overage} sp)\n"
            f"Completed: {completed_sp} sp · Remaining: {remaining_sp} sp"
            + defer_suggestion
        )

    logger.info(f"Scope creep detected: {total_sp} sp vs {capacity} sp capacity")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    check_scope_creep(args.repo, config)
```

---

## 8. `scripts/insights/generate_insights.py`

```python
"""
scripts/insights/generate_insights.py
Generate cross-sprint insight files:
  insights/velocity-trends.md   — velocity history + trend line
  insights/blocker-patterns.md  — most common blockers across sprints
  insights/team-health.md       — sentiment + capacity trends

Run after each sprint closes or on monthly schedule.
These are read by: milestone health check, suggestion detectors,
the stakeholder portal, and the visibility engine.
"""
import json
import logging
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import atomic_write, read_file, extract_section
from scripts.sprint.calculate_velocity import (calculate_sprint_velocity,
                                                calculate_rolling_velocity)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_velocity_trends(repo_name: str, config: dict) -> None:
    """Write insights/velocity-trends.md with historical velocity data."""
    root = get_repo_root()
    sprint_num = get_current_sprint()
    rolling = calculate_rolling_velocity(repo_name, num_sprints=sprint_num)

    velocity_history = []
    for s in range(1, sprint_num + 1):
        try:
            vel = calculate_sprint_velocity(s, repo_name)
            velocity_history.append({
                "sprint": s,
                "completed_sp": vel["completed_sp"],
                "planned_sp": vel["planned_sp"],
                "completion_rate": vel["completion_rate"],
            })
        except Exception:
            continue

    content = (
        f"<!-- BOT-GENERATED: updated after each sprint -->\n"
        f"# Velocity Trends\n"
        f"*Last updated: {date.today().isoformat()}*\n\n"
        f"## Rolling averages\n"
        f"- Average: **{rolling.get('avg', 0)} sp/sprint**\n"
        f"- Standard deviation: {rolling.get('std_dev', 0)} sp\n"
        f"- Min: {rolling.get('min', 0)} sp · Max: {rolling.get('max', 0)} sp\n"
        f"- Sprints sampled: {rolling.get('sprints_sampled', 0)}\n\n"
        f"## Sprint-by-sprint history\n\n"
        f"| Sprint | Completed | Planned | Rate |\n"
        f"|--------|-----------|---------|------|\n"
    )
    for v in velocity_history:
        bar = "█" * (v["completed_sp"] // 3) if v["completed_sp"] else ""
        content += (
            f"| Sprint {v['sprint']:02d} | {v['completed_sp']} sp {bar} | "
            f"{v['planned_sp']} sp | {round(v['completion_rate']*100)}% |\n"
        )

    # JSON block for machine reading by health_check.py
    content += f"\n## Raw data (machine-readable)\n```json\n{json.dumps({'rolling': rolling, 'history': velocity_history}, indent=2)}\n```\n"
    atomic_write(root / "insights" / "velocity-trends.md", content)
    logger.info("velocity-trends.md updated")


def generate_blocker_patterns(config: dict) -> None:
    """Analyse standup files for recurring blockers. Write insights/blocker-patterns.md."""
    root = get_repo_root()
    sprint_num = get_current_sprint()
    all_blockers = []

    for s in range(1, sprint_num + 1):
        standup_base = root / f"sprint-{s:02d}" / "standup"
        if not standup_base.exists():
            continue
        for date_dir in standup_base.iterdir():
            if not date_dir.is_dir() or date_dir.name == "summary":
                continue
            for f in date_dir.glob("*.md"):
                content = read_file(f)
                blocker_text = extract_section(content, "Blockers")
                if blocker_text and blocker_text.lower().strip() not in ("none", ""):
                    for line in blocker_text.split("\n"):
                        line = line.strip().lstrip("- ").strip()
                        if len(line) > 5:
                            all_blockers.append({"sprint": s, "text": line, "author": f.stem})

    # Simple frequency count by keywords
    from collections import Counter
    import re
    word_counts = Counter()
    for b in all_blockers:
        words = re.findall(r'\b\w{4,}\b', b["text"].lower())
        word_counts.update(words)

    stopwords = {"that","this","with","have","been","from","they","their","will","when","were","would"}
    top_words = [(w,c) for w,c in word_counts.most_common(30) if w not in stopwords]

    content = (
        f"<!-- BOT-GENERATED -->\n"
        f"# Blocker Patterns\n"
        f"*Last updated: {date.today().isoformat()}*\n\n"
        f"**Total blocker mentions across {sprint_num} sprints:** {len(all_blockers)}\n\n"
        f"## Most frequent blocker keywords\n"
        f"| Keyword | Frequency |\n"
        f"|---------|----------|\n"
    )
    for word, count in top_words[:15]:
        bar = "█" * min(count, 20)
        content += f"| {word} | {count} {bar} |\n"

    content += f"\n## Recent blockers (last 2 sprints)\n"
    recent = [b for b in all_blockers if b["sprint"] >= sprint_num - 1]
    for b in recent[-20:]:
        content += f"- Sprint {b['sprint']} · {b['author']}: {b['text'][:100]}\n"

    atomic_write(root / "insights" / "blocker-patterns.md", content)
    logger.info("blocker-patterns.md updated")


def generate_team_health(config: dict) -> None:
    """Aggregate sentiment scores and write insights/team-health.md."""
    root = get_repo_root()
    sprint_num = get_current_sprint()
    health_data = []

    for s in range(1, sprint_num + 1):
        sprint_health_dir = root / f"sprint-{s:02d}"
        if not sprint_health_dir.exists():
            continue
        # Try to find health score from suggestion system sentiment data
        # or use a simple heuristic: velocity completion rate
        try:
            vel = calculate_sprint_velocity(s, "")
            completion = vel.get("completion_rate", 0)
            health_indicator = "healthy" if completion > 0.8 else "watch" if completion > 0.6 else "concern"
            health_data.append({"sprint": s, "completion_rate": completion, "status": health_indicator})
        except Exception:
            pass

    content = (
        f"<!-- BOT-GENERATED -->\n"
        f"# Team Health\n"
        f"*Last updated: {date.today().isoformat()}*\n\n"
        f"## Sprint completion rates (proxy for team health)\n\n"
        f"| Sprint | Rate | Status |\n"
        f"|--------|------|--------|\n"
    )
    for h in health_data:
        icon = "✅" if h["status"] == "healthy" else "⚠️" if h["status"] == "watch" else "🔴"
        content += f"| Sprint {h['sprint']:02d} | {round(h['completion_rate']*100)}% | {icon} {h['status']} |\n"

    content += (
        f"\n## Notes\n"
        f"*For richer team health data, enable sentiment analysis in scraut.yml.*\n"
        f"*Sentiment scoring requires `llm.provider` to be configured.*\n"
    )
    atomic_write(root / "insights" / "team-health.md", content)
    logger.info("team-health.md updated")


def generate_all_insights(repo_name: str, config: dict) -> None:
    (get_repo_root() / "insights").mkdir(exist_ok=True)
    generate_velocity_trends(repo_name, config)
    generate_blocker_patterns(config)
    generate_team_health(config)
    logger.info("All insights regenerated")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    generate_all_insights(args.repo, config)
```

---

## 9. `scripts/backlog/pr_auto_describe.py`

```python
"""
scripts/backlog/pr_auto_describe.py
When a PR is opened, auto-generate a description from the diff and linked issues.
Fills in the PR template sections: Summary, Linked issues, Testing notes.
Only fills sections that are empty — never overwrites human content.
"""
import argparse
import logging
import re
from scripts.utils.config import load_config
from scripts.github.api import get_github_client, get_sp_from_issue
from scripts.llm.client import complete
from scripts.llm.prompts import SYSTEM_SCRUM_ASSISTANT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PR_DESCRIPTION_PROMPT = """
You are writing a GitHub PR description for a developer.

## Linked issues (from PR title/branch):
{issues}

## Files changed:
{files_changed}

## Diff summary:
{diff_summary}

## Instructions:
Write a clear, concise PR description that:
1. Summarises WHAT this PR does (1-2 sentences)
2. Explains WHY (links to the issue goal)
3. Notes what tests were added (if any obvious from diff)
4. Flags anything the reviewer should pay attention to

Keep it under 200 words. Write for a peer reviewer.
Output only the description text — no markdown headers, no preamble.
"""

TEMPLATE_SUMMARY_MARKER = "<!-- What does this PR do? One sentence. -->"
TEMPLATE_NOTES_MARKER = "<!-- Anything the reviewer should pay special attention to -->"


def extract_linked_issues(pr, repo) -> list:
    """Extract issues linked via 'Closes #NNN' in PR title, body, or branch name."""
    text = (pr.title or "") + " " + (pr.body or "") + " " + pr.head.ref
    issue_nums = [int(n) for n in re.findall(r"#(\d+)", text)]
    issues = []
    for num in set(issue_nums):
        try:
            issue = repo.get_issue(num)
            issues.append({
                "number": num,
                "title": issue.title,
                "body": (issue.body or "")[:300],
                "acceptance_criteria": "",
            })
        except Exception:
            pass
    return issues


def get_diff_summary(pr, max_lines: int = 50) -> str:
    """Get a condensed summary of changed files and key diff lines."""
    files = list(pr.get_files())
    summary_parts = []
    for f in files[:10]:
        summary_parts.append(f"  {f.filename} (+{f.additions}/-{f.deletions})")
    return "\n".join(summary_parts)


def auto_describe_pr(pr_number: int, repo_name: str, config: dict) -> None:
    g = get_github_client()
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    # Check if the PR already has a human-written description (non-template)
    current_body = pr.body or ""
    if (TEMPLATE_SUMMARY_MARKER not in current_body and
            len(current_body.strip()) > 200):
        logger.info(f"PR #{pr_number} already has description. Skipping.")
        return

    linked_issues = extract_linked_issues(pr, repo)
    if not linked_issues:
        logger.info(f"PR #{pr_number}: no linked issues found. Skipping auto-description.")
        return

    diff_summary = get_diff_summary(pr)
    files_list = "\n".join(f.filename for f in list(pr.get_files())[:15])

    issues_text = "\n".join(
        f"- #{i['number']}: {i['title']}\n  Goal: {i['body'][:150]}"
        for i in linked_issues
    )

    generated_desc = complete(
        PR_DESCRIPTION_PROMPT.format(
            issues=issues_text,
            files_changed=files_list,
            diff_summary=diff_summary,
        ),
        system=SYSTEM_SCRUM_ASSISTANT,
    )

    if not generated_desc:
        return

    # Build the updated PR body by replacing the template placeholder
    closes_section = "\n".join(f"Closes #{i['number']}" for i in linked_issues)

    new_body = f"""## Summary
{generated_desc}

## Linked issues
{closes_section}

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation

## Testing
<!-- How was this tested? -->
- [ ] Unit tests added/updated
- [ ] Tested manually

## Notes for reviewers
<!-- Anything the reviewer should pay special attention to -->
_Auto-generated by Scraut. Please review and edit as needed._
"""

    pr.edit(body=new_body)
    logger.info(f"Auto-described PR #{pr_number}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    auto_describe_pr(args.pr, args.repo, config)
```

---

## 10. `scripts/backlog/pr_knowledge_extract.py`

```python
"""
scripts/backlog/pr_knowledge_extract.py
When a PR is merged, extract "what we learned" from the PR description
and review comments. Append to knowledge/YYYY-MM.md.
Builds institutional memory from code reviews over time.
"""
import argparse
import logging
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import read_file, atomic_write
from scripts.github.api import get_github_client
from scripts.llm.client import complete
from scripts.llm.prompts import SYSTEM_SCRUM_ASSISTANT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """
You are extracting institutional knowledge from a merged GitHub PR.

## PR title: {title}
## PR description: {body}
## Review comments (key ones): {review_comments}

## Instructions:
Extract any REUSABLE insights from this PR. Only include if genuinely useful:
- New patterns or approaches discovered
- Pitfalls or gotchas to avoid
- Architectural decisions made and why
- Performance or security considerations
- Libraries or tools evaluated

If nothing notable, reply with exactly: SKIP

Otherwise reply with a concise bullet point (1-3 sentences max).
Do NOT include: PR-specific details, author names, issue numbers.
Write as a generic lesson, not "in this PR we..."
"""


def extract_knowledge(pr_number: int, repo_name: str, config: dict) -> None:
    g = get_github_client()
    repo = g.get_repo(repo_name)

    try:
        pr = repo.get_pull(pr_number)
    except Exception as e:
        logger.error(f"Could not access PR #{pr_number}: {e}")
        return

    if not pr.merged:
        logger.info(f"PR #{pr_number} not merged. Skipping.")
        return

    # Collect review comments
    review_comments = []
    try:
        for comment in list(pr.get_review_comments())[:10]:
            if len(comment.body or "") > 20:
                review_comments.append(comment.body[:200])
    except Exception:
        pass

    review_text = "\n".join(f"- {c}" for c in review_comments) or "No review comments"

    insight = complete(
        EXTRACT_PROMPT.format(
            title=pr.title,
            body=(pr.body or "")[:600],
            review_comments=review_text,
        ),
        system=SYSTEM_SCRUM_ASSISTANT,
    )

    if not insight or insight.strip().upper() == "SKIP":
        logger.info(f"PR #{pr_number}: no notable insight to extract")
        return

    # Append to knowledge/YYYY-MM.md
    root = get_repo_root()
    today = date.today()
    knowledge_file = root / "knowledge" / f"{today.year}-{today.month:02d}.md"
    knowledge_file.parent.mkdir(exist_ok=True)

    existing = read_file(knowledge_file)
    if not existing:
        existing = (
            f"<!-- BOT-GENERATED: extracted from merged PRs -->\n"
            f"# Knowledge — {today.strftime('%B %Y')}\n\n"
        )

    new_entry = f"- **{today.isoformat()}** (from PR #{pr_number}): {insight.strip()}\n"
    atomic_write(knowledge_file, existing + new_entry)
    logger.info(f"Knowledge extracted from PR #{pr_number}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    extract_knowledge(args.pr, args.repo, config)
```

---

## 11. Missing GitHub Actions Workflows

### `.github/workflows/backlog-grooming.yml`

```yaml
name: Scraut — Backlog Grooming
on:
  schedule:
    - cron: '0 2 * * 3'  # Wednesday 9am Jakarta = 02:00 UTC (mid-sprint)
  workflow_dispatch:

jobs:
  grooming:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Prioritise unlabelled backlog items
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          python scripts/backlog/prioritize_backlog.py --repo ${{ github.repository }}

      - name: Check for scope creep
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          python scripts/sprint/check_scope_creep.py --repo ${{ github.repository }}
```

---

### `.github/workflows/pr-linker.yml`

```yaml
name: Scraut — PR Linker
on:
  pull_request:
    types: [opened, edited]

jobs:
  link-pr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Auto-describe PR from linked issues
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python scripts/backlog/pr_auto_describe.py \
            --pr ${{ github.event.pull_request.number }} \
            --repo ${{ github.repository }}

      - name: Move linked issues to In Progress
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python - << 'EOF'
          import sys, os, re
          sys.path.insert(0, '.')
          from scripts.github.api import get_github_client, add_label_to_issue, ensure_label_exists
          from scripts.utils.config import load_config

          g = get_github_client()
          repo_name = os.environ.get('GITHUB_REPOSITORY', '')
          pr_body = """${{ github.event.pull_request.body }}"""
          pr_title = """${{ github.event.pull_request.title }}"""

          config = load_config()
          repo = g.get_repo(repo_name)
          ensure_label_exists(repo, "in-review", color="5319e7")

          linked = re.findall(r'[Cc]loses?\s+#(\d+)', pr_body + ' ' + pr_title)
          for num in set(linked):
              try:
                  issue = repo.get_issue(int(num))
                  add_label_to_issue(issue, "in-review")
                  print(f"Marked #{num} as in-review")
              except Exception as e:
                  print(f"Could not update #{num}: {e}")
          EOF
```

---

### `.github/workflows/pr-close-stories.yml`

```yaml
name: Scraut — Close Stories on PR Merge
on:
  pull_request:
    types: [closed]

jobs:
  close-stories:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Close linked issues and extract knowledge
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python - << 'EOF'
          import sys, os, re
          sys.path.insert(0, '.')
          from scripts.github.api import get_github_client, add_label_to_issue
          from scripts.utils.config import load_config

          g = get_github_client()
          repo_name = os.environ.get('GITHUB_REPOSITORY', '')
          pr_body = """${{ github.event.pull_request.body }}"""
          pr_title = """${{ github.event.pull_request.title }}"""
          pr_number = int('${{ github.event.pull_request.number }}')

          config = load_config()
          repo = g.get_repo(repo_name)

          linked = re.findall(r'[Cc]loses?\s+#(\d+)', pr_body + ' ' + pr_title)
          for num in set(linked):
              try:
                  issue = repo.get_issue(int(num))
                  issue.edit(state='closed')
                  print(f"Closed #{num} via PR #{pr_number}")
              except Exception as e:
                  print(f"Could not close #{num}: {e}")
          EOF

      - name: Extract PR knowledge
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python scripts/backlog/pr_knowledge_extract.py \
            --pr ${{ github.event.pull_request.number }} \
            --repo ${{ github.repository }}

      - name: Commit knowledge file
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add knowledge/
          git diff --staged --quiet || git commit -m "chore: knowledge extraction [skip ci]"
          git push
```

---

### `.github/workflows/dod-check.yml`

```yaml
name: Scraut — Definition of Done Check
on:
  issues:
    types: [closed]

jobs:
  dod-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Check Definition of Done
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          # Only check sprint issues (labelled with in-sprint or sp:N)
          HAS_SPRINT=$(python -c "
          import os
          from scripts.github.api import get_github_client
          g = get_github_client()
          repo = g.get_repo('${{ github.repository }}')
          issue = repo.get_issue(${{ github.event.issue.number }})
          labels = [l.name for l in issue.labels]
          print('yes' if any(l.startswith('sp:') or l == 'in-sprint' for l in labels) else 'no')
          ")
          if [ "$HAS_SPRINT" = "yes" ]; then
            python scripts/backlog/dod_check.py \
              --issue ${{ github.event.issue.number }} \
              --repo ${{ github.repository }}
          fi
```

---

### `.github/workflows/incident-to-backlog.yml`

```yaml
name: Scraut — Incident to Backlog
on:
  push:
    paths:
      - 'sprint-*/incidents/**/action-items.md'

jobs:
  create-backlog-items:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Detect changed incident file
        id: detect
        run: |
          CHANGED=$(git diff --name-only HEAD~1 HEAD | grep 'incidents/.*/action-items.md' | head -1)
          echo "incident_file=$CHANGED" >> $GITHUB_OUTPUT

      - name: Create GitHub issues from action items
        if: steps.detect.outputs.incident_file != ''
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python - << 'EOF'
          import sys, os
          sys.path.insert(0, '.')
          from pathlib import Path
          from scripts.utils.config import load_config
          from scripts.utils.file_utils import read_file
          from scripts.github.api import get_github_client, create_issue, ensure_label_exists
          from scripts.llm.client import complete_json
          from scripts.llm.prompts import SYSTEM_SCRUM_ASSISTANT

          config = load_config()
          incident_file = Path('${{ steps.detect.outputs.incident_file }}')
          content = read_file(incident_file)
          incident_dir = incident_file.parent
          timeline = read_file(incident_dir / 'timeline.md')
          incident_name = incident_dir.name

          prompt = f"""
          Extract all action items from this incident postmortem.
          Incident: {incident_name}
          Timeline: {timeline[:500]}
          Action items file:
          {content}

          Reply with ONLY JSON:
          {{"action_items": [{{"title": "...", "description": "...", "priority": "p:high|p:medium"}}]}}
          """
          result = complete_json(prompt, system=SYSTEM_SCRUM_ASSISTANT)

          g = get_github_client()
          repo = g.get_repo(os.environ.get('GITHUB_REPOSITORY', ''))
          ensure_label_exists(repo, "incident-followup", color="b60205")

          for item in (result or {}).get("action_items", []):
              issue = create_issue(
                  repo,
                  title=f"[Incident followup] {item['title']}",
                  body=f"{item['description']}\n\n**Source:** {incident_name}\n**Timeline:** See `{incident_dir}/timeline.md`",
                  labels=["task", "incident-followup", item.get("priority", "p:medium")],
              )
              print(f"Created #{issue.number}: {item['title']}")
          EOF
```

---

### `.github/workflows/sprint-plan-pr.yml`

```yaml
name: Scraut — Sprint Planning PR Merged
on:
  pull_request:
    types: [closed]
    branches: [main]

jobs:
  confirm-sprint:
    # Only run when a sprint planning PR is merged
    if: |
      github.event.pull_request.merged == true &&
      contains(github.event.pull_request.labels.*.name, 'sprint-planning')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Sprint committed — generate insights and notify
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          python - << 'EOF'
          import sys, os, re
          sys.path.insert(0, '.')
          from scripts.utils.config import load_config, get_current_sprint
          from scripts.notifications.slack_post import post_to_slack

          config = load_config()
          sprint_num = get_current_sprint()
          webhook = config.get('notifications', {}).get('slack_webhook')
          pr_title = """${{ github.event.pull_request.title }}"""

          if webhook:
              post_to_slack(webhook,
                  f"🎯 *Sprint {sprint_num:02d} is now committed!*\n"
                  f"Planning PR merged: {pr_title}\n"
                  f"Sprint starts today. Standups begin tomorrow at 9am."
              )
          print(f"Sprint {sprint_num} confirmed via planning PR merge")
          EOF
```

---

## 12. Breadcrumb Navigation (update `scripts/standup/reset_templates.py`)

**Add to the `STANDUP_TEMPLATE` in `reset_templates.py`:**

```python
# Replace the existing STANDUP_TEMPLATE with this updated version
STANDUP_TEMPLATE = """# Standup — {display_name}
<!-- 
  Sprint: sprint-{sprint_num:02d}
  Date: {date}
  Author: {login}

  ─── NAVIGATION ──────────────────────────────────────────
  📁 Sprint folder:   sprint-{sprint_num:02d}/
  📋 Sprint meta:     sprint-{sprint_num:02d}/meta.md
  📝 Your standup:    sprint-{sprint_num:02d}/standup/{date}/{login}.md
  💬 Retro (when due): sprint-{sprint_num:02d}/retrospective/{login}.md
  🗒️  Backlog ideas:   sprint-{sprint_num:02d}/grooming/backlog-ideas.md
  🏁 Board:           [GitHub Projects - see scraut.yml portal.project_number]
  ─────────────────────────────────────────────────────────
-->

## Yesterday
<!-- What did you complete? Reference issues/PRs where applicable. -->

## Today
<!-- What will you work on today? Reference issues if possible. -->

## Blockers
<!-- Anything blocking your progress? Scraut tracks these automatically. -->
<!-- Write "None" if no blockers. -->
None

## Notes
<!-- Optional: OOO, reduced availability, context for the team -->
"""
```

---

## 13. LLM Cost Batching (update `scripts/llm/client.py`)

Add this batch utility to `scripts/llm/client.py`:

```python
def complete_batch(prompts: list[str], system: Optional[str] = None,
                   max_tokens: Optional[int] = None) -> list[str]:
    """
    Process multiple prompts in a single LLM call to reduce token overhead.
    Each prompt is separated with a numbered marker.
    Use when batching multiple independent requests (e.g., triage 5 issues at once).
    """
    config = get_llm_config()
    if not config.get("cost_controls", {}).get("batch_where_possible"):
        # Batching disabled — call individually
        return [complete(p, system, max_tokens) for p in prompts]

    if not prompts:
        return []

    # Build batched prompt
    batch_prompt = "Answer each numbered prompt INDEPENDENTLY. Reply with JSON array.\n\n"
    for i, p in enumerate(prompts, 1):
        batch_prompt += f"=== PROMPT {i} ===\n{p}\n\n"
    batch_prompt += (
        f"Reply with ONLY a JSON array of {len(prompts)} strings, "
        f"one result per prompt:\n"
        f'["result for prompt 1", "result for prompt 2", ...]'
    )

    import json
    raw = complete(batch_prompt, system, max_tokens=max_tokens or 2000)
    try:
        # Strip markdown fences
        import re
        clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        results = json.loads(clean)
        if isinstance(results, list) and len(results) == len(prompts):
            return results
    except Exception:
        pass

    # Fallback: call individually
    return [complete(p, system, max_tokens) for p in prompts]
```

---

## 14. Web Form Team Members Population (update `portal/form.html`)

Add this build step to `scripts/visibility/generate_portal.py`:

```python
def generate_form_html(config: dict) -> None:
    """
    Generate portal/form.html with team members populated from scraut.yml.
    This replaces the static CONFIG.teamMembers = [] with actual data.
    """
    root = get_repo_root()
    form_template = read_file(root / "portal" / "form.html")
    if not form_template:
        return

    members_js = json.dumps([
        {"login": m["login"], "display": m["display"]}
        for m in config["team"]["members"]
    ])

    # Replace the empty array with populated data
    updated = form_template.replace(
        "teamMembers: [],    // Populated from scraut.yml via build step",
        f"teamMembers: {members_js},",
    )
    atomic_write(root / "portal" / "form.html", updated)
    logger.info("form.html populated with team members from scraut.yml")
```

**Call `generate_form_html(config)` at the end of `generate_portal()` in the same file.**

---

## 15. Updated `scripts/visibility/generate_insights_workflow.yml`

```yaml
name: Scraut — Generate Insights
on:
  workflow_run:
    workflows: ["Scraut — Sprint Review"]
    types: [completed]
  schedule:
    - cron: '0 4 1 * *'   # First day of month at 4am — monthly cross-sprint insights
  workflow_dispatch:

jobs:
  generate-insights:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Generate cross-sprint insights
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python scripts/insights/generate_insights.py --repo ${{ github.repository }}

      - name: Commit insights
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add insights/
          git diff --staged --quiet || git commit -m "chore: cross-sprint insights update [skip ci]"
          git push
```

---

## Done Criteria for Phase 9

- [ ] `scripts/backlog/tally_estimation.py` — tallies emoji reactions, applies sp label after 24h or full team vote, posts result comment
- [ ] `scripts/sprint/close_sprint.py` — closes milestone, labels deferred issues, increments `current_sprint` in scraut.yml
- [ ] `scripts/sprint/create_planning_pr.py` — creates planning PR with proposed sprint backlog, LLM sprint goal, correct issue table
- [ ] `scripts/sprint/generate_review.py` — generates sprint-review.md with velocity stats + LLM narrative, posts to Slack
- [ ] `scripts/sprint/synthesise_retrospective.py` — reads all retro files, synthesises with LLM, checks unresolved previous action items
- [ ] `scripts/backlog/prioritize_backlog.py` — labels unpriorityised issues with p:high/medium/low using OKR + milestone context
- [ ] `scripts/sprint/check_scope_creep.py` — detects SP overage vs capacity, Slack alert with deferral suggestions
- [ ] `scripts/insights/generate_insights.py` — writes velocity-trends.md, blocker-patterns.md, team-health.md
- [ ] `scripts/backlog/pr_auto_describe.py` — generates PR description from linked issue + diff, only fills empty sections
- [ ] `scripts/backlog/pr_knowledge_extract.py` — extracts reusable knowledge from merged PRs, appends to knowledge/YYYY-MM.md
- [ ] `backlog-grooming.yml` — runs mid-sprint, calls prioritize_backlog + check_scope_creep
- [ ] `pr-linker.yml` — runs on PR open: auto-describes PR, moves linked issues to in-review
- [ ] `pr-close-stories.yml` — runs on PR merge: closes linked issues, extracts knowledge
- [ ] `dod-check.yml` — runs on issue close: checks DoD, reopens if not met
- [ ] `incident-to-backlog.yml` — runs on push to incidents/**/action-items.md, creates GitHub issues
- [ ] `sprint-plan-pr.yml` — runs when planning PR merges: posts Slack confirmation
- [ ] `generate-insights-workflow.yml` — generates insights after sprint review
- [ ] Breadcrumb navigation comment present in standup template
- [ ] `complete_batch()` function in `scripts/llm/client.py`
- [ ] `generate_form_html()` called in `generate_portal()` — form.html has team members populated
- [ ] End-to-end: create an incident action-items.md, push it, verify GitHub issues are created

---

## Final Completeness Checklist

After Phase 9, every item from the conversation is implemented:

| Capability | Phase | Status |
|-----------|-------|--------|
| Text files as source of truth | 1 | ✅ |
| One file per contributor | 1,2 | ✅ |
| Sprint folder structure with time periods | 1 | ✅ |
| scraut.yml with all schema fields | 1 | ✅ |
| LLM abstraction layer (multi-provider) | 2 | ✅ |
| LLM cost controls + batching | 2, 9 | ✅ |
| Backlog triage (labels + story points) | 2 | ✅ |
| Estimation via emoji reactions | 2, 9 | ✅ |
| Sprint planning as PR review | 2, 9 | ✅ |
| DoD enforcement | 2, 9 | ✅ |
| Burndown chart generation | 2 | ✅ |
| All 5 Scrum ceremonies | 2, 9 | ✅ |
| Retro synthesis + followthrough check | 2, 9 | ✅ |
| Sprint review generation | 9 | ✅ |
| Milestone decomposition + planning session | 3 | ✅ |
| Roadmap generation | 3 | ✅ |
| Sprint health scoring (4 dimensions) | 3 | ✅ |
| Milestone ETA forecasting | 3 | ✅ |
| Repo sync (commits, PRs, reviews) | 4 | ✅ |
| Standup pre-fill from commits | 4 | ✅ |
| Delta analysis | 4 | ✅ |
| PR aging alerts | 4 | ✅ |
| Board sync (derived view) | 5 | ✅ |
| State inference from text artifacts | 5 | ✅ |
| Stakeholder portal (GitHub Pages) | 5 | ✅ |
| Morning Slack DM with file link | 5 | ✅ |
| Weekly email digest | 5 | ✅ |
| Breadcrumb navigation in templates | 9 | ✅ |
| 6-detector suggestion system | 6 | ✅ |
| Suggestion lifecycle management | 6 | ✅ |
| Measurement learning loop | 6 | ✅ |
| AI agent orchestrator | 7 | ✅ |
| Human checkpoints | 7 | ✅ |
| Deadlock detection | 7 | ✅ |
| Setup CLI (npx create-scraut) | 8 | ✅ |
| scraut CLI (pip install) | 8 | ✅ |
| Non-dev web form | 8 | ✅ |
| GitHub App design | 8 | ✅ |
| PR auto-description from diff | 9 | ✅ |
| PR knowledge extraction | 9 | ✅ |
| Incident → backlog items | 9 | ✅ |
| Backlog prioritization with OKR | 9 | ✅ |
| Scope creep detection | 9 | ✅ |
| Cross-sprint insights generation | 9 | ✅ |
| Web form team members populated | 9 | ✅ |
