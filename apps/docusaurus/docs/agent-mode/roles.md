---
sidebar_position: 2
---

# Agent Roles

Scraut has five built-in agent roles. Each is a separate GitHub Actions workflow with a distinct specialty. You enable only the agents your team needs.

---

## Available roles

### agent-orchestrator

**File:** `.github/workflows/agent-orchestrator.yml`
**Specialty:** Sprint orchestration and task distribution

The orchestrator reads the current sprint plan, identifies unassigned issues, and dispatches them to appropriate specialist agents based on the issue type and specialty match.

```yaml
roles:
  - id: agent-orchestrator
    type: orchestrator
    enabled: true
    description: "Plans sprints, assigns tasks to specialist agents"
```

The orchestrator runs every 4 hours on weekdays and checks:
1. Are there unassigned `in-sprint` issues?
2. Which specialist agents are available (not currently blocked)?
3. Does the issue type match the agent's specialty?

---

### agent-backend

**File:** `.github/workflows/agent-backend.yml`
**Specialty:** Backend, API, database, server-side logic

Claims issues labelled as backend tasks: API endpoints, database migrations, performance work, server-side bug fixes.

```yaml
  - id: agent-backend
    type: specialist
    specialty: backend
    enabled: true
    github_workflow: .github/workflows/agent-backend.yml
    description: "Implements backend/API tasks"
```

**Issue types it handles:** `task` or `story` with backend context, `bug` with server-side symptoms

---

### agent-frontend

**File:** `.github/workflows/agent-frontend.yml`
**Specialty:** UI, components, CSS, user-facing features

Claims issues related to frontend work: React components, styling, accessibility, client-side bug fixes.

```yaml
  - id: agent-frontend
    type: specialist
    specialty: frontend
    enabled: true
    github_workflow: .github/workflows/agent-frontend.yml
    description: "Implements UI/frontend tasks"
```

---

### agent-test

**File:** `.github/workflows/agent-test.yml`
**Specialty:** Testing, quality assurance

Writes tests for completed features, validates DoD criteria, improves test coverage. Can claim issues specifically about testing, or be dispatched to write tests for any recently merged PR.

```yaml
  - id: agent-test
    type: specialist
    specialty: testing
    enabled: true
    github_workflow: .github/workflows/agent-test.yml
    description: "Reviews PRs, writes tests, validates DoD"
```

---

### agent-review

**File:** `.github/workflows/agent-review.yml`
**Specialty:** Code review

Reviews open PRs and leaves structured feedback: code quality, test coverage, security concerns, performance, adherence to patterns. Does not merge — only reviews.

```yaml
  - id: agent-review
    type: specialist
    specialty: review
    enabled: true
    github_workflow: .github/workflows/agent-review.yml
    description: "Reviews PRs, leaves structured feedback"
```

**Typical review comment:**

```markdown
## Agent Review — agent-review

**Summary:** This PR implements rate limiting. Overall approach is sound.

**Feedback:**
1. **Security** ⚠️ — The rate limit key uses only IP address. Consider adding user ID for authenticated endpoints to prevent shared-IP false positives.
2. **Tests** ✓ — Good coverage. Consider adding a test for the 429 response body format.
3. **Performance** ✓ — Redis-based counter is the right choice here.
4. **Patterns** ✓ — Follows existing middleware structure.

**Recommendation:** Approve after addressing item 1. Optional improvements noted in items 2-4.
```

---

## Enabling multiple agents

You can enable multiple agents simultaneously. The orchestrator handles dispatch:

```yaml
agents:
  enabled: true
  roles:
    - id: agent-orchestrator
      type: orchestrator
      enabled: true
    - id: agent-backend
      type: specialist
      specialty: backend
      enabled: true
    - id: agent-review
      type: specialist
      specialty: review
      enabled: true
    # agent-frontend and agent-test disabled (team prefers to handle these)
```

---

## Escalation: `escalate:human`

Any agent that gets stuck (unclear requirements, failing CI that it can't fix, dependency on human decision) applies the `escalate:human` label to its issue and writes in its standup:

```markdown
## Blockers
Issue #45: requirements are ambiguous — AC says "support all export formats"
but doesn't specify which formats. Needs human clarification before proceeding.
Escalation label applied.
```

The SM is notified via Slack. Once the human resolves the ambiguity, they remove the `escalate:human` label and the agent resumes on the next orchestrator cycle.
