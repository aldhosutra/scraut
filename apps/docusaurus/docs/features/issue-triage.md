---
sidebar_position: 4
---

# Issue Triage & PR Linking

Two automatic workflows fire whenever issues and pull requests are created, keeping your backlog organised without manual labelling effort.

---

## Issue Triage

**Trigger:** `issues: [opened]`
**Workflow:** `issue-triage.yml`

When anyone creates a new issue, Scraut reads the title and description and suggests appropriate labels.

### What it does

```
New issue #52 opened: "Export button broken on Firefox 124"
  │
  ├─ Calls LLM with issue title + body:
  │     "Classify this issue: type (story/bug/task/spike/chore) + priority (high/medium/low)"
  │
  ├─ LLM responds: type=bug, priority=high
  │
  ├─ Applies labels: bug, p:high
  │
  └─ Posts comment:
        "🏷️ Auto-triaged: bug, p:high
         Reason: Issue describes a broken UI element (export button) affecting Firefox users.
         Please add story points when estimated. Override labels if needed."
```

### The triage comment

```
🏷️ Scraut Auto-Triage

**Type:** bug
**Priority:** p:high
**Suggested story points:** sp:2 (based on similar bug fixes)

Reasoning: This issue describes a broken UI element (export button) affecting all Firefox users.
The reproduction steps are clear and the fix scope appears limited.

Labels applied. Override manually if needed.
```

---

## PR Linking & Auto-Description

**Trigger:** `pull_request: [opened, edited]`
**Workflow:** `pr-linker.yml`

When a PR is opened, Scraut checks for linked issues (via `Closes #N`, `Fixes #N`, or `Resolves #N` in the PR body) and enriches the PR description.

### What it does

```
PR #50 opened: "Fix login redirect bug"
  │
  ├─ Parses PR body for: Closes #33, Fixes #, Resolves #
  │     Found: Closes #33
  │
  ├─ Fetches issue #33: title, description, acceptance criteria
  │
  ├─ Calls LLM: "Generate a PR description from the linked issue and PR diff summary"
  │
  └─ Updates PR body with:
        - Summary of changes (from diff)
        - Acceptance criteria (from issue)
        - Testing instructions
        - Screenshots section (if applicable)
```

### Auto-generated PR description

```markdown
## Summary
Fixes the login redirect bug where users were sent to the dashboard instead of
the originally requested page after login (#33).

## Changes
- `auth/middleware.py`: Store the `next` URL in session before redirect
- `auth/views.py`: Read `next` URL from session after successful login
- `tests/test_auth.py`: Added regression test for redirect behaviour

## Acceptance Criteria (from #33)
- [x] After login, user is redirected to the page they originally requested
- [x] Falls back to dashboard if no redirect URL is stored
- [x] Works for both OAuth and password login flows

## Testing
1. Navigate to `/settings` while logged out
2. Log in via the login page
3. Verify you land on `/settings`, not `/dashboard`

## Notes
Minor change — no migration needed. CI should be green.

Closes #33
```

---

## Scenario: New issue from a customer complaint

**Characters:** Alice (PO), Scraut bot, Bob (developer)

1. **Alice** creates issue #52: "Export button broken on Firefox 124" with steps to reproduce
2. **Scraut** reads the issue → applies `bug`, `p:high` labels within seconds
3. **Alice** sees the triage comment — labels match her expectation, she leaves them
4. **Bob** picks up the issue during grooming, estimates it at `sp:2`
5. **Bob** creates PR #68 with body: `Closes #52`
6. **Scraut** reads the issue, pulls the AC from #52, generates a full PR description
7. **Bob** sees the description is already filled in — just needs to check the AC boxes
8. **Alice** reviews PR #68 — the AC checkboxes make it easy to verify

**What Alice and Bob saved: ~15 minutes of writing labels and PR descriptions per issue/PR.**
