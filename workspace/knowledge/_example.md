> **This folder is a free-form team knowledge base.** Files here are not read by Scraut automation.
> Create any `.md` files or subdirectories you find useful — architecture notes, runbooks,
> onboarding guides, API references, decision logs, etc.

---

# Knowledge Base

## What to put here

| File / Folder             | Contents                                              |
|---------------------------|-------------------------------------------------------|
| `architecture.md`         | System architecture overview, diagrams, data flows    |
| `runbooks/`               | Incident response procedures, on-call playbooks       |
| `onboarding.md`           | New team member setup guide                           |
| `api-reference.md`        | Internal API notes, auth flows, rate limits           |
| `decisions/`              | Lightweight ADRs that span multiple sprints           |
| `integrations.md`         | Third-party services, credentials location, rate limits |

## Tips

- Keep pages short — link out rather than copy-paste from external docs
- Date your entries so readers know how current the information is
- If a decision belongs to a specific sprint, put it in `sprint/NNN/decisions/` instead
- Files here are committed to the repo — avoid secrets; use GitHub Secrets for credentials
