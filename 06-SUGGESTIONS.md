# Phase 6: Suggestion System
*Scraut Implementation — requires Phases 1–5 complete*

## Goal
Build the intelligence layer that reads all Scraut artifacts, detects recurring
patterns using 6 deterministic detectors, generates evidence-backed LLM suggestions,
manages the full suggestion lifecycle (proposed → accepted → implemented → measured
→ resolved), and closes the learning loop by measuring whether suggestions worked.

---

## Architecture

```
suggestion-detect.yml (runs after sprint-review.yml)
  ↓
scripts/suggestions/detectors.py  (all 6 detectors — pure scripts, no LLM)
  → BlockerFrequencyDetector
  → VelocityDropDetector
  → PRReviewLagDetector
  → CapacityImbalanceDetector
  → RetroFollowthroughDetector
  → SentimentTrendDetector
  ↓ (for each triggered detector)
scripts/suggestions/generate_suggestion.py  (LLM only here)
  → formats evidence into suggestion file
  → creates GitHub Issue for team review
  → writes suggestions/active/s[NNN]-name.md
  ↓
Team responds: /accept A | /modify [notes] | /decline [reason]
  (via GitHub Issue comment — same flow as milestone planning)
  ↓
suggestion-measure.yml (runs 2 sprints after implementation)
  ↓
scripts/suggestions/measure.py
  → re-runs the same detector
  → compares before/after metrics
  → marks resolved/re-opens if no improvement
```

---

## Suggestion File States

```
proposed   → team has not yet responded
accepted   → team accepted (moved to implemented/ after action taken)
modified   → team accepted with modifications
declined   → team declined (moved to resolved/ with reason)
implemented → action taken, measuring
measured   → 2-sprint check complete
resolved   → closed (improved ✅ or no-effect ❌)
```

---

## 1. `scripts/suggestions/detectors.py`

All 6 detectors. Pure Python — no LLM calls. Evidence only. LLM drafts the suggestion.

```python
"""
scripts/suggestions/detectors.py
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
from scripts.utils.config import load_config, get_repo_root, get_current_sprint
from scripts.utils.file_utils import read_file, extract_section
from scripts.github.api import get_github_client, get_sp_from_issue, get_issues
from scripts.sprint.calculate_velocity import calculate_sprint_velocity

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
    root = get_repo_root()
    sprint_num = get_current_sprint()
    all_blockers = []

    for s in range(max(1, sprint_num - 1), sprint_num + 1):
        standup_base = root / f"sprint-{s:02d}" / "standup"
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
        "pr review": ["review", "pr", "pull request", "waiting for review", "needs review"],
        "design approval": ["design", "mockup", "figma", "approval", "ux"],
        "external dependency": ["external", "third party", "vendor", "waiting on", "blocked by team"],
        "environment": ["environment", "staging", "deploy", "infra", "server", "database"],
        "unclear requirements": ["unclear", "requirements", "spec", "need more info", "waiting for clarification"],
        "testing": ["test", "qa", "bug", "regression", "failing"],
    }
    clusters = {k: [] for k in keyword_groups}

    for blocker in blockers:
        text_lower = blocker["text"].lower()
        matched = False
        for theme, keywords in keyword_groups.items():
            if any(kw in text_lower for kw in keywords):
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
    from scripts.sprint.calculate_velocity import (calculate_sprint_velocity,
                                                    calculate_rolling_velocity)
    sprint_num = get_current_sprint()
    if sprint_num < 3:
        return None

    baseline = calculate_rolling_velocity(repo_name, num_sprints=5)
    avg = baseline.get("avg", 0)
    if avg == 0:
        return None

    recent_drops = []
    for s in range(max(1, sprint_num - min_sprints), sprint_num):
        vel = calculate_sprint_velocity(s, repo_name)
        completed = vel.get("completed_sp", 0)
        if completed < avg * (1 - drop_threshold):
            drop_pct = round((avg - completed) / avg * 100)
            recent_drops.append({
                "sprint": s,
                "completed_sp": completed,
                "baseline_avg": avg,
                "drop_percent": drop_pct,
                "file": f"sprint-{s:02d}/meta.md",
                "text": f"Sprint {s}: {completed} sp completed vs {avg} sp avg ({drop_pct}% below average)",
                "date": f"sprint-{s:02d}",
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
    sprint_label = f"sprint-{sprint_num:02d}"
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

    sprint_label = f"sprint-{sprint_num:02d}"
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
            "file": f"sprint-{sprint_num:02d}/meta.md",
            "author": login,
            "text": f"{display_map.get(login, login)}: {sp} sp ({pct}% of team avg)",
            "quote": f"{display_map.get(login, login)} assigned {sp} sp vs {avg_load:.0f} avg",
        })
    for login, sp in underloaded:
        pct = round(sp / avg_load * 100)
        instances.append({
            "sprint": sprint_num, "date": date.today().isoformat(),
            "file": f"sprint-{sprint_num:02d}/meta.md",
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
    root = get_repo_root()
    sprint_num = get_current_sprint()
    missed_items = []

    for s in range(1, sprint_num):
        retro_summary = read_file(root / f"sprint-{s:02d}" / "retrospective" / "summary.md")
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
                future_meta = read_file(root / f"sprint-{future_s:02d}" / "meta.md")
                future_meta_lower = (future_meta or "").lower()
                if any(kw in future_meta_lower for kw in keywords):
                    appeared = True
                    break

            if not appeared and len(action) > 10:
                missed_items.append({
                    "sprint": s,
                    "date": f"sprint-{s:02d}",
                    "file": f"sprint-{s:02d}/retrospective/summary.md",
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
    from scripts.llm.client import complete_json
    from scripts.llm.prompts import SENTIMENT_SCORE

    root = get_repo_root()
    sprint_num = get_current_sprint()
    sentiment_scores = []

    for s in range(max(1, sprint_num - 3), sprint_num + 1):
        sprint_dir = root / f"sprint-{s:02d}"
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

        retro_summary = read_file(sprint_dir / "retrospective" / "summary.md")
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
        "date": f"sprint-{s['sprint']:02d}",
        "file": f"sprint-{s['sprint']:02d}/standup/summary",
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
```

