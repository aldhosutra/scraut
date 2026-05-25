---
sidebar_position: 7
---

# Notifications

Scraut sends targeted Slack notifications at key moments — morning reminders, ceremony summaries, blocker alerts, and more. All notifications are opt-in and configurable.

---

## Morning standup reminder

**When:** Every weekday at 7:55 AM (your configured timezone)
**Channel:** Personal Slack DM (requires `SLACK_BOT_TOKEN` + `slack_id` per member)
**Config:** `notifications.morning_dm: true`

Each team member with a configured `slack_id` receives:

```
Good morning Alice! 🌅

Standup time for Sprint 01.
Your file: workspace/sprint/001/standup/2026-05-24/alice.md

Quick tip: run `scraut standup` to open directly in GitHub.

Sprint 01 ends in 8 days.
```

---

## Standup summary

**When:** 9:00 AM weekdays (after everyone has pushed their standup)
**Channel:** `#scraut-bot`

```
📋 Sprint 01 Standup — May 24, 2026

👤 Alice — OAuth integration in progress (#21). OOO Friday PM.
👤 Bob — Rate limiting PR open for review (#25). No blockers.
👤 Charlie — Updating sprint meta, reviewing velocity.

🚧 Blockers (1)
  • Alice: Waiting on design mockups for #31 (day 1)
    → Flagged to SM: Charlie

📈 Sprint health: 18/34 sp done (53%) — on track
```

---

## Sprint ceremony notifications

| Event | Slack message |
|-------|--------------|
| Sprint planning PR created | "🗓️ Sprint 2 planning PR ready for review — see #42" |
| Sprint planning merged | "🚀 Sprint 2 is GO! 26 sp committed across 6 issues" |
| Sprint review complete | "📊 Sprint 1 complete! 30/34 sp (88%). Review in .scraut/sprint/001/review/" |
| Retrospective synthesis done | "🔁 Sprint 1 retro synthesis ready — 3 themes, 4 action items" |
| Backlog grooming done | "🌿 Grooming complete — 5 issues labelled, 1 scope creep alert" |

---

## Alert notifications

| Event | Slack message |
|-------|--------------|
| DoD check failed | "⚠️ Issue #33 closed with DoD:pending — tests missing. SM alerted." |
| Milestone at risk | "⚠️ Milestone v2.0 at risk — forecast slipped to Sep 14 (target Aug 31)" |
| New suggestion | "💡 New suggestion: PR review cycle averaging 4 days. See .scraut/suggestions/active/" |
| Agent escalation | "🆘 Agent agent-backend is blocked on #45. Human review needed." |

---

## Weekly digest

**When:** Every Monday at 8:00 AM
**Channel:** `#scraut-bot` + email (if configured)
**Config:** `notifications.weekly_email: true`

See [Weekly Digest](./weekly-digest) for details.

---

## Configuring notifications

In `workspace/scraut.yml`:

```yaml
notifications:
  slack_webhook: ""      # Set via SLACK_WEBHOOK secret
  morning_dm: true       # Toggle morning standup DMs
  weekly_email: false    # Toggle Monday email digest
  stakeholder_emails:    # Email list for weekly digest
    - cto@company.com
    - pm@company.com
```

To disable a notification type, set it to `false`. The webhook is never committed to the file — use the `SLACK_WEBHOOK` GitHub Secret.

---

## GitHub Secrets required for notifications

| Notification | Secret needed |
|-------------|--------------|
| Channel posts (standup, ceremonies) | `SLACK_WEBHOOK` |
| Personal morning DMs | `SLACK_BOT_TOKEN` |
| Email digest | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` |

---

## Notification-free mode

If you don't configure Slack or email, all outputs still go to `.scraut/` files. The team can check summaries directly in the repository. Everything works — it's just less real-time.
