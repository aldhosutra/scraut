---
sidebar_position: 4
---

# Human Checkpoints

Human checkpoints are automatic pause points built into agent mode. When a checkpoint triggers, agents stop working and wait for a human to review and resume. They are the safety net that keeps humans in control even in semi-auto and full-auto modes.

---

## Configured checkpoints

```yaml
agents:
  human_checkpoints:
    - event: sprint_boundary
    - event: milestone_eta_slip
    - event: escalation_count
    - event: agent_failure
```

---

## `sprint_boundary`

**Fires:** At the start of every new sprint
**What happens:** Agent orchestrator pauses. No new issues are claimed or started.
**Required action:** SM reviews the proposed sprint plan and triggers `sprint-planning` workflow manually.
**Resumption:** Orchestrator resumes automatically after sprint plan is merged.

This ensures humans approve the goal and scope of every sprint, even in full-auto mode.

---

## `milestone_eta_slip`

**Fires:** When a milestone forecast slips more than 1 sprint from the original target
**What happens:** Orchestrator pauses. Agents finish in-progress work but don't start new issues.
**Required action:** SM/PM reviews the milestone health file, adjusts scope or deadline.
**Resumption:** After SM commits an updated milestone file, orchestrator resumes.

This prevents agents from continuing to build features for a milestone that's already off-track without human awareness.

---

## `escalation_count`

**Fires:** When 2 or more agents are simultaneously marked `escalate:human`
**What happens:** Orchestrator pauses all agents.
**Required action:** SM resolves each escalation (clarifies requirements, unlocks dependencies).
**Resumption:** After all `escalate:human` labels are removed, orchestrator resumes automatically.

---

## `agent_failure`

**Fires:** When any agent workflow fails more than 3 times in a single day
**What happens:** That specific agent is paused (others continue).
**Required action:** SM investigates the agent workflow logs, identifies root cause.
**Resumption:** SM manually re-enables the agent workflow after the fix.

---

## Checkpoint notifications

When a checkpoint fires, Scraut:
1. Posts a Slack alert to `#scraut-bot` with the checkpoint type and reason
2. Applies `agent-blocked` label to any affected issues
3. Writes a checkpoint event to `.scraut/sprint/NN/code/checkpoint-log.md`

**Example Slack alert:**

```
🛑 Agent Checkpoint — sprint_boundary

Sprint 02 has started. Agents are paused until the sprint plan is approved.

Action required: Trigger the sprint-planning workflow from GitHub Actions UI.
Once the planning PR is merged, agents will resume automatically.
```

---

## Manual pause/resume

You can also pause and resume agents manually at any time:

**To pause:** In `workspace/scraut.yml`, set `agents.enabled: false` and commit. Orchestrator reads this at the next cycle.

**To resume:** Set `agents.enabled: true` and commit.

For finer control (pause one agent, not all), set `enabled: false` on the specific role.

---

## Viewing checkpoint history

```bash
cat .scraut/sprint/001/code/checkpoint-log.md
```

```markdown
<!-- BOT-GENERATED — Checkpoint Log — Sprint 01 -->

## Checkpoint Events

| Date | Event | Agents paused | Resolved by | Resolution time |
|------|-------|--------------|------------|----------------|
| 2026-05-25 | sprint_boundary | all | Charlie (merged planning PR) | 4h |
| 2026-06-01 | escalation_count | agent-backend, agent-frontend | Alice (clarified AC on #45, #51) | 2h |
```
