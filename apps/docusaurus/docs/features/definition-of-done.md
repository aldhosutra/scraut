---
sidebar_position: 3
---

# Definition of Done

When a sprint issue is closed in GitHub, Scraut automatically checks whether it meets your team's Definition of Done (DoD). If the criteria aren't met, the issue is flagged.

---

## Configuring your DoD

In `workspace/scraut.yml`:

```yaml
definition_of_done:
  - Tests written for new functionality
  - PR reviewed by at least one team member
  - Acceptance criteria mentioned in PR description
  - No open review comments
  - CI passing
```

Customise this list to match your team's standards. The LLM uses these criteria to evaluate each closed issue.

---

## How it works

**Trigger:** `issues: [closed]`
**Workflow:** `dod-check.yml`

Only sprint issues are checked (those with `sp:N` or `in-sprint` labels). Non-sprint issues are ignored.

```
Issue #21 closed
  │
  ├─ Check: is this a sprint issue? (has sp:N or in-sprint label?)
  │     Yes → proceed
  │     No  → skip
  │
  ├─ Fetch: linked PR(s) from issue description/comments
  │
  ├─ Evaluate each DoD criterion using LLM:
  │     "Tests written?" → check PR diff for test files
  │     "PR reviewed?" → check PR review status
  │     "AC in PR description?" → check PR body
  │     "No open comments?" → check review threads
  │     "CI passing?" → check commit status checks
  │
  ├─ If ALL criteria met:
  │     Apply label: dod:approved
  │     Post comment: "✅ Definition of Done: all criteria met"
  │
  └─ If ANY criterion NOT met:
        Apply label: dod:pending
        Post comment: "⚠️ DoD check: 1 criterion not met: [Tests written]"
        Notify SM via Slack
```

---

## DoD check comment

When an issue closes, Scraut posts a comment:

**All criteria met:**
```
✅ Definition of Done — Sprint 01

Criteria checked:
  ✓ Tests written for new functionality — 12 test files modified in PR #45
  ✓ PR reviewed by at least one team member — 2 approvals (bob, charlie)
  ✓ Acceptance criteria mentioned in PR description — AC listed in PR body
  ✓ No open review comments — 0 unresolved threads
  ✓ CI passing — all checks passed

Label applied: dod:approved
```

**Criteria not met:**
```
⚠️ Definition of Done — Sprint 01

Criteria checked:
  ✗ Tests written for new functionality — no test files changed in PR #46
  ✓ PR reviewed by at least one team member — 1 approval (alice)
  ✓ Acceptance criteria mentioned in PR description
  ✓ No open review comments
  ✓ CI passing

Label applied: dod:pending
Action: SM notified. Issue may need to be re-opened.
```

---

## Handling a DoD failure

When an issue gets `dod:pending`:

1. The SM receives a Slack alert
2. The SM decides: re-open the issue, or accept the exception with a note
3. If re-opened: the developer adds the missing tests, closes again — DoD re-runs
4. If accepted: SM adds a comment explaining the exception and manually applies `dod:approved`

---

## Scenario: Developer closes an issue too early

**Characters:** Bob (developer), Alice (SM)

1. **Bob** closes issue #33 (fix login redirect bug) after fixing the code, but without adding tests
2. Issue #33 has `sp:2` label → Scraut runs DoD check
3. LLM sees no test files changed in PR #50
4. Comment posted: "✗ Tests written — no test files changed"
5. `dod:pending` label applied
6. **Alice** (SM) gets Slack alert
7. **Alice** comments on the issue: "Bob, please add a regression test for this fix"
8. **Bob** adds `test_login_redirect.py`, pushes a new commit to PR #50, and re-closes the issue
9. DoD check runs again: all criteria met → `dod:approved`

**Result: A quality gate enforced automatically, without a code review process document that nobody reads.**