---

## 2. `scripts/suggestions/generate_suggestion.py`

```python
"""
scripts/suggestions/generate_suggestion.py
Given Evidence from a detector, use LLM to draft a Suggestion file.
Creates suggestions/active/s[NNN]-[name].md and a GitHub Issue for team review.
"""
import json
import logging
import re
from pathlib import Path
from datetime import date
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import atomic_write, read_file
from scripts.llm.client import complete_json
from scripts.llm.prompts import SUGGESTION_DRAFT, SYSTEM_SCRUM_ASSISTANT
from scripts.github.api import get_github_client, create_issue, post_comment
from scripts.suggestions.detectors import Evidence

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUGGESTION_FILE_TEMPLATE = """<!-- scraut-suggestion id:{suggestion_id} detector:{detector} -->
# {suggestion_id}: {title}

**Status:** proposed
**Priority:** {priority}
**Category:** {category}
**Detected:** {detected_date}
**Detector:** {detector}
**Evidence count:** {evidence_count} instances across {sprints_count} sprints
**Est. impact:** {estimated_impact}

---

## Evidence trail
| Sprint | Date | File | Quote |
|--------|------|------|-------|
{evidence_table}

## Suggested actions

{options_md}

## Expected impact
{impact_md}

## How Scraut will measure (auto-scheduled Sprint {measure_sprint})
{measurement_criteria}

## Baseline metrics (captured at detection time)
```json
{baseline_json}
```

---
*Reply in comments: `/accept A` · `/accept B` · `/modify [notes]` · `/decline [reason]`*
*This issue is managed by Scraut. Issue #{github_issue_num} tracks team response.*
"""

REVIEW_ISSUE_TEMPLATE = """<!-- scraut-suggestion-review id:{suggestion_id} -->
## 📊 Scraut Improvement Suggestion: {title}

**Priority:** {priority} | **Detector:** {detector}

{why_flagged}

### Evidence ({evidence_count} instances)
{evidence_table}

### Suggested actions

{options_md}

**Expected impact:** {impact_summary}

---
*Reply with one of:*
- `/accept A` — implement Option A (recommended)
- `/accept B` — implement Option B
- `/modify [your notes]` — accept with modifications
- `/decline [reason]` — decline this suggestion

*Scraut will auto-measure effectiveness {measure_sprint} sprints after implementation.*
"""


def get_next_suggestion_id(root: Path) -> str:
    """Generate next sequential suggestion ID (s001, s002, ...)."""
    all_suggestions = (
        list((root / "suggestions" / "active").glob("s*.md")) +
        list((root / "suggestions" / "implemented").glob("s*.md")) +
        list((root / "suggestions" / "resolved").glob("s*.md"))
    )
    if not all_suggestions:
        return "s001"
    ids = [int(re.match(r"s(\d+)", f.stem).group(1))
           for f in all_suggestions if re.match(r"s(\d+)", f.stem)]
    next_id = max(ids) + 1 if ids else 1
    return f"s{next_id:03d}"


def generate_suggestion(evidence: Evidence, repo_name: str,
                        config: dict) -> Optional[Path]:
    root = get_repo_root()
    sprint_num = config["sprint"]["current_sprint"]
    measure_sprint = sprint_num + 2

    # Call LLM to draft the suggestion
    evidence_str = "\n".join(
        f"- Sprint {inst['sprint']} | {inst['date']} | {inst['file']} | {inst['quote']}"
        for inst in evidence.instances
    )
    prompt = SUGGESTION_DRAFT.format(
        detector_name=evidence.detector_name,
        evidence=evidence_str,
        estimated_impact=evidence.estimated_impact,
    )
    draft = complete_json(prompt, system=SYSTEM_SCRUM_ASSISTANT)

    if not draft:
        logger.warning("LLM draft failed. Using fallback template.")
        draft = {
            "title": evidence.pattern_description[:60],
            "why_flagged": evidence.pattern_description,
            "options": [
                {"label": "A", "description": "Investigate and address the root cause",
                 "expected_impact": "To be determined", "recommended": True}
            ],
            "measurement_criteria": ["Re-run detector — expect fewer occurrences"],
        }

    suggestion_id = get_next_suggestion_id(root)
    title = draft.get("title", evidence.pattern_description[:60])
    safe_name = re.sub(r"[^a-z0-9]+", "-", title.lower())[:40]
    file_name = f"{suggestion_id}-{safe_name}.md"

    # Format evidence table
    evidence_table = "\n".join(
        f"| Sprint {i['sprint']} | {i['date']} | `{i['file'][-40:]}` | {i['quote'][:60]} |"
        for i in evidence.instances[:6]
    )

    # Format options
    options_md_lines = []
    impact_md_lines = []
    options_issue_lines = []
    for opt in draft.get("options", []):
        rec_label = " **(Recommended)**" if opt.get("recommended") else ""
        options_md_lines.append(
            f"**Option {opt['label']}{rec_label}:** {opt['description']}\n"
        )
        impact_md_lines.append(
            f"- Option {opt['label']}: {opt.get('expected_impact', 'TBD')}"
        )
        options_issue_lines.append(
            f"**Option {opt['label']}{rec_label}:** {opt['description']}"
        )

    priority = ("High" if evidence.severity == "high"
                else "Medium" if evidence.severity == "medium" else "Low")
    category_map = {
        "BlockerFrequencyDetector": "Process",
        "VelocityDropDetector": "Capacity",
        "PRReviewLagDetector": "Process",
        "CapacityImbalanceDetector": "Capacity",
        "RetroFollowthroughDetector": "Process",
        "SentimentTrendDetector": "Team Health",
    }
    category = category_map.get(evidence.detector_name, "Process")

    # Create GitHub Issue for team review
    g = get_github_client()
    repo = g.get_repo(repo_name)
    issue_body = REVIEW_ISSUE_TEMPLATE.format(
        suggestion_id=suggestion_id,
        title=title,
        priority=priority,
        detector=evidence.detector_name,
        why_flagged=draft.get("why_flagged", evidence.pattern_description),
        evidence_count=len(evidence.instances),
        evidence_table=evidence_table,
        options_md="\n".join(options_issue_lines),
        impact_summary=evidence.estimated_impact,
        measure_sprint=measure_sprint,
    )
    issue = create_issue(
        repo,
        title=f"💡 Suggestion: {title}",
        body=issue_body,
        labels=["scraut-suggestion"],
    )

    # Write suggestion file to suggestions/active/
    (root / "suggestions" / "active").mkdir(parents=True, exist_ok=True)
    file_path = root / "suggestions" / "active" / file_name
    file_content = SUGGESTION_FILE_TEMPLATE.format(
        suggestion_id=suggestion_id,
        title=title,
        priority=priority,
        category=category,
        detected_date=date.today().isoformat(),
        detector=evidence.detector_name,
        evidence_count=len(evidence.instances),
        sprints_count=len(set(i["sprint"] for i in evidence.instances)),
        estimated_impact=evidence.estimated_impact,
        evidence_table=evidence_table,
        options_md="\n".join(options_md_lines),
        impact_md="\n".join(impact_md_lines),
        measure_sprint=measure_sprint,
        measurement_criteria="\n".join(
            f"- {c}" for c in draft.get("measurement_criteria", [])
        ),
        baseline_json=json.dumps(evidence.metrics_before, indent=2),
        github_issue_num=issue.number,
    )
    atomic_write(file_path, file_content)
    logger.info(f"Created suggestion {suggestion_id}: {title} (Issue #{issue.number})")
    return file_path
```

