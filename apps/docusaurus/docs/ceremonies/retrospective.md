---
sidebar_position: 3
---

# Sprint Retrospective

The retrospective is the team's reflective ceremony. Each member writes their personal retro file, then the Scrum Master triggers a synthesis that produces a unified retrospective document with themes, patterns, and action items.

---

## Step 1: Each team member fills in their retro file

The retro template is created at:
```
workspace/sprint/NN/retrospective/[login].md
```

**Template:**

```markdown
# Retro — Alice Smith — Sprint 01

## Went well
<!-- What went well this sprint? Be specific. -->

## Could improve
<!-- What would you change? Focus on process, not people. -->

## Action items I'll own
<!-- Personal commitments for next sprint. -->
```

**Example filled-in:**

```markdown
# Retro — Alice Smith — Sprint 01

## Went well
- Pairing with Bob on the OAuth integration was really effective
- PR reviews happened same-day for most of the sprint
- Standup async format saved a lot of context-switching

## Could improve
- The infra blocker on #38 sat unresolved for 3 days before Charlie escalated
  — we need a clearer escalation policy
- Story #31 had unclear acceptance criteria — required 3 rounds of clarification

## Action items I'll own
- Draft an external dependency escalation policy doc
- Next sprint: write AC before creating stories, not after
```

Each team member commits their file:

```bash
git add workspace/sprint/01/retrospective/
git commit -m "retro: sprint 01 [skip ci]"
git push
```

---

## Step 2: Trigger retrospective synthesis (Scrum Master)

Once all retro files are pushed:

1. Go to **Actions** → **Scraut — Sprint Retrospective**
2. Click **Run workflow**
3. Fill in: **Sprint number**: `1`
4. Click **Run workflow**

---

## What happens

```
SM triggers sprint-retrospective
  │
  ├─ synthesise_retrospective.py
  │     Reads all workspace/sprint/01/retrospective/*.md files
  │     Extracts "Went well", "Could improve", "Action items" sections
  │     Calls LLM: "Identify themes across these individual retros"
  │     LLM groups insights by theme, surfaces common patterns
  │
  ├─ Writes .scraut/sprint/01/review/retro-synthesis.md  [BOT-GENERATED]
  │
  └─ Posts synthesis to #scraut-bot
```

---

## The synthesis document

`.scraut/sprint/01/review/retro-synthesis.md`:

```markdown
<!-- BOT-GENERATED — Sprint 01 Retrospective Synthesis -->

# Sprint 01 Retrospective — Team Synthesis

## What went well (3 contributors, 6 items)

**Collaboration (mentioned by 2/3):**
- Alice + Bob pairing on OAuth was effective
- PR reviews averaged 1 day turnaround

**Process (mentioned by 3/3):**
- Async standup format reduced context-switching
- Sprint goal was clear and well-understood

## Could improve (3 contributors, 7 items)

**Blocker escalation (mentioned by 2/3):**
- External dependency on infra sat unresolved for 3 days before escalation
- No clear policy for when to escalate vs wait

**Story quality (mentioned by 3/3):**
- Acceptance criteria written after story creation caused rework
- Two stories (#31, #37) needed 3+ rounds of clarification

## Action items proposed by the team

| Owner | Action item |
|-------|------------|
| Alice | Draft external dependency escalation policy |
| Bob | Run an AC-writing workshop before Sprint 2 planning |
| Charlie (SM) | Add "AC complete" as a sprint planning gate |

## Suggested process changes
Based on team input, Scraut recommends adding these as Suggestions (see .scraut/suggestions/):
1. Pre-sprint AC review step in planning checklist
2. External dependency register reviewed at each standup
```

---

## Scenario: 3-person retro with divergent views

**Characters:** Alice (feature dev), Bob (backend dev), Charlie (SM)

**Retros submitted:**
- **Alice**: Praises pairing, frustrated by unclear AC
- **Bob**: Likes async standups, concerned about merge conflicts on shared files
- **Charlie**: Happy with sprint velocity, worried about the infra blocker pattern

**Synthesis:**
- LLM identifies "AC clarity" as the highest-frequency theme (mentioned by Alice and Charlie)
- LLM surfaces "external dependencies" as a recurring risk (Alice and Charlie)
- Bob's merge conflict concern is noted but not a group theme
- Synthesis recommends 2 action items with clear owners

**Time investment:**
- Each team member: ~10 minutes writing their retro file
- SM: 2 clicks to trigger synthesis
- Synthesis is ready in ~2 minutes
- No synchronous retro meeting needed (though you can hold one using the synthesis as discussion material)
