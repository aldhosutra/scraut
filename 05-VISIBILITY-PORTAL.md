# Phase 5: Visibility Portal
*Scraut Implementation — requires Phases 1–4 complete*

## Goal
Build the visibility engine that reads all text artifacts and syncs the GitHub
Projects board as a derived view. Generate the static stakeholder portal (GitHub
Pages). Send morning Slack DMs with direct standup links. Send weekly email digests.
The board is NEVER edited directly — it is always regenerated from text files.

---

## Architecture

```
Any push to sprint-*/standup/**, sprint-*/code/**, milestones/*/health/**
  ↓
visibility-engine.yml (also runs on 30-min schedule as heartbeat)
  ↓
scripts/visibility/derive_state.py
  → reads all artifact files
  → applies inference rules to determine column for each issue
  → returns {issue_number: IssueState}
  ↓
scripts/visibility/sync_board.py
  → calls GitHub Projects GraphQL API
  → updates Status, Agent, Health, SP Remaining, Last Activity, Sprint, Blocker fields
  ↓
scripts/visibility/generate_portal.py
  → reads forecast.md, meta.md, velocity data, health reports
  → renders static HTML dashboard to portal/index.html
  ↓
portal-publish.yml
  → pushes portal/ to gh-pages branch
```

---

## 1. `scripts/visibility/derive_state.py`

The core inference engine. Reads text artifacts, derives board state for each issue.
Deterministic rules first; LLM only for genuinely ambiguous cases.

