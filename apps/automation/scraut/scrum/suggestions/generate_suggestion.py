"""
scrum/.scraut/suggestions/generate_suggestion.py
Given Evidence from a detector, use LLM to draft a Suggestion file.
Creates .scraut/suggestions/active/s[NNN]-[name].md and a GitHub Issue for team review.
"""
import json
import logging
import re
from pathlib import Path
from datetime import date
from typing import Optional
from scraut.platform.utils.config import load_config, get_workspace_root, get_scraut_root
from scraut.platform.utils.file_utils import atomic_write, read_file
from scraut.platform.llm.client import complete_json
from scraut.platform.llm.prompts import SUGGESTION_DRAFT, SYSTEM_SCRUM_ASSISTANT
from scraut.platform.github.api import get_github_client, create_issue, post_comment
from scraut.scrum.suggestions.detectors import Evidence

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
    scraut_root = get_scraut_root()
    all_suggestions = (
        list((scraut_root / "suggestions" / "active").glob("s*.md")) +
        list((scraut_root / "suggestions" / "implemented").glob("s*.md")) +
        list((scraut_root / "suggestions" / "resolved").glob("s*.md"))
    )
    if not all_suggestions:
        return "s001"
    ids = [int(re.match(r"s(\d+)", f.stem).group(1))
           for f in all_suggestions if re.match(r"s(\d+)", f.stem)]
    next_id = max(ids) + 1 if ids else 1
    return f"s{next_id:03d}"


def generate_suggestion(evidence: Evidence, repo_name: str,
                        config: dict) -> Optional[Path]:
    root = get_workspace_root()
    scraut_root = get_scraut_root()
    sprint_num = config["sprint"]["current_sprint"]
    measure_sprint = sprint_num + 2

    # Call LLM to draft the suggestion
    evidence_str = "\n".join(
        f"- Sprint {inst['sprint']} | {inst['date']} | {inst['file']} | "
        f"{inst.get('quote', inst.get('text', ''))}"
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
        f"| Sprint {i['sprint']} | {i['date']} | `{i['file'][-40:]}` | "
        f"{i.get('quote', i.get('text', ''))[:60]} |"
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

    # Write suggestion file to .scraut/suggestions/active/
    (scraut_root / "suggestions" / "active").mkdir(parents=True, exist_ok=True)
    file_path = scraut_root / "suggestions" / "active" / file_name
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
