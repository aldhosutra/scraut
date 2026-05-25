"""
scrum/.scraut/suggestions/detectors.py
All 6 Scraut pattern detectors. Pure scripts — deterministic, no LLM.
Each detector:
  - Reads Scraut text artifacts
  - Returns Evidence object if threshold exceeded
  - Returns None if no pattern detected

Detectors:
  1. BlockerFrequencyDetector   — same blocker theme ≥3 times in last 2 sprints
  2. VelocityDropDetector       — >15% sustained velocity drop over 2 sprints
  3. PRReviewLagDetector        — avg PR open-to-first-review >48h this sprint
  4. CapacityImbalanceDetector  — one member >130%, another <70% median load
  5. RetroFollowthroughDetector — retro action items not in subsequent sprints
  6. SentimentTrendDetector     — LLM sentiment score declining ≥2 sprints
"""
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from scraut.platform.utils.config import load_config, get_workspace_root, get_current_sprint, get_sprint_folder, get_sprint_output_folder, format_sprint_num, get_folder_padding
from scraut.platform.utils.file_utils import read_file, extract_section
from scraut.platform.github.api import get_github_client, get_sp_from_issue, get_issues
from scraut.scrum.sprint.calculate_velocity import calculate_sprint_velocity, calculate_rolling_velocity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Evidence:
    detector_name: str
    pattern_description: str
    instances: list[dict]             # Each: {sprint, date, file, quote}
    estimated_impact: str             # Human-readable impact estimate
    metrics_before: dict              # Baseline metrics (for later measurement)
    severity: str = "medium"          # low | medium | high
    threshold_met: bool = True


# ─────────────────────────────────────────────────────────
# Detector 1: Blocker Frequency
# ─────────────────────────────────────────────────────────
def blocker_frequency_detector(config: dict,
                                min_occurrences: int = 3) -> Optional[Evidence]:
    """Detect when the same type of blocker recurs across ≥2 sprints."""
    root = get_workspace_root()
    sprint_num = get_current_sprint()
    all_blockers = []

    for s in range(max(1, sprint_num - 1), sprint_num + 1):
        standup_base = get_sprint_folder(s) / "standup"
        if not standup_base.exists():
            continue
        for date_dir in standup_base.iterdir():
            if not date_dir.is_dir() or date_dir.name == "summary":
                continue
            for f in date_dir.glob("*.md"):
                content = read_file(f)
                blocker_text = extract_section(content, "Blockers")
                if not blocker_text or blocker_text.lower().strip() == "none":
                    continue
                for line in blocker_text.split("\n"):
                    line = line.strip().lstrip("- ").strip()
                    if len(line) > 5:
                        all_blockers.append({
                            "sprint": s,
                            "date": date_dir.name,
                            "author": f.stem,
                            "file": str(f.relative_to(root)),
                            "text": line[:200],
                        })

    if len(all_blockers) < min_occurrences:
        return None

    # Simple theme clustering by keyword frequency
    themes = _cluster_by_keywords(all_blockers)
    top_theme = max(themes.items(), key=lambda x: len(x[1]), default=(None, []))

    if not top_theme[0] or len(top_theme[1]) < min_occurrences:
        return None

    theme_name, theme_instances = top_theme
    severity = "high" if len(theme_instances) >= 5 else "medium"

    return Evidence(
        detector_name="BlockerFrequencyDetector",
        pattern_description=(
            f"Blocker theme '{theme_name}' mentioned {len(theme_instances)} times "
            f"across {len(set(i['sprint'] for i in theme_instances))} sprints"
        ),
        instances=theme_instances[:10],
        estimated_impact="Estimated -4 to -8 sp/sprint in deferred work",
        metrics_before={
            "blocker_mentions": len(theme_instances),
            "sprints_affected": len(set(i["sprint"] for i in theme_instances)),
            "theme": theme_name,
        },
        severity=severity,
    )