```python
"""
scripts/visibility/derive_state.py
Read all Scraut text artifacts and derive the current state of each issue.
Returns a dict of {issue_number: IssueState} for the board sync to consume.

Inference priority (highest confidence first):
1. merged PR closing the issue → Done
2. "completed" or "closes #N" in Yesterday section + date=today → Done
3. open PR linked to the issue → Review
4. issue number in Blockers section → In Progress (blocked)
5. issue number in Today section (today's standup) → In Progress
6. ambiguous mentions → LLM classification
7. in current sprint roadmap, not mentioned → Ready
8. not in current sprint roadmap → Backlog
"""
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import read_file, extract_section
from scripts.github.api import get_github_client, get_issues

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VALID_COLUMNS = ["Backlog", "Ready", "In Progress", "Review", "Testing", "Done"]


@dataclass
class IssueState:
    column: str
    agent: str = ""
    health: str = "on-track"   # on-track | watch | blocked
    sp_remaining: int = 0
    last_activity: str = ""
    blocker: str = ""
    confidence: float = 1.0
    source: str = ""           # which artifact triggered this state


def extract_issue_refs(text: str) -> list[int]:
    return [int(n) for n in re.findall(r"#(\d+)", text)]


def scan_standup_files(config: dict, target_date: Optional[str] = None) -> dict:
    """
    Scan all standup files for a date range and build a signal map.
    Returns {issue_number: [{"section": "Today|Yesterday|Blockers", "author": login, "text": ...}]}
    """
    if target_date is None:
        target_date = date.today().isoformat()

    root = get_repo_root()
    sprint_num = get_current_sprint()
    standup_dir = root / f"sprint-{sprint_num:02d}" / "standup"
    signals = {}  # issue_num → list of signal dicts

    # Scan last 3 days of standups to catch recent activity
    from datetime import timedelta
    check_dates = []
    d = date.fromisoformat(target_date)
    for i in range(3):
        check_dates.append((d - timedelta(days=i)).isoformat())

    for check_date in check_dates:
        date_dir = standup_dir / check_date
        if not date_dir.exists():
            continue

        for standup_file in date_dir.glob("*.md"):
            author = standup_file.stem
            if author.startswith("agent-"):
                continue  # handle agents separately
            content = read_file(standup_file)
            if not content:
                continue

            for section_name in ["Yesterday", "Today", "Blockers"]:
                section_text = extract_section(content, section_name)
                issue_nums = extract_issue_refs(section_text)
                for num in issue_nums:
                    if num not in signals:
                        signals[num] = []
                    signals[num].append({
                        "section": section_name,
                        "author": author,
                        "text": section_text,
                        "date": check_date,
                        "is_today": check_date == target_date,
                    })

    return signals


def scan_agent_standups(config: dict, target_date: Optional[str] = None) -> dict:
    """Scan agent standup files and return per-agent issue signals."""
    if target_date is None:
        target_date = date.today().isoformat()

    root = get_repo_root()
    sprint_num = get_current_sprint()
    standup_dir = root / f"sprint-{sprint_num:02d}" / "standup" / target_date
    agent_signals = {}

    if not standup_dir.exists():
        return agent_signals

    for standup_file in standup_dir.glob("agent-*.md"):
        agent_id = standup_file.stem
        content = read_file(standup_file)
        if not content:
            continue
        today_section = extract_section(content, "Today")
        blockers_section = extract_section(content, "Blockers")
        agent_state_section = extract_section(content, "Agent State")

        for num in extract_issue_refs(today_section):
            agent_signals[num] = {"agent": agent_id, "status": "working",
                                  "text": today_section}
        for num in extract_issue_refs(blockers_section):
            agent_signals.setdefault(num, {}).update(
                {"agent": agent_id, "status": "blocked", "blocker": blockers_section}
            )

    return agent_signals


def get_pr_issue_map(repo_name: str) -> dict[int, dict]:
    """Return {issue_number: {"state": open|merged, "pr_number": N}} from open PRs."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    pr_map = {}
    try:
        for pr in repo.get_pulls(state="all", sort="updated", direction="desc"):
            # Only look at recent PRs (updated in last 30 days)
            from datetime import timezone
            from datetime import datetime, timedelta
            cutoff = datetime.now(tz=timezone.utc) - timedelta(days=30)
            if pr.updated_at.replace(tzinfo=timezone.utc) < cutoff:
                break
            body = pr.body or ""
            closes = [int(n) for n in re.findall(r"[Cc]loses?\s+#(\d+)", body)]
            for issue_num in closes:
                pr_map[issue_num] = {
                    "pr_number": pr.number,
                    "state": "merged" if pr.merged else "open",
                }
    except Exception as e:
        logger.warning(f"Failed to scan PRs: {e}")
    return pr_map


def get_sprint_roadmap_issues(config: dict) -> set[int]:
    """Get issue numbers mentioned in the current sprint's roadmap (Ready state)."""
    root = get_repo_root()
    sprint_num = get_current_sprint()
    meta = read_file(root / f"sprint-{sprint_num:02d}" / "meta.md")
    return set(extract_issue_refs(meta))


def classify_ambiguous(issue_num: int, signals: list[dict]) -> IssueState:
    """Use LLM to classify an issue with ambiguous signals."""
    from scripts.llm.client import complete_json
    context = "\n".join(
        f"- [{s['date']} {s['section']} by {s['author']}]: {s['text'][:200]}"
        for s in signals
    )
    prompt = (
        f"Based on these standup mentions for GitHub issue #{issue_num}, "
        f"determine its current status.\n\nMentions:\n{context}\n\n"
        f"Reply with ONLY JSON: "
        f'{{\"column\": "In Progress|Review|Done|Blocked", '
        f'"health": "on-track|watch|blocked", "reasoning": "one sentence"}}'
    )
    result = complete_json(prompt)
    col = result.get("column", "In Progress")
    if col not in VALID_COLUMNS:
        col = "In Progress"
    return IssueState(
        column=col,
        health=result.get("health", "on-track"),
        confidence=0.6,
        source="llm",
    )


def derive_all_states(repo_name: str, config: dict,
                      target_date: Optional[str] = None) -> dict[int, IssueState]:
    """
    Main entry point: derive state for all sprint issues.
    Returns {issue_number: IssueState}
    """
    if target_date is None:
        target_date = date.today().isoformat()

    states = {}
    signals = scan_standup_files(config, target_date)
    agent_signals = scan_agent_standups(config, target_date)
    pr_map = get_pr_issue_map(repo_name)
    sprint_issues = get_sprint_roadmap_issues(config)

    # Get all issues from GitHub
    from scripts.github.api import get_sp_from_issue
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_num = get_current_sprint()
    sprint_label = f"sprint-{sprint_num:02d}"
    all_sprint_issues = get_issues(repo, labels=[sprint_label], state="all")

    for issue in all_sprint_issues:
        num = issue.number
        sp = get_sp_from_issue(issue)
        state = None

        # Rule 1: merged PR closing this issue → Done
        if pr_map.get(num, {}).get("state") == "merged" or issue.state == "closed":
            state = IssueState(column="Done", confidence=1.0,
                               source="merged_pr_or_closed", sp_remaining=0)

        # Rule 2: open PR for this issue → Review
        elif pr_map.get(num, {}).get("state") == "open":
            state = IssueState(column="Review", confidence=1.0, source="open_pr",
                               sp_remaining=max(0, sp - 1))

        # Rule 3: in Blockers section today → blocked
        elif num in signals and any(
            s["section"] == "Blockers" and s["is_today"] for s in signals[num]
        ):
            blocker_text = next(
                s["text"] for s in signals[num]
                if s["section"] == "Blockers" and s["is_today"]
            )
            author = next(s["author"] for s in signals[num]
                          if s["section"] == "Blockers" and s["is_today"])
            state = IssueState(column="In Progress", health="blocked",
                               agent=author, blocker=blocker_text[:100],
                               confidence=0.9, source="blockers_section",
                               sp_remaining=sp)

        # Rule 4: agent is working on it
        elif num in agent_signals:
            agent_info = agent_signals[num]
            state = IssueState(
                column="In Progress",
                agent=agent_info.get("agent", ""),
                health="blocked" if agent_info.get("status") == "blocked" else "on-track",
                blocker=agent_info.get("blocker", "")[:100],
                confidence=0.9, source="agent_standup",
                sp_remaining=sp,
            )

        # Rule 5: in Today section today → WIP
        elif num in signals and any(
            s["section"] == "Today" and s["is_today"] for s in signals[num]
        ):
            author = next(s["author"] for s in signals[num]
                          if s["section"] == "Today" and s["is_today"])
            state = IssueState(column="In Progress", agent=author,
                               confidence=0.85, source="today_section",
                               sp_remaining=sp,
                               last_activity=target_date)

        # Rule 6: ambiguous signals → LLM
        elif num in signals and len(signals[num]) > 1:
            state = classify_ambiguous(num, signals[num])
            state.sp_remaining = sp

        # Rule 7: in sprint roadmap, no signals → Ready
        elif num in sprint_issues:
            state = IssueState(column="Ready", confidence=0.7,
                               source="roadmap", sp_remaining=sp)

        # Rule 8: default → Backlog
        else:
            state = IssueState(column="Backlog", confidence=1.0,
                               source="default", sp_remaining=sp)

        states[num] = state

    logger.info(f"Derived states for {len(states)} issues")
    return states
```

