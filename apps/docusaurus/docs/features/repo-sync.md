---
sidebar_position: 8
---

# Repo Sync

If your team works across multiple GitHub repositories (e.g., a separate backend API repo, a mobile repo, a shared library), Repo Sync pulls code activity from those connected repos and makes it available in each morning's standup context.

---

## When it runs

**When:** Every weekday at 8:00 AM (before standup templates are created)
**Workflow:** `repo-sync.yml`

---

## Configuring connected repos

In `workspace/scraut.yml`:

```yaml
repos:
  - name: Backend API
    url: myorg/backend-api    # org/repo format
    branch_filter: [main]     # only watch these branches
    enabled: true

  - name: Mobile App
    url: myorg/mobile-app
    branch_filter: [main, release]
    enabled: true
```

You also need the `SCRAUT_GITHUB_TOKEN` secret — a Personal Access Token with `repo:read` permission on the connected repositories.

---

## What gets synced

For each configured and enabled repo, Scraut fetches:

| Data | Source |
|------|--------|
| Recent commits (last 24h) | GitHub commits API |
| Merged PRs (last 24h) | GitHub PRs API |
| New issues opened | GitHub issues API |
| CI status | GitHub checks API |

---

## Where synced data goes

Synced activity is written to:
```
.scraut/sprint/NN/code/YYYY-MM-DD/[repo-name].md
```

**Example file** (`.scraut/sprint/01/code/2026-05-24/backend-api.md`):

```markdown
<!-- BOT-GENERATED — Repo Sync — backend-api — 2026-05-24 -->

# Code Activity — Backend API — 2026-05-24

## Commits (main branch)
- `a3f21bc` alice: Add rate limiting middleware (09:14)
- `b82e3d1` bob: Fix null pointer in parser (11:32)
- `c94f1e2` alice: Refactor auth token validation (14:15)

## Merged PRs
- PR #201: "Add rate limiting" — alice → main (merged 11:45)

## New issues
- #456: "API timeout on bulk requests" (opened by charlie)

## CI Status
- main: ✅ passing (last checked 14:30)
```

---

## How this helps daily standups

When team members write their standup each morning, the repo sync data is available for reference. The standup summary generation also reads from the code activity files, so the LLM can surface relevant cross-repo context:

```
📋 Sprint 01 Standup — May 24, 2026

...

📦 Cross-repo activity (via Repo Sync)
  Backend API: 3 commits, 1 merged PR (rate limiting — see .scraut/sprint/01/code/)
  Mobile App: no activity today
```

---

## Scenario: Identifying cross-team impact

**Characters:** Alice (frontend dev, Scraut repo), Bob (backend dev, backend-api repo)

1. **Bob** merges a breaking change to the API response format in `backend-api`
2. **Scraut's repo sync** fetches the commit at 8:00 AM
3. The commit summary includes: "Refactor API response envelope format"
4. **Alice's standup summary** mentions: "Note: backend-api had a breaking change yesterday (Bob: API envelope refactor)"
5. **Alice** sees this context in `#scraut-bot` before she starts coding
6. She immediately reaches out to Bob to understand the impact on her frontend code
7. **No surprises — no broken builds that would have been discovered hours later**

**Time saved: Potentially hours of debugging cross-repo breakage.**
