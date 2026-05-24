---
sidebar_position: 3
---

# Autonomy Levels

Scraut offers three levels of agent autonomy. Choose based on your team's comfort with AI-driven automation.

---

## `supervised` (recommended to start)

```yaml
agents:
  autonomy_level: supervised
```

**How it works:**
- Agents propose sprint assignments → human SM approves before execution
- Agents implement tasks and open PRs → human review always required before merge
- Agents submit daily standups → human team reviews summaries
- Human checkpoint fires at every sprint boundary

**Best for:** Teams new to agent mode, high-stakes domains, regulated environments.

**What requires human action:**
- Approving the sprint plan each sprint
- Reviewing and merging every agent PR
- Resolving escalations

---

## `semi-auto`

```yaml
agents:
  autonomy_level: semi-auto
```

**How it works:**
- Agents claim issues and implement them without waiting for approval
- PRs still require human review before merge
- Human checkpoints only at sprint boundary and on escalation
- Agents can self-assign issues from the backlog based on specialty

**Best for:** Teams that have run supervised mode for 2+ sprints and trust the agents.

**What still requires human action:**
- Reviewing and merging every agent PR
- Sprint boundary approval
- Resolving escalations

---

## `full-auto`

```yaml
agents:
  autonomy_level: full-auto
```

**How it works:**
- Agents run continuously, claim issues, implement them, and request review
- Sprint planning happens automatically without waiting for SM input
- Humans receive weekly digests only
- Emergency checkpoints still fire (milestone slip, multiple escalations, repeated failures)

**Best for:** Very mature teams with well-defined acceptance criteria on every issue, and a high-trust relationship with the LLM provider.

:::warning Full-auto requires preparation
Full-auto mode is only effective when:
- Every backlog issue has clear, specific acceptance criteria
- CI is comprehensive and catches regressions reliably
- The `definition_of_done` in scraut.yml is strict
- The team reviews the weekly digest and acts on escalations promptly
:::

---

## Changing autonomy level

You can change the autonomy level between sprints. Edit `workspace/scraut.yml`:

```yaml
agents:
  autonomy_level: semi-auto  # was supervised
```

Commit and push. The change takes effect on the next orchestrator cycle.

---

## Comparison table

| | `supervised` | `semi-auto` | `full-auto` |
|--|--|--|--|
| Sprint plan approval | Human required | Human required | Automated |
| Issue claiming | Human approves | Automated | Automated |
| PR merge | Human required | Human required | Human required |
| Sprint boundary | Human checkpoint | Human checkpoint | Auto |
| Escalation response | Human required | Human required | Human required |
| Weekly digest | Yes | Yes | Yes |
| Suitable for | All teams | Teams with 2+ sprint history | Mature, high-trust teams |

---

## Recommended progression

1. **Sprints 1–2:** Run with agents **disabled** — establish your baseline velocity and processes
2. **Sprint 3:** Enable agents in **supervised** mode with 1 agent and 1 low-risk issue
3. **Sprint 5:** Expand to more agents if supervised mode is working well
4. **Sprint 8+:** Consider **semi-auto** if you're consistently happy with agent PRs
5. **Never rush to full-auto** — supervised and semi-auto deliver most of the value at lower risk
