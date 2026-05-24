"""
scripts/visibility/generate_portal.py
Render the static HTML stakeholder portal from sprint data.
Writes bot-generated files to portal/ (atomic_write is safe here).
"""
import argparse
import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from scripts.utils.config import get_config, get_current_sprint, get_repo_root, load_config
from scripts.utils.date_utils import get_sprint_dates, days_until_sprint_end
from scripts.utils.file_utils import atomic_write, read_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_sprint_meta(sprint_num: int) -> str:
    return read_file(get_repo_root() / f"sprint-{sprint_num:02d}" / "meta.md")


def _load_standup_summary(sprint_num: int, today: str) -> str:
    return read_file(
        get_repo_root() / f"sprint-{sprint_num:02d}" / "standup" / "summary" / f"{today}.md"
    )


def _load_velocity_insight() -> Optional[float]:
    content = read_file(get_repo_root() / "insights" / "velocity-trends.md")
    if not content:
        return None
    m = re.search(r"velocity[:\s]+(\d+(?:\.\d+)?)", content, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _collect_data(config: dict) -> dict:
    sprint_num = get_current_sprint()
    today = date.today().isoformat()
    sprint_start, sprint_end = get_sprint_dates(sprint_num, config)
    days_left = days_until_sprint_end(sprint_end)

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "date": today,
        "sprint_num": sprint_num,
        "sprint_start": sprint_start.isoformat(),
        "sprint_end": sprint_end.isoformat(),
        "days_remaining": days_left,
        "sprint_meta": _load_sprint_meta(sprint_num),
        "standup_summary": _load_standup_summary(sprint_num, today),
        "velocity": _load_velocity_insight(),
        "portal_title": config.get("portal", {}).get("title", "Team Dashboard"),
        "refresh_minutes": config.get("portal", {}).get("refresh_minutes", 30),
    }


def _md_to_html(text: str) -> str:
    """Minimal markdown → safe HTML for inline portal display."""
    if not text:
        return ""
    # Strip bot-generated comment
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()
    lines = []
    for line in text.split("\n"):
        if line.startswith("## "):
            lines.append(f"<h3>{line[3:].strip()}</h3>")
        elif line.startswith("# "):
            lines.append(f"<h2>{line[2:].strip()}</h2>")
        elif line.startswith("- "):
            lines.append(f"<li>{line[2:].strip()}</li>")
        elif line.strip():
            lines.append(f"<p>{line.strip()}</p>")
    return "\n".join(lines)


def _render_html(data: dict) -> str:
    meta_html = _md_to_html(data["sprint_meta"]) or "<em>No sprint meta available yet.</em>"
    standup_html = _md_to_html(data["standup_summary"]) or "<em>No standup summary yet for today.</em>"
    velocity_str = f"{data['velocity']:.1f} sp/sprint" if data["velocity"] else "N/A"
    days_str = str(data["days_remaining"])
    ts = data["generated_at"][:19].replace("T", " ")

    return f"""<!DOCTYPE html>
<!-- BOT-GENERATED -->
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="{data['refresh_minutes'] * 60}">
  <title>{data['portal_title']}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h1>{data['portal_title']}</h1>
    <p class="subtitle">Sprint {data['sprint_num']} &middot; {data['sprint_start']} &rarr; {data['sprint_end']}</p>
    <p class="generated">Last updated: {ts} UTC</p>
  </header>

  <main>
    <div class="metrics-row">
      <div class="metric-card">
        <div class="metric-label">Days Remaining</div>
        <div class="metric-value">{days_str}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Team Velocity</div>
        <div class="metric-value">{velocity_str}</div>
      </div>
    </div>

    <section class="card" id="sprint-info">
      <h2>Sprint {data['sprint_num']} — Overview</h2>
      <div class="content">{meta_html}</div>
    </section>

    <section class="card" id="standup">
      <h2>Today&rsquo;s Standup Digest</h2>
      <div class="content">{standup_html}</div>
    </section>
  </main>

  <footer>
    <p>Powered by <a href="https://github.com/scraut/scraut">Scraut</a>
    &middot; auto-refreshes every {data['refresh_minutes']} min</p>
  </footer>
</body>
</html>
"""


def _render_css() -> str:
    return """/* BOT-GENERATED — Scraut stakeholder portal stylesheet */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, sans-serif;
  background: #f6f8fa;
  color: #24292f;
  line-height: 1.6;
  min-height: 100vh;
}

header {
  background: linear-gradient(135deg, #0969da 0%, #0550ae 100%);
  color: white;
  padding: 2.5rem 2rem 2rem;
  text-align: center;
}
header h1 { font-size: 2rem; font-weight: 700; margin-bottom: 0.4rem; }
.subtitle { font-size: 1rem; opacity: 0.88; }
.generated { font-size: 0.78rem; opacity: 0.7; margin-top: 0.5rem; }

main {
  max-width: 980px;
  margin: 2rem auto;
  padding: 0 1.25rem;
  display: grid;
  gap: 1.5rem;
}

.metrics-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.metric-card {
  background: white;
  border-radius: 10px;
  border: 1px solid #d0d7de;
  padding: 1.25rem 1.5rem;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.metric-label { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; color: #57606a; }
.metric-value { font-size: 2.2rem; font-weight: 700; color: #0969da; margin-top: 0.25rem; }

.card {
  background: white;
  border-radius: 10px;
  border: 1px solid #d0d7de;
  padding: 1.5rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.card h2 {
  font-size: 1rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #57606a;
  border-bottom: 1px solid #d0d7de;
  padding-bottom: 0.75rem;
  margin-bottom: 1rem;
}
.content h2, .content h3 { color: #0969da; margin: 1rem 0 0.5rem; font-size: 1rem; }
.content p { margin-bottom: 0.5rem; }
.content li { margin-left: 1.5rem; margin-bottom: 0.25rem; }
.content em { color: #57606a; }

footer {
  text-align: center;
  padding: 2rem;
  color: #57606a;
  font-size: 0.82rem;
}
footer a { color: #0969da; text-decoration: none; }
footer a:hover { text-decoration: underline; }

@media (max-width: 600px) {
  header h1 { font-size: 1.4rem; }
  .metric-value { font-size: 1.6rem; }
}
"""


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

    updated = form_template.replace(
        "teamMembers: [],    // Populated from scraut.yml via build step",
        f"teamMembers: {members_js},",
    )
    atomic_write(root / "portal" / "form.html", updated)
    logger.info("form.html populated with team members from scraut.yml")


def generate_portal(config: dict, dry_run: bool = False) -> None:
    data = _collect_data(config)
    root = get_repo_root()
    portal_dir = root / "portal"

    html = _render_html(data)
    css = _render_css()
    data_json = json.dumps(data, indent=2, default=str)

    if dry_run:
        logger.info("[DRY-RUN] Would write portal/index.html")
        logger.info("[DRY-RUN] Would write portal/style.css")
        logger.info("[DRY-RUN] Would write portal/data.json")
        logger.info(f"[DRY-RUN] sprint={data['sprint_num']}, date={data['date']}, days_remaining={data['days_remaining']}")
        return

    atomic_write(portal_dir / "index.html", html)
    atomic_write(portal_dir / "style.css", css)
    atomic_write(portal_dir / "data.json", data_json)
    generate_form_html(config)
    logger.info(f"Portal generated at {portal_dir} (sprint={data['sprint_num']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    generate_portal(config, dry_run=args.dry_run)