def _cluster_by_keywords(blockers: list[dict]) -> dict[str, list[dict]]:
    """Simple keyword-based clustering. No LLM — just keyword matching."""
    keyword_groups = {
        "pr review": ["review", r"\bpr\b", "pull request", "waiting for review", "needs review"],
        "design approval": ["design", "mockup", "figma", "approval", "ux"],
        "external dependency": ["external", "third party", "vendor", "waiting on", "blocked by team"],
        "environment": ["environment", "staging", "deploy", "infra", "server", "database"],
        "unclear requirements": ["unclear", "requirements", "spec", "need more info", "waiting for clarification"],
        "testing": [r"\btest\b", "qa", "bug", "regression", "failing"],
    }
    clusters = {k: [] for k in keyword_groups}

    for blocker in blockers:
        text_lower = blocker["text"].lower()
        matched = False
        for theme, keywords in keyword_groups.items():
            if any(re.search(kw, text_lower) for kw in keywords):
                clusters[theme].append(blocker)
                matched = True
                break
        if not matched:
            clusters.setdefault("other", []).append(blocker)

    return {k: v for k, v in clusters.items() if v}


# ─────────────────────────────────────────────────────────
# Detector 2: Velocity Drop
# ─────────────────────────────────────────────────────────
def velocity_drop_detector(repo_name: str, config: dict,
                            drop_threshold: float = 0.15,
                            min_sprints: int = 2) -> Optional[Evidence]:
    """Detect sustained velocity drop >15% over 2+ consecutive sprints."""
    sprint_num = get_current_sprint()
    if sprint_num < 1:
        return None

    baseline = calculate_rolling_velocity(repo_name, num_sprints=5)
    avg = baseline.get("avg", 0)
    if avg == 0:
        return None

    recent_drops = []
    for s in range(max(1, sprint_num - min_sprints + 1), sprint_num + 1):
        vel = calculate_sprint_velocity(s, repo_name)
        completed = vel.get("completed_sp", 0)
        if completed < avg * (1 - drop_threshold):
            drop_pct = round((avg - completed) / avg * 100)
            recent_drops.append({
                "sprint": s,
                "completed_sp": completed,
                "baseline_avg": avg,
                "drop_percent": drop_pct,
                "file": f"sprint-{format_sprint_num(s, get_folder_padding())}/meta.md",
                "text": f"Sprint {s}: {completed} sp completed vs {avg} sp avg ({drop_pct}% below average)",
                "date": f"sprint-{format_sprint_num(s, get_folder_padding())}",
                "author": "scraut-velocity",
                "quote": f"{completed} sp completed vs {avg:.1f} sp baseline avg",
            })

    if len(recent_drops) < min_sprints:
        return None

    avg_drop = sum(d["drop_percent"] for d in recent_drops) / len(recent_drops)
    return Evidence(
        detector_name="VelocityDropDetector",
        pattern_description=(
            f"Velocity {avg_drop:.0f}% below baseline for {len(recent_drops)} consecutive sprints"
        ),
        instances=recent_drops,
        estimated_impact=f"Lost ~{round(avg * avg_drop / 100)} sp/sprint vs historical average",
        metrics_before={
            "baseline_avg": avg,
            "recent_sprints": recent_drops,
            "avg_drop_percent": avg_drop,
        },
        severity="high" if avg_drop > 25 else "medium",
    )


