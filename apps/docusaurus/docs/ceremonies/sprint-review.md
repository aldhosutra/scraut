---
sidebar_position: 2
---

# Sprint Review

The sprint review happens at the end of each sprint. The Scrum Master triggers it from GitHub Actions, and Scraut generates a comprehensive review document from the sprint's closed issues, velocity data, and standup summaries.

---

## Triggering the sprint review

1. Go to **Actions** → **Scraut — Sprint Review**
2. Click **Run workflow**
3. Fill in:
   - **Sprint number**: `1`
   - **org/repo**: `myorg/my-repo`
4. Click **Run workflow**

---

## What happens

```
SM triggers sprint-review
  │
  ├─ generate_review.py
  │     Fetches all issues closed this sprint (labeled in-sprint)
  │     Calculates: completed sp, planned sp, completion rate
  │     Reads all standup summaries from .scraut/sprint/001/standup/summary/
  │     Reads milestone health from .scraut/milestones/
  │     Calls LLM: "Generate a sprint review document from this data"
  │
  ├─ Writes .scraut/sprint/001/review/review.md  [BOT-GENERATED]
  │
  ├─ Updates workspace/scraut.yml current_sprint: 2  (increments sprint counter)
  │
  ├─ Posts summary to #scraut-bot in Slack
  │
  └─ Triggers: suggestion-detect.yml (pattern detection across sprint history)
```

---

## The review document

The generated review in `.scraut/sprint/001/review/review.md`:

```markdown
<!-- BOT-GENERATED — Sprint 01 Review — 2026-06-08 -->

# Sprint 01 Review

## Summary
- **Period:** 2026-05-26 → 2026-06-07 (10 working days)
- **Goal:** Deliver user authentication and basic dashboard
- **Goal met:** Yes ✓
- **Completed:** 30 of 34 story points (88%)
- **Issues closed:** 7 of 8

## Completed work
| Issue | Title | SP | Assignee | PR |
|-------|-------|----|---------|-----|
| #21 | OAuth integration | 5 | alice | #45 |
| #25 | API rate limiting | 3 | bob | #46 |
| #28 | Dashboard skeleton | 8 | charlie | #47 |
| #31 | Profile page | 5 | alice | #49 |
| #33 | Fix login redirect bug | 2 | bob | #50 |
| #35 | Write auth test suite | 3 | charlie | #51 |
| #42 | Fix typo in onboarding | 1 | alice | #52 |

## Deferred (not completed)
| Issue | Title | SP | Reason |
|-------|-------|----|--------|
| #38 | Performance optimisation | 3 | Blocked by infra team — carry to Sprint 2 |

## Velocity
- Sprint 01: 30 sp ← new
- Sprint 00: — (no history)
- Rolling average: 30 sp

## Highlights
- OAuth integration completed ahead of schedule — Alice paired with Bob to unblock #21
- Dashboard is functional but needs UX polish (noted for Sprint 2 grooming)

## Issues for next sprint
Deferred issues are automatically carried over to Sprint 2 backlog.
```

---

## Closing the sprint and deferred issues

Issues that were not completed are automatically deferred:
- `in-sprint` label is removed
- `deferred` label is added
- Issue is moved to the backlog for the next sprint planning

---

## Scenario: Sprint 1 review with one deferred story

**Characters:** Charlie (SM), Alice, Bob

**End of sprint day:**
1. **Charlie** triggers sprint-review for Sprint 1
2. Scraut fetches 7 closed issues (30 sp) and 1 open issue (#38, 3 sp, blocked by infra)
3. LLM generates the review document highlighting the infra blocker
4. Review is committed to `.scraut/sprint/001/review/review.md`
5. Slack post arrives in `#scraut-bot`:
   > Sprint 01 complete! 30/34 sp (88%) — Goal MET ✓. 1 issue deferred (#38 — infra blocker). Sprint 02 planning ready.
6. **suggestion-detect** workflow fires automatically — reads 1 sprint of history
7. Not enough data for suggestions yet (needs 3 sprints minimum by default)
8. **Sprint counter** in `workspace/scraut.yml` is incremented to `current_sprint: 2`
9. Next morning, team gets morning DMs for Sprint 2

**Total ceremony time: 0 minutes synchronous. The review document is ready in ~3 minutes.**