---

## 2. `scripts/visibility/sync_board.py`

```python
"""
scripts/visibility/sync_board.py
Sync the GitHub Projects board from derived issue states.
Uses the GraphQL API. Never the source of truth — always derived from text.
"""
import logging
import os
from typing import Optional
from scripts.utils.config import load_config
from scripts.github.projects import (get_project_id, get_project_items,
                                      get_field_ids, update_item_status,
                                      update_item_text_field)
from scripts.visibility.derive_state import derive_all_states, IssueState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sync_board(repo_name: str, project_number: int, config: dict,
               dry_run: bool = False) -> None:
    """
    Main sync function. Derives all issue states from text artifacts,
    then updates the GitHub Projects board to reflect those states.
    """
    owner = repo_name.split("/")[0]
    token = os.environ.get("GITHUB_TOKEN")

    logger.info(f"Syncing board for {repo_name} project #{project_number}")

    # Derive states from text artifacts
    states = derive_all_states(repo_name, config)

    # Get project metadata
    project_id = get_project_id(owner, project_number, token)
    field_ids = get_field_ids(project_id, token)
    items = get_project_items(project_id, token)

    # Build issue number → project item ID map
    item_map = {}
    for item in items:
        content = item.get("content") or {}
        issue_num = content.get("number")
        if issue_num:
            item_map[issue_num] = item["id"]

    # Get field and option IDs
    status_field = field_ids.get("Status", {})
    status_field_id = status_field.get("id")
    status_options = status_field.get("options", {})

    agent_field_id = field_ids.get("Agent", {}).get("id")
    health_field_id = field_ids.get("Health", {}).get("id")
    sp_field_id = field_ids.get("SP Remaining", {}).get("id")
    last_activity_field_id = field_ids.get("Last Activity", {}).get("id")
    sprint_field_id = field_ids.get("Sprint", {}).get("id")
    blocker_field_id = field_ids.get("Blocker", {}).get("id")

    sprint_num = config["sprint"]["current_sprint"]
    sprint_label = f"sprint-{sprint_num:02d}"
    updated = 0

    for issue_num, state in states.items():
        item_id = item_map.get(issue_num)
        if not item_id:
            logger.debug(f"Issue #{issue_num} not in project. Skipping.")
            continue

        if dry_run:
            logger.info(f"[DRY RUN] #{issue_num}: {state.column} "
                        f"(health={state.health}, agent={state.agent})")
            continue

        try:
            # Update status column
            if status_field_id and state.column in status_options:
                update_item_status(
                    project_id, item_id,
                    status_field_id, status_options[state.column], token
                )

            # Update text fields
            if agent_field_id and state.agent:
                update_item_text_field(project_id, item_id,
                                       agent_field_id, state.agent, token)

            if health_field_id:
                health_options = field_ids.get("Health", {}).get("options", {})
                if state.health in health_options:
                    update_item_status(project_id, item_id,
                                       health_field_id,
                                       health_options[state.health], token)

            if blocker_field_id and state.blocker:
                update_item_text_field(project_id, item_id,
                                       blocker_field_id, state.blocker[:200], token)

            if sprint_field_id:
                update_item_text_field(project_id, item_id,
                                       sprint_field_id, sprint_label, token)

            updated += 1

        except Exception as e:
            logger.error(f"Failed to update #{issue_num}: {e}")

    logger.info(f"Board sync complete: {updated}/{len(states)} issues updated")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--project", type=int, required=True,
                        help="GitHub Projects v2 number")
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    sync_board(args.repo, args.project, config, args.dry_run)
```

