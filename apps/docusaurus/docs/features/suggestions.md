---
sidebar_position: 6
---

# Suggestions System

The Suggestions system is Scraut's continuous process improvement engine. After each sprint review, it analyses patterns across your sprint history and proposes targeted improvements to your team's workflow.

---

## How it works

**Trigger:** Automatically after sprint review completes (`workflow_run: sprint-review`)
**Workflow:** `suggestion-detect.yml` → `suggestion-measure.yml`

```
Sprint review completes
  │
  └─ suggestion-detect.yml fires
        │
        ├─ detectors.py
        │     Reads last N sprints of standup summaries
        │     Reads velocity history
        │     Reads blocker patterns from standup files
        │     Checks: recurring blockers, velocity trends, PR cycle times
        │     Applies pattern detection rules (deterministic — no LLM here)
        │
        ├─ For each detected pattern with ≥ 3 occurrences:
        │     Calls LLM: "Draft a process improvement suggestion for this pattern"
        │     LLM generates: title, evidence, proposed change, expected benefit
        │
        └─ Writes .scraut/suggestions/active/s00N-[slug].md  [BOT-GENERATED]
              Notifies SM via Slack
```

---

## Suggestion lifecycle

```
active/     → newly generated, awaiting SM review
implemented/ → SM has committed to trying this change
resolved/   → measured, outcome recorded
```

The SM moves suggestions between states by moving the file and editing it with the outcome.

---

## Example suggestion file

`.scraut/suggestions/active/s003-external-blockers.md`:

```markdown
<!-- BOT-GENERATED — Suggestion — Sprint 03 -->

# Suggestion: Proactive External Dependency Management

**Category:** Process
**Evidence strength:** 3 occurrences (Sprints 01, 02, 03)
**SM notified:** 2026-06-22

## Pattern detected
Alice has reported an unresolved external dependency blocker for 3+ days
in 3 consecutive sprints:
- Sprint 01: Waiting for AWS IAM permissions (3 days)
- Sprint 02: Waiting for API credentials (4 days)
- Sprint 03: Waiting for design mockups (2 days)

These blockers average 3.0 days unresolved before SM escalation.

## Proposed change
Add a "Dependency Register" step to sprint planning:
1. During planning, list all known external dependencies
2. Pre-contact dependency owners before sprint start
3. Add daily SM check for unresolved dependencies > 1 day

## Expected benefit
- Reduce average blocker duration from 3.0 days to < 1 day
- Improve sprint completion rate from 82% to ~90%

## Measurement plan
Scraut will measure: avg blocker duration in the next 2 sprints.
If avg < 1 day after implementation, suggestion will be marked as successful.
```

---

## Implementing a suggestion

When the SM decides to implement a suggestion:

1. Move the file: `active/s003-...md` → `implemented/s003-...md`
2. Add an "Implementation" section to the file:
   ```markdown
   ## Implementation
   - Date: 2026-06-25
   - Change made: Added "Dependency Register" section to sprint planning template
   - Owner: Charlie (SM)
   ```
3. Commit and push

After `measurement_sprints` (default: 2), the `suggestion-measure.yml` workflow runs automatically and checks if the metrics improved. It writes the outcome and moves the file to `resolved/`.

---

## Detection patterns

Scraut currently detects these patterns:

| Pattern | Trigger | Evidence needed |
|---------|---------|----------------|
| Recurring blockers | Same blocker type 3+ sprints | 3 occurrences |
| Velocity decline | Velocity drops 3 consecutive sprints | 3 sprints |
| Long PR review cycle | PRs open > 3 days avg | 3 sprints |
| Scope creep frequency | Mid-sprint additions > 2 issues/sprint | 3 sprints |
| Unmet DoD | DoD:pending rate > 20% | 3 sprints |
| Retro action item follow-through | Action items not appearing in next sprint | 2 sprints |

---

## Scenario: Suggestion leads to measurable improvement

**Characters:** Charlie (SM), 3-sprint history

**Detection (after Sprint 3 review):**
- Suggestion generated: "PR review cycle averages 4 days — recommend daily review slot"
- Charlie reads the suggestion, sees evidence: PRs from Sprints 1, 2, 3 averaged 4.2 days

**Implementation (Sprint 4 start):**
- Charlie adds a 15-minute daily review slot to the team calendar
- Moves suggestion to `implemented/`

**Measurement (after Sprint 5 and 6):**
- suggestion-measure.yml runs
- Sprint 4: avg PR review 2.1 days
- Sprint 5: avg PR review 1.8 days
- Scraut writes outcome: "PR review cycle improved from 4.2 days to 2.0 days (52% reduction)"
- Suggestion moved to `resolved/` as successful

**The improvement was driven by data, proposed automatically, and measured objectively.**
