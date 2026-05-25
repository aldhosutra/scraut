"""
scrum/standup/coach.py
Detect vague Today sections in standups and DM personalised task
recommendations to affected team members.

Detection is deterministic (word count + issue reference check).
Recommendations are LLM-generated using sprint goal + open issues + OKR context.
Output is a private Slack DM — nothing is posted to the team channel.

Usage:
  python -m scraut.scrum.standup.coach --date 2026-05-25 --repo myorg/my-repo
  python -m scraut.scrum.standup.coach --dry-run
"""
import argparse
import logging
import re
from datetime import date
from pathlib import Path
from typing import Optional

from scraut.platform.utils.config import (
    load_config, get_workspace_root, get_scraut_root,
    get_current_sprint, get_sprint_folder, get_folder_padding,
)
from scraut.platform.utils.file_utils import read_file, extract_section, format_sprint_num, glob_md
from scraut.platform.utils.date_utils import get_sprint_dates, working_days_remaining, working_days_elapsed
from scraut.platform.github.api import get_github_client, get_issues, get_sp_from_issue
from scraut.platform.llm.client import complete
from scraut.platform.llm.prompts import SYSTEM_SCRUM_ASSISTANT, STANDUP_COACH_RECOMMENDATION
from scraut.platform.notifications.slack_post import send_slack_dm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Phrases in the Today section that indicate the update is legitimately low-specificity.
# A standup containing any of these is not flagged regardless of word count.
_EXEMPT_PHRASES = frozenset([
    "code review", "pr review", "pull request review",
    "pairing", "pair programming",
    "onboarding",
    "sprint planning", "sprint review", "retrospective", "grooming", "backlog",
    "all-hands", "all hands",
    "interview",
    "out of office", "ooo",
    "sick", "sick leave", "medical",
    "holiday", "public holiday",
    "travel",
])


def is_today_vague(
    content: str,
    min_words: int = 20,
    require_issue_ref: bool = True,
) -> bool:
    """Return True if the Today section appears too vague to be actionable.

    False negatives (missing a vague standup) are acceptable.
    False positives (flagging a legitimate standup) are not — be conservative.
    """
    today_text = extract_section(content, "Today")
    if not today_text:
        return False

    stripped = today_text.strip().lower()
    if stripped in ("", "none", "tbd", "—", "-", "n/a"):
        return False  # empty is handled by generate_summary's missing-member logic

    # Long enough text is treated as specific enough
    if len(today_text.split()) >= min_words:
        return False

    # Has at least one issue reference
    if require_issue_ref and re.search(r"#\d+", today_text):
        return False

    # Contains a known legitimate vague-but-valid phrase
    lower = today_text.lower()
    for phrase in _EXEMPT_PHRASES:
        if phrase in lower:
            return False

    return True


def _get_open_sprint_issues(repo_name: str, sprint_num: int, login: str) -> list[dict]:
    """Return open sprint issues assigned to login, capped at 10."""
    try:
        g = get_github_client()
        repo = g.get_repo(repo_name)
        sprint_label = f"sprint-{format_sprint_num(sprint_num, get_folder_padding())}"
        issues = get_issues(repo, labels=[sprint_label, "in-sprint"], state="open")
        return [
            {
                "number": i.number,
                "title": i.title,
                "sp": get_sp_from_issue(i),
            }
            for i in issues
            if any(a.login == login for a in i.assignees)
        ][:10]
    except Exception as exc:
        logger.warning(f"Could not fetch open issues for {login}: {exc}")
        return []


def _fallback_recommendation(display: str, open_issues: list[dict]) -> str:
    """Plain-text recommendation used when LLM is unavailable."""
    if not open_issues:
        return (
            f"Looks like your standup today didn't mention specific issues, {display}. "
            "Check the sprint board for your open items and pick the one most aligned "
            "with the sprint goal. Adding issue numbers tomorrow helps the whole team "
            "track dependencies."
        )
    top = open_issues[:3]
    issue_list = ", ".join(f"#{i['number']} ({i['title']})" for i in top)
    return (
        f"Your standup today didn't reference specific issues, {display}. "
        f"Based on your open sprint items, consider focusing on: {issue_list}. "
        "Referencing issue numbers in tomorrow's standup helps the team spot "
        "dependencies early — keep it up!"
    )


