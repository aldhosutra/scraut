---
sidebar_position: 1
---

# Velocity Tracking

Scraut automatically calculates sprint velocity and maintains a rolling average, which feeds into sprint planning capacity estimates.

---

## Checking velocity

```bash
scraut velocity
# or for a specific sprint:
scraut velocity --sprint 3
```

**Example output:**

```
Sprint 03: 28 / 34 sp (82%)
Rolling average: 30 sp/sprint (σ=4, 3 sprints sampled)
```

| Value | Meaning |
|-------|---------|
| `28 / 34 sp` | 28 sp completed out of 34 planned |
| `(82%)` | Completion rate for this sprint |
| `Rolling average: 30` | Average sp completed across last N sprints |
| `σ=4` | Standard deviation — how consistent the team is |
| `3 sprints sampled` | Number of sprints used for the rolling average |

---

## How velocity is calculated

Velocity is calculated from **closed issues** in GitHub with story point labels (`sp:1` through `sp:13`) and the `in-sprint` label.

```python
# For each sprint:
completed_sp = sum(sp for issue in closed_issues if 'in-sprint' in issue.labels)
planned_sp = sum(sp for issue in all_sprint_issues)
completion_rate = completed_sp / planned_sp
```

The rolling average uses the most recent 5 sprints (or all available if fewer than 5).

---

## How velocity feeds sprint planning

When the sprint planning workflow runs, it uses:

```
available_capacity = rolling_velocity × capacity_buffer (default 0.85)
```

So if your rolling velocity is 34 sp and your buffer is 0.85:
```
planned sprint capacity = 34 × 0.85 = 29 sp
```

This prevents overcommitment — Scraut intentionally leaves 15% headroom for unplanned work.

---

## Velocity history over time

After each sprint review, the sprint velocity is appended to the review document. The Visibility Portal displays a velocity chart from this history.

To view the raw data:
```bash
ls .scraut/sprint/*/review/review.md | xargs grep "Sprint velocity:"
```

---

## Scenario: Team notices velocity declining

**After Sprint 3:**
```
Sprint 01: 30 sp
Sprint 02: 28 sp
Sprint 03: 22 sp  ← decline
Rolling average: 26 sp (σ=4)
```

The Suggestions system (after Sprint 4 if the trend continues) would detect the pattern:
> "Velocity has declined 3 sprints in a row. Possible causes: increasing story size, more blockers, or underestimation. Recommend: velocity retrospective discussion."

The SM gets a suggestion in `.scraut/suggestions/active/` and can investigate root causes.
