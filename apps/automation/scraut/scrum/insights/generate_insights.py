"""
scrum/.scraut/insights/generate_insights.py
Generate cross-sprint insight files:
  .scraut/insights/velocity-trends.md   — velocity history + trend line
  .scraut/insights/blocker-patterns.md  — most common blockers across sprints
  .scraut/insights/team-health.md       — sentiment + capacity trends

Run after each sprint closes or on monthly schedule.
These are read by: milestone health check, suggestion detectors,
the stakeholder portal, and the visibility engine.
"""
import json
import logging
from collections import Counter
from datetime import date
import re
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_current_sprint, get_sprint_folder, get_scraut_root, format_sprint_num, get_folder_padding
from scraut.platform.utils.file_utils import atomic_write, read_file, extract_section
from scraut.scrum.sprint.calculate_velocity import (calculate_sprint_velocity,
                                                calculate_rolling_velocity)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_velocity_trends(repo_name: str, config: dict) -> None:
    """Write .scraut/insights/velocity-trends.md with historical velocity data."""
    root = get_workspace_root()
    scraut_root = get_scraut_root()
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
            f"| Sprint {format_sprint_num(v['sprint'], get_folder_padding())} | {v['completed_sp']} sp {bar} | "
            f"{v['planned_sp']} sp | {round(v['completion_rate']*100)}% |\n"
        )

    content += (
        f"\n## Raw data (machine-readable)\n"
        f"```json\n{json.dumps({'rolling': rolling, 'history': velocity_history}, indent=2)}\n```\n"
    )
    atomic_write(scraut_root / "insights" / "velocity-trends.md", content)
    logger.info("velocity-trends.md updated")


def generate_blocker_patterns(config: dict) -> None:
    """Analyse standup files for recurring blockers. Write .scraut/insights/blocker-patterns.md."""
    root = get_workspace_root()
    scraut_root = get_scraut_root()
    sprint_num = get_current_sprint()
    all_blockers = []

    for s in range(1, sprint_num + 1):
        standup_base = get_sprint_folder(s) / "standup"
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

    word_counts = Counter()
    for b in all_blockers:
        words = re.findall(r'\b\w{4,}\b', b["text"].lower())
        word_counts.update(words)

    stopwords = {"that", "this", "with", "have", "been", "from", "they", "their",
                 "will", "when", "were", "would"}
    top_words = [(w, c) for w, c in word_counts.most_common(30) if w not in stopwords]

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

    atomic_write(scraut_root / "insights" / "blocker-patterns.md", content)
    logger.info("blocker-patterns.md updated")


def generate_team_health(config: dict) -> None:
    """Aggregate sentiment scores and write .scraut/insights/team-health.md."""
    root = get_workspace_root()
    scraut_root = get_scraut_root()
    sprint_num = get_current_sprint()
    health_data = []

    for s in range(1, sprint_num + 1):
        sprint_health_dir = get_sprint_folder(s)
        if not sprint_health_dir.exists():
            continue
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
        content += f"| Sprint {format_sprint_num(h['sprint'], get_folder_padding())} | {round(h['completion_rate']*100)}% | {icon} {h['status']} |\n"

    content += (
        f"\n## Notes\n"
        f"*For richer team health data, enable sentiment analysis in scraut.yml.*\n"
        f"*Sentiment scoring requires `llm.provider` to be configured.*\n"
    )
    atomic_write(scraut_root / "insights" / "team-health.md", content)
    logger.info("team-health.md updated")


def generate_all_insights(repo_name: str, config: dict) -> None:
    (get_scraut_root() / "insights").mkdir(exist_ok=True)
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