---

## 3. `scripts/visibility/generate_portal.py`

Generates the static HTML stakeholder dashboard from text artifacts.
No GitHub login required to view it. Published to GitHub Pages.

```python
"""
scripts/visibility/generate_portal.py
Render static HTML stakeholder portal from Scraut text artifacts.
Output goes to portal/index.html — published to GitHub Pages by portal-publish.yml.
Designed for non-technical stakeholders: plain English, no GitHub jargon.
"""
import json
import logging
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import read_file, atomic_write, extract_section
from scripts.sprint.calculate_velocity import calculate_rolling_velocity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PORTAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{team_title} — Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: #f5f5f7; color: #1d1d1f; padding: 0; }}
  header {{ background: #1d1d1f; color: white; padding: 24px 32px; }}
  header h1 {{ font-size: 22px; font-weight: 600; }}
  header p {{ font-size: 13px; color: #aeaeb2; margin-top: 4px; }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 32px 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
           gap: 16px; margin-bottom: 24px; }}
  .card {{ background: white; border-radius: 12px; padding: 20px;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .card-label {{ font-size: 11px; font-weight: 600; color: #86868b;
                  text-transform: uppercase; letter-spacing: .04em; margin-bottom: 8px; }}
  .card-value {{ font-size: 36px; font-weight: 500; color: #1d1d1f; }}
  .card-sub {{ font-size: 13px; color: #86868b; margin-top: 4px; }}
  .bar-container {{ background: #e5e5ea; border-radius: 4px; height: 8px;
                    margin-top: 12px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 4px; transition: width .3s; }}
  .status-badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px;
                   font-size: 12px; font-weight: 600; }}
  .on-track {{ background: #d1fae5; color: #065f46; }}
  .watch {{ background: #fef3c7; color: #92400e; }}
  .at-risk {{ background: #fee2e2; color: #991b1b; }}
  .blockers {{ background: white; border-radius: 12px; padding: 20px;
               box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 16px; }}
  .blockers h3 {{ font-size: 14px; font-weight: 600; margin-bottom: 12px; }}
  .blocker-item {{ padding: 10px 0; border-bottom: 1px solid #f2f2f7;
                   font-size: 13px; color: #3a3a3c; }}
  .blocker-item:last-child {{ border-bottom: none; }}
  footer {{ text-align: center; padding: 24px; font-size: 12px; color: #aeaeb2; }}
</style>
</head>
<body>
<header>
  <h1>{team_title}</h1>
  <p>Last updated: {generated_at} &nbsp;·&nbsp; Sprint {sprint_num} of {total_sprints}</p>
</header>
<div class="container">

  <div class="grid">
    <div class="card">
      <div class="card-label">Milestone progress</div>
      <div class="card-value">{percent_done}%</div>
      <div class="card-sub">{delivered_sp} of {total_sp} story points delivered</div>
      <div class="bar-container">
        <div class="bar-fill" style="width:{percent_done}%;background:{progress_color}"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-label">Sprint</div>
      <div class="card-value">{sprint_num}</div>
      <div class="card-sub">of {total_sprints} planned &nbsp;·&nbsp;
        <span class="status-badge {status_class}">{status_text}</span>
      </div>
    </div>

    <div class="card">
      <div class="card-label">Expected completion</div>
      <div class="card-value">{eta_sprints}</div>
      <div class="card-sub">sprint{eta_plural} remaining · target: {target_sprints}</div>
    </div>

    <div class="card">
      <div class="card-label">Team velocity</div>
      <div class="card-value">{avg_velocity}</div>
      <div class="card-sub">story points per sprint (avg last {velocity_sprints} sprints)</div>
    </div>
  </div>

  {blockers_section}

  <div class="card" style="margin-bottom: 16px;">
    <div class="card-label">This sprint</div>
    <p style="font-size:14px;color:#3a3a3c;line-height:1.7;margin-top:8px;">{sprint_summary}</p>
  </div>

</div>
<footer>Scraut Visibility Portal · auto-generated from team activity data · no login required</footer>
</body>
</html>
"""

BLOCKERS_HTML = """
  <div class="blockers">
    <h3>⚠️ Active blockers ({count})</h3>
    {items}
  </div>
"""


def read_forecast(config: dict) -> dict:
    """Read the latest active milestone forecast."""
    root = get_repo_root()
    milestones_dir = root / "milestones"
    if not milestones_dir.exists():
        return {}

    # Find the most recently modified forecast.md
    forecasts = list(milestones_dir.glob("*/health/forecast.md"))
    if not forecasts:
        return {}

    latest = max(forecasts, key=lambda p: p.stat().st_mtime)
    content = read_file(latest)

    result = {}
    for line in content.split("\n"):
        if line.startswith("**Status:**"):
            result["status"] = line.replace("**Status:**", "").strip()
        elif line.startswith("**Sprint:**"):
            parts = line.replace("**Sprint:**", "").strip().split(" of ")
            if len(parts) == 2:
                result["sprint_num"] = parts[0].strip()
                result["total_sprints"] = parts[1].replace("planned", "").strip()
        elif line.startswith("**Points delivered:**"):
            val = line.replace("**Points delivered:**", "").strip()
            if " of " in val:
                parts = val.split(" of ")
                result["delivered_sp"] = parts[0].strip().split(" ")[0]
                result["total_sp"] = parts[1].strip().split(" ")[0]
        elif line.startswith("**Updated ETA:**"):
            result["eta"] = line.replace("**Updated ETA:**", "").strip()

    return result


def read_blockers(config: dict) -> list[str]:
    """Read active blockers from today's standup files."""
    root = get_repo_root()
    sprint_num = get_current_sprint()
    today = date.today().isoformat()
    standup_dir = root / f"sprint-{sprint_num:02d}" / "standup" / today
    blockers = []

    if not standup_dir.exists():
        return blockers

    members_map = {m["login"]: m["display"] for m in config["team"]["members"]}
    for login, display in members_map.items():
        f = standup_dir / f"{login}.md"
        content = read_file(f)
        if not content:
            continue
        blocker_text = extract_section(content, "Blockers")
        if blocker_text and blocker_text.lower() not in ("none", ""):
            for line in blocker_text.split("\n"):
                line = line.strip().lstrip("- ").strip()
                if line:
                    # Strip GitHub issue numbers (jargon) for portal
                    import re
                    plain = re.sub(r"#\d+", "", line).strip()
                    blockers.append(f"<div class='blocker-item'><strong>{display}:</strong> {plain}</div>")

    return blockers


def generate_portal(config: dict) -> None:
    root = get_repo_root()
    portal_dir = root / "portal"
    portal_dir.mkdir(exist_ok=True)

    forecast = read_forecast(config)
    velocity = calculate_rolling_velocity("")  # will use cached from config

    sprint_num = forecast.get("sprint_num", str(get_current_sprint()))
    total_sprints = forecast.get("total_sprints", "?")
    delivered_sp = forecast.get("delivered_sp", "0")
    total_sp = forecast.get("total_sp", "?")
    status = forecast.get("status", "on-track").lower().replace(" ", "-")
    eta = forecast.get("eta", "unknown")

    # Compute percent
    try:
        pct = round(int(delivered_sp) / int(total_sp) * 100)
    except (ValueError, ZeroDivisionError):
        pct = 0

    # Color
    progress_color = "#34c759" if pct >= 70 else "#ff9f0a" if pct >= 40 else "#ff3b30"
    status_class = ("on-track" if "on-track" in status
                    else "at-risk" if "risk" in status else "watch")
    status_text = status.replace("-", " ").title()

    # ETA
    try:
        eta_val = float(eta.replace(" sprints", "").strip())
        eta_remaining = max(0, round(eta_val - float(sprint_num)))
    except Exception:
        eta_remaining = "?"
    eta_plural = "s" if eta_remaining != 1 else ""

    # Blockers
    blockers = read_blockers(config)
    if blockers:
        blockers_html = BLOCKERS_HTML.format(
            count=len(blockers),
            items="\n".join(blockers)
        )
    else:
        blockers_html = ""

    # Sprint summary from latest summary file
    sprint_summary_path = (root / f"sprint-{sprint_num:02d}" / "standup" /
                           "summary" / f"{date.today().isoformat()}.md")
    sprint_summary_content = read_file(sprint_summary_path)
    # Take first 2 paragraphs, strip markdown, truncate
    import re
    plain_summary = re.sub(r"[*#`\[\]()]", "", sprint_summary_content or "")
    plain_summary = " ".join(plain_summary.split())[:400] or "No summary available yet."

    team_title = config.get("portal", {}).get("title", "Team Dashboard")

    html = PORTAL_HTML.format(
        team_title=team_title,
        generated_at=f"{date.today().isoformat()} (auto-generated)",
        sprint_num=sprint_num,
        total_sprints=total_sprints,
        percent_done=pct,
        delivered_sp=delivered_sp,
        total_sp=total_sp,
        progress_color=progress_color,
        status_class=status_class,
        status_text=status_text,
        eta_sprints=eta_remaining,
        eta_plural=eta_plural,
        target_sprints=total_sprints,
        avg_velocity=velocity.get("avg", "?"),
        velocity_sprints=velocity.get("sprints_sampled", 0),
        blockers_section=blockers_html,
        sprint_summary=plain_summary,
    )

    atomic_write(portal_dir / "index.html", html)

    # Write data.json for potential future use
    data = {
        "generated": date.today().isoformat(),
        "sprint": sprint_num,
        "total_sprints": total_sprints,
        "percent_done": pct,
        "status": status,
        "velocity_avg": velocity.get("avg"),
    }
    atomic_write(portal_dir / "data.json", json.dumps(data, indent=2))
    logger.info("Portal generated successfully")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    generate_portal(config)