def build_recommendation(
    display: str,
    login: str,
    sprint_goal: str,
    open_issues: list[dict],
    okr_text: str,
    days_elapsed: int,
    days_remaining: int,
    config: dict,
) -> str:
    """Call the LLM to generate a personalised task recommendation."""
    issues_text = "\n".join(
        f"  - #{i['number']}: {i['title']} ({i['sp']} sp)"
        for i in open_issues
    ) or "  (no open sprint issues currently assigned)"

    prompt = STANDUP_COACH_RECOMMENDATION.format(
        display=display,
        sprint_goal=sprint_goal,
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        issues_text=issues_text,
        okr_text=(okr_text[:400] if okr_text else "Not defined"),
    )
    result = complete(prompt, system=SYSTEM_SCRUM_ASSISTANT, use_small_model=True)
    return result or _fallback_recommendation(display, open_issues)


def run_coach(
    config: dict,
    target_date: Optional[str] = None,
    repo_name: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    """Main entry point. Reads standups, detects vague Today sections, sends DMs."""
    coach_cfg = config.get("standup_coach", {})
    if not coach_cfg.get("enabled", False):
        logger.info("Standup coach disabled (standup_coach.enabled: false) — skipping")
        return

    min_words = int(coach_cfg.get("min_today_words", 20))
    require_issue_ref = bool(coach_cfg.get("require_issue_ref", True))
    skip_days = int(coach_cfg.get("skip_sprint_start_days", 1))
    notify_sm = bool(coach_cfg.get("notify_sm", False))

    today = date.fromisoformat(target_date) if target_date else date.today()
    sprint_num = get_current_sprint()
    scraut_root = get_scraut_root()

    sprint_start, sprint_end = get_sprint_dates(sprint_num, config)
    elapsed = working_days_elapsed(sprint_start, config, scraut_root)

    if elapsed < skip_days:
        logger.info(
            f"Standup coach skipping sprint day {elapsed + 1} "
            f"(skip_sprint_start_days: {skip_days})"
        )
        return

    days_remaining = working_days_remaining(sprint_end, config, scraut_root)

    # Read sprint context once — shared across all team member recommendations
    meta = read_file(get_sprint_folder(sprint_num) / "meta.md")
    sprint_goal = extract_section(meta, "Goal") if meta else "Not specified"

    root = get_workspace_root()
    okr_files = glob_md(root / "okr")
    okr_text = read_file(okr_files[-1])[:400] if okr_files else ""

    standup_dir = get_sprint_folder(sprint_num) / "standup" / today.isoformat()
    members = {m["login"]: m for m in config["team"]["members"]}
    coached: list[str] = []

    for login, member in members.items():
        standup_path = standup_dir / f"{login}.md"
        content = read_file(standup_path)
        if not content:
            continue  # missing standup — handled by generate_summary

        if not is_today_vague(content, min_words, require_issue_ref):
            continue

        display = member["display"]
        slack_id = member.get("slack_id", "")
        logger.info(f"Coaching {display} ({login}) — Today section flagged as vague")

        open_issues = (
            _get_open_sprint_issues(repo_name, sprint_num, login)
            if repo_name else []
        )

        message = build_recommendation(
            display=display,
            login=login,
            sprint_goal=sprint_goal,
            open_issues=open_issues,
            okr_text=okr_text,
            days_elapsed=elapsed,
            days_remaining=days_remaining,
            config=config,
        )

        if dry_run:
            logger.info(f"[dry-run] DM to {display} ({slack_id or 'no slack_id'}):\n{message}\n")
        elif not slack_id:
            logger.warning(f"No slack_id configured for {display} — cannot send DM")
        else:
            send_slack_dm(slack_id, message, config)
            coached.append(display)
            logger.info(f"DM sent to {display}")

    if not coached and not dry_run:
        logger.info("No vague standups detected today — no coaching DMs sent")

    # Optional SM summary
    if notify_sm and coached and not dry_run:
        sm_login = config.get("team", {}).get("scrum_master", "")
        sm_member = members.get(sm_login)
        if sm_member and sm_member.get("slack_id"):
            names = "\n".join(f"• {name}" for name in coached)
            sm_msg = (
                f"*Standup Coach — {today.isoformat()}*\n"
                f"Task recommendations were sent privately to:\n{names}\n"
                f"Their Today sections didn't reference specific sprint issues."
            )
            send_slack_dm(sm_member["slack_id"], sm_msg, config)
            logger.info(f"SM summary DM sent to {sm_member['display']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standup coach — detect vague Today sections and DM recommendations")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD, default: today)")
    parser.add_argument("--repo", help="GitHub repo (org/repo)")
    parser.add_argument("--config", default="workspace/scraut.yml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    run_coach(cfg, target_date=args.date, repo_name=args.repo, dry_run=args.dry_run)