---

## 3. `scripts/suggestions/measure.py`

```python
"""
scripts/suggestions/measure.py
Run 2 sprints after a suggestion is implemented.
Re-runs the original detector. Compares before/after.
Marks suggestion resolved (improved) or re-opens (no effect).
"""
import json
import logging
import re
from pathlib import Path
from scripts.utils.config import load_config, get_repo_root
from scripts.utils.file_utils import read_file, atomic_write
from scripts.github.api import get_github_client, post_comment
from scripts.notifications.slack_post import post_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def measure_suggestion(suggestion_file: str, repo_name: str, config: dict) -> None:
    path = Path(suggestion_file)
    content = read_file(path)

    # Extract baseline metrics and detector name
    detector_match = re.search(r"\*\*Detector:\*\*\s+(\w+)", content)
    baseline_match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
    issue_match = re.search(r"Issue #(\d+)", content)

    if not detector_match or not baseline_match:
        logger.warning(f"Could not parse suggestion file: {suggestion_file}")
        return

    detector_name = detector_match.group(1)
    baseline = json.loads(baseline_match.group(1))
    issue_num = int(issue_match.group(1)) if issue_match else None

    # Re-run the appropriate detector
    from scripts.suggestions.detectors import (
        blocker_frequency_detector, velocity_drop_detector,
        pr_review_lag_detector, capacity_imbalance_detector,
        retro_followthrough_detector, sentiment_trend_detector,
    )
    detector_map = {
        "BlockerFrequencyDetector": lambda: blocker_frequency_detector(config),
        "VelocityDropDetector": lambda: velocity_drop_detector(repo_name, config),
        "PRReviewLagDetector": lambda: pr_review_lag_detector(repo_name, config),
        "CapacityImbalanceDetector": lambda: capacity_imbalance_detector(repo_name, config),
        "RetroFollowthroughDetector": lambda: retro_followthrough_detector(config),
        "SentimentTrendDetector": lambda: sentiment_trend_detector(config),
    }

    run_detector = detector_map.get(detector_name)
    if not run_detector:
        logger.error(f"Unknown detector: {detector_name}")
        return

    current_evidence = run_detector()
    improved = current_evidence is None  # Pattern no longer detected = improvement

    if not improved and current_evidence:
        # Check if metrics improved (even if pattern still present)
        current_count = len(current_evidence.instances)
        baseline_count = baseline.get("blocker_mentions",
                          baseline.get("prs_over_sla",
                          baseline.get("missed_action_items", 999)))
        improved = current_count < baseline_count * 0.6  # 40%+ improvement

    root = get_repo_root()
    suggestion_id = re.search(r"(s\d+)", path.stem).group(1)

    if improved:
        # Move to resolved/
        resolved_dir = root / "suggestions" / "resolved"
        resolved_dir.mkdir(exist_ok=True)
        result_note = (
            f"\n\n---\n## ✅ Measurement Result (Sprint +2)\n"
            f"Pattern no longer detected or significantly reduced.\n"
            f"**Outcome:** Improved\n"
            f"**Baseline:** {json.dumps(baseline, indent=2)}\n"
        )
        atomic_write(resolved_dir / path.name, content + result_note)
        path.unlink()
        outcome = "✅ improved"
    else:
        # Re-open as active
        active_dir = root / "suggestions" / "active"
        result_note = (
            f"\n\n---\n## ❌ Measurement Result (Sprint +2)\n"
            f"Pattern still present. Suggestion may need a different approach.\n"
            f"**Outcome:** No significant improvement\n"
        )
        current_content = content.replace("**Status:** implemented",
                                           "**Status:** proposed (re-opened)")
        atomic_write(active_dir / path.name, current_content + result_note)
        path.unlink()
        outcome = "❌ no improvement — re-opened"

    # Post result to GitHub Issue
    if issue_num:
        g = get_github_client()
        repo = g.get_repo(repo_name)
        issue = repo.get_issue(issue_num)
        post_comment(issue,
            f"## 📊 Measurement complete\n\n"
            f"**2-sprint post-implementation check:** {outcome}\n\n"
            f"Suggestion moved to `suggestions/{'resolved' if improved else 'active'}/`"
        )

    # Post to Slack
    webhook = config.get("notifications", {}).get("slack_webhook")
    if webhook:
        post_to_slack(webhook,
            f"📊 Suggestion {suggestion_id} measurement: {outcome}"
        )

    logger.info(f"Measurement complete for {suggestion_id}: {outcome}")
```

