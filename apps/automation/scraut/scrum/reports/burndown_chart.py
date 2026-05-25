"""
scrum/reports/burndown_chart.py
Generate a sprint burndown chart (PNG) from GitHub issue data.
Compares ideal burndown vs actual burndown.
"""
import argparse
import logging
from datetime import date, timedelta
from pathlib import Path
from scraut.platform.utils.config import load_config, get_workspace_root, get_current_sprint, get_sprint_folder, get_sprint_output_folder, format_sprint_num, get_folder_padding, get_scraut_root
from scraut.platform.utils.date_utils import is_working_day
from scraut.platform.github.api import get_github_client, get_issues, get_sp_from_issue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_burndown(sprint_num: int, repo_name: str, config: dict,
                      output_path: Path = None) -> Path:
    """Generate burndown chart PNG for the given sprint."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from scraut.platform.utils.date_utils import get_sprint_dates

    start, end = get_sprint_dates(sprint_num, config)

    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_label = f"sprint-{format_sprint_num(sprint_num, get_folder_padding())}"
    issues = get_issues(repo, labels=[sprint_label], state="all")

    total_sp = sum(get_sp_from_issue(i) for i in issues)
    if total_sp == 0:
        logger.warning("No story points found for sprint. Cannot generate burndown.")
        return None

    scraut_dir = get_scraut_root()
    working_days = []
    current = start
    while current <= end:
        if is_working_day(current, config, scraut_dir):
            working_days.append(current)
        current += timedelta(days=1)

    ideal_remaining = [total_sp * (1 - i / max(len(working_days) - 1, 1))
                       for i in range(len(working_days))]

    closed_by_date = {}
    for issue in issues:
        if issue.state == "closed" and issue.closed_at:
            close_date = issue.closed_at.date()
            sp = get_sp_from_issue(issue)
            closed_by_date[close_date] = closed_by_date.get(close_date, 0) + sp

    actual_remaining = []
    remaining = total_sp
    today = date.today()
    for d in working_days:
        if d > today:
            break
        remaining -= closed_by_date.get(d, 0)
        actual_remaining.append(remaining)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(working_days[:len(ideal_remaining)], ideal_remaining,
            "b--", label="Ideal", linewidth=1.5, alpha=0.6)
    if actual_remaining:
        ax.plot(working_days[:len(actual_remaining)], actual_remaining,
                "g-o", label="Actual", linewidth=2, markersize=4)

    ax.set_xlabel("Date")
    ax.set_ylabel("Story Points Remaining")
    ax.set_title(f"Sprint {format_sprint_num(sprint_num, get_folder_padding())} Burndown")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    plt.xticks(rotation=45)
    plt.tight_layout()

    if output_path is None:
        root = get_workspace_root()
        output_path = get_sprint_output_folder(sprint_num) / "review" / "burndown.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Burndown chart saved: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    parser.add_argument("--output")
    args = parser.parse_args()
    config = load_config(args.config)
    sprint_num = args.sprint or config["sprint"]["current_sprint"]
    output = Path(args.output) if args.output else None
    generate_burndown(sprint_num, args.repo, config, output)
