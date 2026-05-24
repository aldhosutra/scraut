---
sidebar_position: 1
---

# Agent Mode Overview

Agent Mode is Scraut's fully autonomous AI development capability. When enabled, AI agents participate as team members — claiming issues, writing code, opening PRs, and submitting daily standups — alongside your human developers.

:::caution Beta feature
Agent Mode is powerful but requires careful configuration. Start with `autonomy_level: supervised` and a small number of low-risk issues before expanding agent autonomy.
:::

---

## What agents can do

| Capability | Description |
|-----------|-------------|
| Claim issues | Pick up stories from the backlog and move them through the sprint |
| Write code | Implement features, write tests, fix bugs |
| Open PRs | Submit work for human review |
| Submit standups | Write their own standup files each morning |
| Escalate | Apply `escalate:human` label when stuck |
| Report blockers | Flag dependencies or ambiguities in standups |

---

## What agents cannot do

| Action | Reason |
|--------|--------|
| Merge their own PRs | Human review always required |
| Approve sprint plans | Human checkpoint enforced at sprint boundary |
| Commit to `workspace/` human files | Agents only write their standup/retro in the correct format |
| Run destructively without human approval | Escalation always surfaces to a human first |

---

## Agent architecture

```
agent-orchestrator (every 4 hours, weekdays)
  │
  ├─ Reads workspace/scraut.yml — is agents.enabled = true?
  │     No → exits
  │
  ├─ For each enabled agent role:
  │     Runs the agent's workflow:
  │       agent-backend.yml
  │       agent-frontend.yml
  │       agent-test.yml
  │       agent-review.yml
  │
  └─ Each agent workflow:
        Claims an appropriate issue
        Works on it (writes code, opens PR)
        Submits standup
        Escalates if blocked
```

---

## Enabling agents

In `workspace/scraut.yml`:

```yaml
agents:
  enabled: true   # ← turn on agent mode

  roles:
    - id: agent-backend
      type: specialist
      specialty: backend
      enabled: true   # ← enable specific agents
      github_workflow: .github/workflows/agent-backend.yml
      description: "Implements backend/API tasks"

  autonomy_level: supervised  # supervised | semi-auto | full-auto

  human_checkpoints:
    - event: sprint_boundary   # Pause at start of every sprint
    - event: milestone_eta_slip # Pause if milestone forecast slips
    - event: escalation_count  # Pause if ≥2 agents blocked simultaneously
    - event: agent_failure     # Pause if an agent fails repeatedly
```

---

## Agent standup files

Each agent submits a daily standup at the same path as a human team member:

```
workspace/sprint/01/standup/2026-05-24/agent-backend.md
```

**Example agent standup:**

```markdown
# Standup — Agent Backend

## Yesterday
- Implemented rate limiting middleware (#25) — PR #46 open for review
- Fixed null pointer in parser (#33) — merged via PR #50

## Today
- Starting OAuth integration (#21) — backend API portion
- Will review any comments on PR #46 if they arrive

## Blockers
None

## Notes
- Operating in supervised mode
- 2 tasks completed this sprint, 0 blocked
- CI: all checks passing
```

This means the team sees agent activity in the same Slack standup summary as human activity — full transparency.

---

## Scenario: Agent handles a task while the human team focuses elsewhere

**Characters:** Alice (developer), agent-backend, Charlie (SM)

**Sprint setup:**
- 34 sp of work, 3 humans + 1 agent
- agent-backend assigned: `sp:3 task` — "Add database index to exports table" (#71)

**Day 1:**
1. agent-backend claims issue #71 (applies `agent-assigned` label)
2. Reads the issue description and acceptance criteria
3. Writes migration script, adds tests, opens PR #72
4. Standup: "Yesterday: — / Today: Started #71, migration complete, tests added. PR #72 open."

**Day 2 (after human review):**
1. Alice reviews PR #72 — leaves 2 comments: "Add a rollback migration" and "Index name too long"
2. agent-backend reads review comments
3. Addresses both comments, pushes updates
4. PR approved and merged by Alice

**End of sprint:**
- Issue #71 closed, DoD check passes
- Agent contributed 3 sp — tracked in velocity like any team member

**Time invested by Alice: ~20 minutes for PR review. The implementation was fully automated.**