---

## 4. GitHub Actions Workflows

### `.github/workflows/suggestion-detect.yml`

```yaml
name: Scraut — Suggestion Detection
on:
  workflow_run:
    workflows: ["Scraut — Sprint Review"]
    types: [completed]
  workflow_dispatch:

jobs:
  detect-patterns:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Run pattern detectors and generate suggestions
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          python - << 'EOF'
          import sys
          sys.path.insert(0, '.')
          from scripts.utils.config import load_config
          from scripts.suggestions.detectors import run_all_detectors
          from scripts.suggestions.generate_suggestion import generate_suggestion
          import os

          config = load_config()
          repo = os.environ.get('GITHUB_REPOSITORY', '')
          evidences = run_all_detectors(repo, config)

          print(f"Detectors triggered: {len(evidences)}")
          for evidence in evidences:
              generate_suggestion(evidence, repo, config)
          EOF

      - name: Commit suggestion files
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add suggestions/
          git diff --staged --quiet || git commit -m "chore: new suggestions detected [skip ci]"
          git push
```

---

### `.github/workflows/suggestion-measure.yml`

```yaml
name: Scraut — Suggestion Measurement
on:
  schedule:
    - cron: '0 3 * * 1'  # Monday morning, after sprint reviews
  workflow_dispatch:

jobs:
  measure-suggestions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - run: pip install -r requirements.txt

      - name: Measure implemented suggestions
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          python - << 'EOF'
          import sys
          from pathlib import Path
          sys.path.insert(0, '.')
          from scripts.utils.config import load_config
          from scripts.suggestions.measure import measure_suggestion
          import os

          config = load_config()
          repo = os.environ.get('GITHUB_REPOSITORY', '')
          implemented_dir = Path('suggestions/implemented')

          if not implemented_dir.exists():
              print("No implemented suggestions to measure.")
          else:
              files = list(implemented_dir.glob('s*.md'))
              print(f"Measuring {len(files)} implemented suggestions")
              for f in files:
                  measure_suggestion(str(f), repo, config)
          EOF

      - name: Commit measurement results
        run: |
          git config user.email "scraut-bot@noreply.github.com"
          git config user.name "Scraut Bot"
          git add suggestions/
          git diff --staged --quiet || git commit -m "chore: suggestion measurements [skip ci]"
          git push
```

