> **This file is never read by Scraut.** It exists to show the milestone format.
> To track a real milestone, create a **subdirectory** with a `milestone.md` inside it.
> Example: `milestones/v1.0/milestone.md`
>
> Scraut reads `milestones/*/milestone.md` — any subdirectory name works.

---

# Milestone: v1.0

- Due: 2026-07-01
- Goal: Ship the MVP — core authentication, API v1, and the team dashboard
- GitHub milestone: https://github.com/myorg/my-repo/milestone/1

## Epics

- [ ] Epic: User Authentication — #45
- [ ] Epic: Dashboard MVP — #67
- [ ] Epic: Public API v1 — #89
- [ ] Epic: Documentation — #102

## Risks

- Third-party OAuth provider has had 3 outages this quarter — Mitigation: circuit breaker + fallback
- Two team members on PTO last 2 weeks of June — Mitigation: front-load risky work to June 1–14

## Definition of Done

- [ ] All committed issues closed or explicitly deferred with owner
- [ ] Load test passing: p95 < 200ms at 100 req/s
- [ ] Release notes drafted and reviewed by PM
- [ ] Stakeholders notified via email
- [ ] `CHANGELOG.md` updated
