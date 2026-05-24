---
sidebar_position: 6
---

# GitHub Labels Reference

Scraut uses a specific set of GitHub labels for story points, type, priority, status, ceremony, agent state, and Definition of Done. These are created automatically by `scraut init` or `npx create-scraut` when `GITHUB_TOKEN` is set.

---

## Story point labels

Used for velocity tracking and sprint capacity planning.

| Label | Color | Description |
|-------|-------|-------------|
| `sp:1` | Blue | 1 story point |
| `sp:2` | Blue | 2 story points |
| `sp:3` | Blue | 3 story points |
| `sp:5` | Blue | 5 story points |
| `sp:8` | Blue | 8 story points |
| `sp:13` | Blue | 13 story points |

Story points follow the Fibonacci sequence. Use the `estimation` ceremony to vote on story points asynchronously.

---

## Issue type labels

Used for backlog categorisation and grooming.

| Label | Color | Description |
|-------|-------|-------------|
| `story` | Light blue | User story (feature, user-facing work) |
| `bug` | Red | Something isn't working |
| `task` | Yellow | Technical task (not user-facing) |
| `spike` | Orange | Research or investigation |
| `chore` | Light yellow | Maintenance, refactoring |

---

## Priority labels

Used for backlog ordering and sprint planning.

| Label | Color | Description |
|-------|-------|-------------|
| `p:high` | Dark red | Must be in next sprint |
| `p:medium` | Yellow | Target within 2 sprints |
| `p:low` | Green | Nice to have |

---

## Status labels

Applied automatically by Scraut workflows.

| Label | Color | Description | Applied by |
|-------|-------|-------------|-----------|
| `in-sprint` | Dark blue | Issue is committed in current sprint | Sprint plan merge |
| `in-review` | Purple | PR open for this issue | PR linker |
| `blocked` | Dark red | Blocked by dependency | Manual or agent |
| `escalate:human` | Crimson | Needs human intervention | Agent escalation |

---

## Ceremony labels

Applied during standup processing to link issues mentioned in standups.

| Label | Color | Description |
|-------|-------|-------------|
| `standup` | Light blue | Referenced in a standup |
| `retrospective` | Light blue | Discussed in a retrospective |
| `sprint-review` | Purple | Included in sprint review |
| `sprint-planning` | Salmon | Discussed in sprint planning |

---

## Agent labels

Applied by agent workflows.

| Label | Color | Description | Applied by |
|-------|-------|-------------|-----------|
| `agent-assigned` | Gold | Issue claimed by an AI agent | Agent orchestrator |
| `agent-blocked` | Orange | Agent is blocked on this issue | Agent workflow |

---

## Definition of Done labels

Applied after DoD check when sprint issues close.

| Label | Color | Description | Applied by |
|-------|-------|-------------|-----------|
| `dod:pending` | Light yellow | DoD check failed — needs attention | `dod-check.yml` |
| `dod:approved` | Green | DoD check passed | `dod-check.yml` |

---

## Milestone labels

Applied during milestone health monitoring.

| Label | Color | Description | Applied by |
|-------|-------|-------------|-----------|
| `milestone-risk` | Dark red | This issue's milestone is at risk | `milestone-planning.yml` |

---

## Creating labels manually

If you need to recreate labels after setup:

```bash
export GITHUB_TOKEN=your_personal_access_token
python apps/automation/scraut/platform/setup/create_labels.py --repo myorg/my-repo
```

Or use the GitHub CLI:
```bash
gh label create "sp:1" --color "0075ca" --description "1 story point" --repo myorg/my-repo
```

---

## Label conventions

- **One `sp:N` label per issue** — velocity calculation sums the value from the first matching label
- **One `p:*` label per issue** — for sprint planning prioritisation
- **One type label per issue** — (`story`, `bug`, `task`, `spike`, `chore`)
- **Multiple status labels allowed** — an issue can be both `in-sprint` and `blocked`