---

## Done Criteria for Phase 6

- [ ] `BlockerFrequencyDetector` — detects when same blocker theme appears ≥3 times across 2 sprints
- [ ] `VelocityDropDetector` — correctly detects >15% velocity drop vs rolling average
- [ ] `PRReviewLagDetector` — reads GitHub API for PR review wait times; triggers above SLA
- [ ] `CapacityImbalanceDetector` — detects >130% and <70% load against team median
- [ ] `RetroFollowthroughDetector` — detects action items that never appear in subsequent planning
- [ ] `SentimentTrendDetector` — uses LLM scoring (correctly calls LLM, not plain text)
- [ ] `run_all_detectors()` — runs all 6 detectors without crashing, returns list of Evidence
- [ ] `generate_suggestion()` — creates suggestion file in `suggestions/active/` with correct format
- [ ] `generate_suggestion()` — creates GitHub Issue with team review template and `/accept /decline` options
- [ ] `measure.py` — re-runs the original detector, determines if improved
- [ ] `measure.py` — moves to `resolved/` if improved, back to `active/` if not
- [ ] `measure.py` — posts result to original GitHub Issue
- [ ] `suggestion-detect.yml` — triggers after sprint review workflow
- [ ] `suggestion-measure.yml` — runs on Monday, processes all `suggestions/implemented/` files
- [ ] Test: manually create a test retro summary with action items, run `retro_followthrough_detector` — verify it detects the pattern

*Proceed to `07-AGENT-MODE.md`*