# ─────────────────────────────────────────────────────────
# Detector 3: PR Review Lag
# ─────────────────────────────────────────────────────────
def pr_review_lag_detector(repo_name: str, config: dict,
                            sla_hours: int = 48) -> Optional[Evidence]:
    """Detect when average PR review wait exceeds the team SLA."""
    from datetime import timezone, datetime
    g = get_github_client()
    try:
        repo = g.get_repo(repo_name)
    except Exception as e:
        logger.warning(f"Could not access repo {repo_name}: {e}")
        return None

    sprint_num = get_current_sprint()
    lag_instances = []
    total_wait_hours = []

    try:
        for pr in repo.get_pulls(state="all", sort="updated", direction="desc"):
            from datetime import timedelta as td
            cutoff = datetime.now(tz=timezone.utc) - td(days=30)
            if pr.updated_at.replace(tzinfo=timezone.utc) < cutoff:
                break
            if pr.user.login not in [m["login"] for m in config["team"]["members"]]:
                continue

            reviews = list(pr.get_reviews())
            if not reviews:
                if pr.state == "open":
                    age_hours = (datetime.now(tz=timezone.utc) -
                                  pr.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                    if age_hours > sla_hours:
                        lag_instances.append({
                            "sprint": sprint_num,
                            "date": pr.created_at.date().isoformat(),
                            "file": f"PR #{pr.number}",
                            "author": pr.user.login,
                            "text": f"PR #{pr.number} open {age_hours:.0f}h with no reviews",
                            "quote": f"PR #{pr.number}: \"{pr.title[:60]}\" — {age_hours:.0f}h with no review",
                        })
            else:
                first_review = min(r.submitted_at for r in reviews
                                   if r.submitted_at is not None)
                wait_hours = (first_review.replace(tzinfo=timezone.utc) -
                               pr.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                total_wait_hours.append(wait_hours)
                if wait_hours > sla_hours:
                    lag_instances.append({
                        "sprint": sprint_num,
                        "date": pr.created_at.date().isoformat(),
                        "file": f"PR #{pr.number}",
                        "author": pr.user.login,
                        "text": f"PR #{pr.number} waited {wait_hours:.0f}h for first review",
                        "quote": f"PR #{pr.number}: \"{pr.title[:60]}\" — {wait_hours:.0f}h wait",
                    })
    except Exception as e:
        logger.warning(f"PR scan failed: {e}")
        return None

    if len(lag_instances) < 3:
        return None

    avg_wait = sum(total_wait_hours) / len(total_wait_hours) if total_wait_hours else 0
    return Evidence(
        detector_name="PRReviewLagDetector",
        pattern_description=(
            f"{len(lag_instances)} PRs exceeded {sla_hours}h review SLA. "
            f"Average review wait: {avg_wait:.1f}h."
        ),
        instances=lag_instances[:8],
        estimated_impact="Review delays directly cause story deferral and velocity loss",
        metrics_before={
            "avg_wait_hours": round(avg_wait, 1),
            "sla_hours": sla_hours,
            "prs_over_sla": len(lag_instances),
            "total_prs_sampled": len(total_wait_hours),
        },
        severity="high" if avg_wait > 72 else "medium",
    )


# ─────────────────────────────────────────────────────────
# Detector 4: Capacity Imbalance
# ─────────────────────────────────────────────────────────
def capacity_imbalance_detector(repo_name: str, config: dict,
                                 high_threshold: float = 1.3,
                                 low_threshold: float = 0.7) -> Optional[Evidence]:
    """Detect when one team member is >130% loaded while another is <70%."""
    sprint_num = get_current_sprint()
    g = get_github_client()
    try:
        repo = g.get_repo(repo_name)
    except Exception:
        return None

    sprint_label = f"sprint-{format_sprint_num(sprint_num, get_folder_padding())}"
    member_sp = {}
    for member in config["team"]["members"]:
        login = member["login"]
        try:
            issues = [i for i in get_issues(repo, labels=[sprint_label], state="all")
                      if any(a.login == login for a in i.assignees)]
            member_sp[login] = sum(get_sp_from_issue(i) for i in issues)
        except Exception:
            member_sp[login] = 0

    if not member_sp or len(member_sp) < 2:
        return None

    avg_load = sum(member_sp.values()) / len(member_sp)
    if avg_load == 0:
        return None

    overloaded = [(login, sp) for login, sp in member_sp.items()
                  if sp > avg_load * high_threshold]
    underloaded = [(login, sp) for login, sp in member_sp.items()
                   if sp < avg_load * low_threshold]

    if not overloaded or not underloaded:
        return None

    display_map = {m["login"]: m["display"] for m in config["team"]["members"]}
    instances = []
    for login, sp in overloaded:
        pct = round(sp / avg_load * 100)
        instances.append({
            "sprint": sprint_num, "date": date.today().isoformat(),
            "file": f"sprint-{format_sprint_num(sprint_num, get_folder_padding())}/meta.md",
            "author": login,
            "text": f"{display_map.get(login, login)}: {sp} sp ({pct}% of team avg)",
            "quote": f"{display_map.get(login, login)} assigned {sp} sp vs {avg_load:.0f} avg",
        })
    for login, sp in underloaded:
        pct = round(sp / avg_load * 100)
        instances.append({
            "sprint": sprint_num, "date": date.today().isoformat(),
            "file": f"sprint-{format_sprint_num(sprint_num, get_folder_padding())}/meta.md",
            "author": login,
            "text": f"{display_map.get(login, login)}: {sp} sp ({pct}% of team avg — underutilised)",
            "quote": f"{display_map.get(login, login)} assigned only {sp} sp vs {avg_load:.0f} avg",
        })

    return Evidence(
        detector_name="CapacityImbalanceDetector",
        pattern_description=(
            f"{len(overloaded)} member(s) overloaded, {len(underloaded)} underutilised in Sprint {sprint_num}"
        ),
        instances=instances,
        estimated_impact="Uneven load causes burnout for the overloaded member and idle time for others",
        metrics_before={
            "avg_team_sp": round(avg_load, 1),
            "member_loads": member_sp,
        },
        severity="medium",
    )


# ─────────────────────────────────────────────────────────
# Detector 5: Retro Follow-through
# ─────────────────────────────────────────────────────────
def retro_followthrough_detector(config: dict,
                                  min_missed: int = 2) -> Optional[Evidence]:
    """Detect when retro action items don't appear in subsequent sprint planning."""
    root = get_workspace_root()
    sprint_num = get_current_sprint()
    missed_items = []

    for s in range(1, sprint_num):
        retro_summary = read_file(get_sprint_output_folder(s) / "retrospective" / "summary.md")
        if not retro_summary:
            continue

        actions_text = extract_section(retro_summary, "Action items")
        if not actions_text:
            continue

        # Extract action item lines
        action_items = [line.strip().lstrip("- ").strip()
                        for line in actions_text.split("\n")
                        if line.strip().startswith("-") and len(line.strip()) > 5]

        # Check if each action item appears in subsequent sprint metas
        for action in action_items[:5]:  # Check first 5 items
            appeared = False
            keywords = set(re.findall(r'\b\w{4,}\b', action.lower()))
            for future_s in range(s + 1, sprint_num + 1):
                future_meta = read_file(get_sprint_folder(future_s) / "meta.md")
                future_meta_lower = (future_meta or "").lower()
                if any(kw in future_meta_lower for kw in keywords):
                    appeared = True
                    break

            if not appeared and len(action) > 10:
                missed_items.append({
                    "sprint": s,
                    "date": f"sprint-{format_sprint_num(s, get_folder_padding())}",
                    "file": f"sprint-{format_sprint_num(s, get_folder_padding())}/retrospective/summary.md",
                    "author": "retrospective",
                    "text": f"Sprint {s} action item not tracked in subsequent sprints: '{action[:80]}'",
                    "quote": action[:100],
                })

    if len(missed_items) < min_missed:
        return None

    return Evidence(
        detector_name="RetroFollowthroughDetector",
        pattern_description=(
            f"{len(missed_items)} retrospective action items from past sprints "
            f"never appeared in subsequent sprint planning"
        ),
        instances=missed_items[:8],
        estimated_impact="Retro value is lost if action items are not tracked to completion",
        metrics_before={
            "missed_action_items": len(missed_items),
            "sprints_checked": sprint_num - 1,
        },
        severity="medium",
    )


# ─────────────────────────────────────────────────────────
# Detector 6: Sentiment Trend
# ─────────────────────────────────────────────────────────
def sentiment_trend_detector(config: dict,
                              declining_threshold: int = 2) -> Optional[Evidence]:
    """Detect declining team sentiment across standup and retro files."""
    from scraut.platform.llm.client import complete_json
    from scraut.platform.llm.prompts import SENTIMENT_SCORE

    root = get_workspace_root()
    sprint_num = get_current_sprint()
    sentiment_scores = []

    for s in range(max(1, sprint_num - 3), sprint_num + 1):
        sprint_dir = get_sprint_folder(s)
        if not sprint_dir.exists():
            continue

        # Sample recent standup files from this sprint
        texts = []
        standup_base = sprint_dir / "standup"
        if standup_base.exists():
            for date_dir in sorted(standup_base.iterdir())[-3:]:  # Last 3 days
                if not date_dir.is_dir():
                    continue
                for f in date_dir.glob("*.md"):
                    content = read_file(f)
                    if content:
                        texts.append(content[:500])

        retro_summary = read_file(get_sprint_output_folder(s) / "retrospective" / "summary.md")
        if retro_summary:
            texts.append(retro_summary[:800])

        if not texts:
            continue

        result = complete_json(
            SENTIMENT_SCORE.format(entries="\n---\n".join(texts[:5]))
        )
        if result and "score" in result:
            sentiment_scores.append({
                "sprint": s,
                "score": result["score"],
                "signals": result.get("signals", []),
                "concern_level": result.get("concern_level", "none"),
            })

    if len(sentiment_scores) < 2:
        return None

    # Check for declining trend
    declining = 0
    for i in range(1, len(sentiment_scores)):
        if sentiment_scores[i]["score"] < sentiment_scores[i-1]["score"]:
            declining += 1

    if declining < declining_threshold:
        return None

    instances = [{
        "sprint": s["sprint"],
        "date": f"sprint-{format_sprint_num(s["sprint"], get_folder_padding())}",
        "file": f"sprint-{format_sprint_num(s["sprint"], get_folder_padding())}/standup/summary",
        "author": "team",
        "text": f"Sprint {s['sprint']} sentiment score: {s['score']}/10 ({s['concern_level']} concern)",
        "quote": "; ".join(s.get("signals", [])[:2]),
    } for s in sentiment_scores]

    last_score = sentiment_scores[-1]["score"]
    first_score = sentiment_scores[0]["score"]
    return Evidence(
        detector_name="SentimentTrendDetector",
        pattern_description=(
            f"Team sentiment declining for {declining} consecutive sprints "
            f"({first_score}/10 → {last_score}/10)"
        ),
        instances=instances,
        estimated_impact="Declining morale correlates with increased sick days, turnover risk, and velocity loss",
        metrics_before={
            "sentiment_trend": [{"sprint": s["sprint"], "score": s["score"]}
                                 for s in sentiment_scores],
            "decline_from": first_score,
            "decline_to": last_score,
        },
        severity="high" if last_score <= 4 else "medium",
    )


def run_all_detectors(repo_name: str, config: dict) -> list[Evidence]:
    """Run all detectors and return list of triggered Evidence objects."""
    detectors = [
        ("BlockerFrequency", lambda: blocker_frequency_detector(config)),
        ("VelocityDrop", lambda: velocity_drop_detector(repo_name, config)),
        ("PRReviewLag", lambda: pr_review_lag_detector(repo_name, config)),
        ("CapacityImbalance", lambda: capacity_imbalance_detector(repo_name, config)),
        ("RetroFollowthrough", lambda: retro_followthrough_detector(config)),
        ("SentimentTrend", lambda: sentiment_trend_detector(config)),
    ]
    results = []
    for name, detector_fn in detectors:
        try:
            evidence = detector_fn()
            if evidence:
                logger.info(f"✓ {name}: pattern detected — {evidence.pattern_description}")
                results.append(evidence)
            else:
                logger.info(f"  {name}: no pattern")
        except Exception as e:
            logger.error(f"  {name}: error — {e}")
    return results
