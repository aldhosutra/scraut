"""
scripts/sprint/calculate_velocity.py
Calculate velocity for a sprint: sum of sp labels on closed issues.
Also calculates rolling average velocity over last N sprints.
"""
import argparse
import logging
from scripts.utils.config import load_config
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_sprint_velocity(sprint_num: int, repo_name: str) -> dict:
    g = get_github_client()
    repo = g.get_repo(repo_name)
    sprint_label = f"sprint-{sprint_num:02d}"

    all_issues = get_issues(repo, labels=[sprint_label], state="all")
    closed = [i for i in all_issues if i.state == "closed"]
    open_issues = [i for i in all_issues if i.state == "open"]

    completed_sp = sum(get_sp_from_issue(i) for i in closed)
    planned_sp = sum(get_sp_from_issue(i) for i in all_issues)
    deferred_sp = sum(get_sp_from_issue(i) for i in open_issues)

    return {
        "sprint_num": sprint_num,
        "completed_sp": completed_sp,
        "planned_sp": planned_sp,
        "deferred_sp": deferred_sp,
        "completion_rate": round(completed_sp / planned_sp, 2) if planned_sp else 0,
        "issues_completed": len(closed),
        "issues_deferred": len(open_issues),
    }


def calculate_rolling_velocity(repo_name: str, num_sprints: int = 5) -> dict:
    """Calculate rolling average velocity over last N sprints."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    velocities = []

    for sprint_num in range(1, num_sprints + 1):
        sprint_label = f"sprint-{sprint_num:02d}"
        try:
            closed = get_issues(repo, labels=[sprint_label], state="closed")
            if not closed:
                continue
            sp = sum(get_sp_from_issue(i) for i in closed)
            velocities.append(sp)
        except Exception:
            continue

    if not velocities:
        return {"avg": 0, "min": 0, "max": 0, "std_dev": 0, "sprints_sampled": 0}

    import statistics
    return {
        "avg": round(sum(velocities) / len(velocities), 1),
        "min": min(velocities),
        "max": max(velocities),
        "std_dev": round(statistics.stdev(velocities), 1) if len(velocities) > 1 else 0,
        "sprints_sampled": len(velocities),
        "velocities": velocities,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    sprint_num = args.sprint or config["sprint"]["current_sprint"]
    result = calculate_sprint_velocity(sprint_num, args.repo)
    print(f"Sprint {sprint_num} velocity: {result['completed_sp']} sp")
    rolling = calculate_rolling_velocity(args.repo)
    print(f"Rolling avg: {rolling['avg']} sp/sprint (σ={rolling['std_dev']})")