```

---

## 4. `scripts/notifications/morning_dm.py`

```python
"""
scripts/notifications/morning_dm.py
Send a personal Slack DM to each team member at 7:55am with
a direct link to their standup file for today.
This eliminates the "where is my file today?" discovery problem.
"""
import logging
from datetime import date
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.notifications.slack_post import send_slack_dm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_standup_url(login: str, repo_name: str, config: dict) -> str:
    """Generate the GitHub.com URL for today's standup file."""
    sprint_num = get_current_sprint()
    today = date.today().isoformat()
    # GitHub.com URL format for editing a file
    branch = "main"
    file_path = f"sprint-{sprint_num:02d}/standup/{today}/{login}.md"
    return (f"https://github.com/{repo_name}/edit/{branch}/{file_path}"
            f"?message=standup%3A+{today}+%5Bskip+ci%5D")


def send_morning_dms(repo_name: str, config: dict) -> None:
    """Send morning DMs to all team members with their standup link."""
    for member in config["team"]["members"]:
        login = member["login"]
        display = member["display"]
        slack_id = member.get("slack_id")

        if not slack_id:
            logger.warning(f"No slack_id for {display}. Skipping DM.")
            continue

        url = get_standup_url(login, repo_name, config)
        sprint_num = get_current_sprint()
        today = date.today().isoformat()

        message = (
            f"Good morning, {display}! 👋\n\n"
            f"*Sprint {sprint_num:02d} • {today}*\n\n"
            f"Your standup file is ready:\n"
            f"→ <{url}|Click to open and fill in your update>\n\n"
            f"_Takes about 2 minutes. Fill in Today and Blockers — "
            f"Yesterday is pre-filled from your commits._"
        )

        success = send_slack_dm(slack_id, message)
        if success:
            logger.info(f"Sent morning DM to {display}")
        else:
            logger.warning(f"Failed to send DM to {display}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    send_morning_dms(args.repo, config)
```

---

## 5. `scripts/notifications/weekly_digest.py`

```python
"""
scripts/notifications/weekly_digest.py
Generate and send the weekly HTML email digest to stakeholders.
Plain English. No PR numbers. No branch names. No GitHub jargon.
Uses SMTP via GitHub Actions.
"""
import logging
import smtplib
import os
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import read_file, extract_section
from scripts.visibility.generate_portal import read_forecast
from scripts.sprint.calculate_velocity import calculate_rolling_velocity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMAIL_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: -apple-system, Arial, sans-serif; margin: 0; background: #f5f5f5; }}
  .wrap {{ max-width: 600px; margin: 0 auto; background: white; }}
  .header {{ background: #1d1d1f; color: white; padding: 24px; }}
  .header h1 {{ margin: 0; font-size: 20px; }}
  .header p {{ margin: 4px 0 0; font-size: 13px; color: #aeaeb2; }}
  .body {{ padding: 24px; }}
  .metric {{ display: inline-block; margin-right: 24px; margin-bottom: 16px; }}
  .metric-val {{ font-size: 28px; font-weight: 600; color: #1d1d1f; }}
  .metric-lbl {{ font-size: 12px; color: #86868b; margin-top: 2px; }}
  .section {{ margin-bottom: 20px; }}
  .section h2 {{ font-size: 14px; color: #86868b; font-weight: 600;
                  text-transform: uppercase; letter-spacing: .04em; margin-bottom: 8px; }}
  .section p {{ font-size: 14px; line-height: 1.7; color: #3a3a3c; }}
  .blocker {{ background: #fff3cd; padding: 10px 14px; border-radius: 6px;
               margin-bottom: 6px; font-size: 13px; color: #856404; }}
  .footer {{ background: #f5f5f7; padding: 16px 24px; font-size: 12px; color: #86868b; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px;
             font-size: 12px; font-weight: 600; }}
  .green {{ background: #d1fae5; color: #065f46; }}
  .yellow {{ background: #fef3c7; color: #92400e; }}
  .red {{ background: #fee2e2; color: #991b1b; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>{team_title} — Weekly Update</h1>
    <p>Week of {week_of} &nbsp;·&nbsp; Sprint {sprint_num}</p>
  </div>
  <div class="body">
    <div class="section">
      <div class="metric">
        <div class="metric-val">{percent_done}%</div>
        <div class="metric-lbl">Goal progress</div>
      </div>
      <div class="metric">
        <div class="metric-val">{eta}</div>
        <div class="metric-lbl">Expected completion</div>
      </div>
      <div class="metric">
        <div class="metric-val">{velocity}</div>
        <div class="metric-lbl">Story points / sprint</div>
      </div>
      <div class="metric">
        <span class="badge {status_class}">{status_text}</span>
        <div class="metric-lbl">Project health</div>
      </div>
    </div>

    <div class="section">
      <h2>This week</h2>
      <p>{this_week_summary}</p>
    </div>

    {blockers_section}

    <div class="section">
      <h2>Next week</h2>
      <p>{next_week_plan}</p>
    </div>
  </div>
  <div class="footer">
    Auto-generated by Scraut &nbsp;·&nbsp; {generated_date} &nbsp;·&nbsp;
    <a href="{portal_url}">View live dashboard</a>
  </div>
</div>
</body>
</html>
"""


def build_email_content(config: dict) -> str:
    """Build the HTML email body from Scraut artifacts."""
    forecast = read_forecast(config)
    velocity = calculate_rolling_velocity("")

    sprint_num = forecast.get("sprint_num", str(get_current_sprint()))
    delivered_sp = forecast.get("delivered_sp", "0")
    total_sp = forecast.get("total_sp", "?")
    status = forecast.get("status", "on-track")
    eta = forecast.get("eta", "unknown")

    try:
        pct = round(int(delivered_sp) / int(total_sp) * 100)
    except Exception:
        pct = 0

    status_class = ("green" if "on-track" in status.lower()
                    else "red" if "risk" in status.lower() else "yellow")
    status_text = status.replace("-", " ").title()

    # Read latest sprint review or summary
    root = get_repo_root()
    review_path = root / f"sprint-{sprint_num:02d}" / "review" / "sprint-review.md"
    review_content = read_file(review_path)
    this_week = extract_section(review_content, "Summary") if review_content else ""
    if not this_week:
        import re
        this_week = re.sub(r"[*#`]", "", review_content or "")[:300] or "Team continued sprint work."

    # Read blockers from standup summaries
    from datetime import date as dt, timedelta
    blockers_html = ""
    blockers = []
    for i in range(5):
        d = dt.today() - timedelta(days=i)
        summary_path = (root / f"sprint-{sprint_num:02d}" / "standup" /
                        "summary" / f"{d.isoformat()}.md")
        content = read_file(summary_path)
        if content:
            blocker_text = extract_section(content, "Blockers")
            if blocker_text and "none" not in blocker_text.lower():
                blockers.append(blocker_text[:150])

    if blockers:
        items = "\n".join(f"<div class='blocker'>{b}</div>" for b in blockers[-3:])
        blockers_html = (
            f"<div class='section'><h2>Active blockers</h2>{items}</div>"
        )

    portal_url = (f"https://{config.get('portal', {}).get('org_slug', 'org')}.github.io/"
                  f"{config.get('portal', {}).get('repo_slug', 'scraut')}/")

    from datetime import date as date_type
    week_of = date_type.today().strftime("%B %d, %Y")

    return EMAIL_HTML.format(
        team_title=config.get("portal", {}).get("title", "Team Dashboard"),
        week_of=week_of,
        sprint_num=sprint_num,
        percent_done=pct,
        eta=eta,
        velocity=velocity.get("avg", "?"),
        status_class=status_class,
        status_text=status_text,
        this_week_summary=this_week,
        blockers_section=blockers_html,
        next_week_plan="Team will continue with planned sprint work. See dashboard for details.",
        generated_date=date_type.today().isoformat(),
        portal_url=portal_url,
    )


def send_weekly_digest(config: dict) -> None:
    emails = config.get("notifications", {}).get("stakeholder_emails", [])
    if not emails:
        logger.info("No stakeholder emails configured. Skipping digest.")
        return

    html_body = build_email_content(config)

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        logger.warning("SMTP credentials not set. Skipping email.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (f"Weekly Update: Sprint {get_current_sprint()} — "
                      f"{config.get('portal', {}).get('title', 'Team')}")
    msg["From"] = smtp_user
    msg["To"] = ", ".join(emails)
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, emails, msg.as_string())
        logger.info(f"Weekly digest sent to {len(emails)} recipients")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    send_weekly_digest(config)
```

---

## 6. GitHub Actions Workflows

### `.github/workflows/visibility-engine.yml`

```yaml
name: Scraut — Visibility Engine
on:
  push:
    paths:
      - 'sprint-*/standup/**'
      - 'sprint-*/code/**'
      - 'milestones/*/health/**'
      - 'sprint-*/review/**'
  schedule:
    - cron: '*/30 * * * *'  # Heartbeat every 30 minutes
  workflow_dispatch:

jobs:
  sync-board:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Sync board from text artifacts
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          PROJECT_NUM=$(python -c "
          import yaml
          cfg = yaml.safe_load(open('scraut.yml'))
          print(cfg.get('portal', {}).get('project_number', '1'))
          ")
          python scripts/visibility/sync_board.py \
            --repo ${{ github.repository }} \
            --project $PROJECT_NUM

  generate-portal:
    needs: sync-board
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Generate stakeholder portal
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/visibility/generate_portal.py

      - name: Commit portal
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add portal/
          git diff --staged --quiet || git commit -m "chore: portal update [skip ci]"
          git push
```

---

### `.github/workflows/portal-publish.yml`

```yaml
name: Scraut — Publish Portal to GitHub Pages
on:
  push:
    paths: ['portal/**']
    branches: [main]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  publish:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: './portal'
      - uses: actions/deploy-pages@v4
        id: deployment
```

---

### `.github/workflows/morning-notification.yml`

```yaml
name: Scraut — Morning Standup Notification
on:
  schedule:
    - cron: '55 0 * * 1-5'  # 7:55 AM Jakarta (UTC+7) = 00:55 UTC
  workflow_dispatch:

jobs:
  send-dms:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Send morning standup DMs
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
        run: |
          python scripts/notifications/morning_dm.py --repo ${{ github.repository }}
```

---

### `.github/workflows/weekly-digest.yml`

```yaml
name: Scraut — Weekly Stakeholder Digest
on:
  schedule:
    - cron: '0 1 * * 1'  # Monday 8:00 AM Jakarta = 01:00 UTC
  workflow_dispatch:

jobs:
  send-digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Send weekly digest
        env:
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASS: ${{ secrets.SMTP_PASS }}
        run: python scripts/notifications/weekly_digest.py
```

---

## Done Criteria for Phase 5

- [ ] `scripts/visibility/derive_state.py` — correct column for: merged PR → Done, open PR → Review, blocked → blocked, today section → WIP, not mentioned but in sprint → Ready
- [ ] `scripts/visibility/derive_state.py` — confidence scores assigned; LLM only called for genuinely ambiguous states
- [ ] `scripts/visibility/sync_board.py` — updates Status, Agent, Health, Blocker fields on GitHub Projects board
- [ ] `scripts/visibility/sync_board.py` — `--dry-run` mode prints proposed changes without updating board
- [ ] `scripts/visibility/generate_portal.py` — generates `portal/index.html` readable in a browser without any GitHub account
- [ ] `scripts/visibility/generate_portal.py` — shows milestone progress, sprint number, ETA, velocity, active blockers in plain English
- [ ] `scripts/notifications/morning_dm.py` — sends Slack DM to each member with a direct edit URL for their standup file
- [ ] `scripts/notifications/weekly_digest.py` — generates and sends HTML email with correct data
- [ ] `visibility-engine.yml` — triggers on push to standup and code paths AND on 30-min schedule
- [ ] `portal-publish.yml` — deploys portal/ to GitHub Pages successfully
- [ ] `morning-notification.yml` — runs at correct time
- [ ] Board test: push a standup file with `## Today: #42`, run `sync_board.py --dry-run`, verify issue #42 shows as "In Progress"

*Proceed to `06-SUGGESTIONS.md`*
