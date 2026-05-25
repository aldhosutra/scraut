> **This file is never read by Scraut.** It exists to show the format.
> The real file for mid-sprint ideas is `backlog-ideas.md` in this folder.
> Anyone on the team can append new ideas there at any time.

---

# Backlog Ideas — Sprint 001

<!-- Append new story ideas here mid-sprint.
     The grooming agent reads backlog-ideas.md to suggest priorities during grooming. -->

## User story ideas

- **Password reset via email**
  - As a user, I want to reset my password via email so that I can regain access if locked out.
  - Why: 5 support tickets this month about locked accounts
  - Rough size: sp:3

- **Bulk CSV export for admins**
  - As an admin, I want to export user data as CSV for compliance audits.
  - Why: Legal team request — needed before Q3 audit
  - Rough size: sp:5

## Bug reports worth tracking

- Login page crashes on Safari iOS 16 — reproducible, low priority but annoying
  - Seen in: #feedback channel, 2 users reported

## Technical debt ideas

- Refactor the auth module — currently has 3 different token formats in use
  - Blocks: adding OAuth providers cleanly
