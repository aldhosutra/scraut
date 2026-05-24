---
sidebar_position: 2
---

# Daily Standup

The standup is Scraut's core daily ceremony. Instead of a synchronous meeting, each team member writes a short Markdown file. The bot reads all files, generates a unified summary, and posts it to Slack — all automatically.

---

## The standup file

Each standup file follows a consistent template. It's created automatically each morning in:

```
workspace/sprint/NN/standup/YYYY-MM-DD/[your-github-login].md
```

**Template:**

```markdown
# Standup — Alice Smith
<!--
  Sprint: sprint-01
  Date: 2026-05-24
  Author: alice
  ...navigation links...
-->

## Yesterday
<!-- What did you complete? Reference issues/PRs where applicable. -->

## Today
<!-- What will you work on today? Reference issues if possible. -->

## Blockers
<!-- Anything blocking your progress? Write "None" if no blockers. -->
None

## Notes
<!-- Optional: OOO, reduced availability, context for the team -->
```

---

## Filling in your standup

Replace the placeholder comments with your actual update:

```markdown
# Standup — Alice Smith

## Yesterday
- Finished password reset flow (#14) — PR open for review
- Fixed the email validation regex (#17, merged)

## Today
- Start on the OAuth integration (#21)
- Review Bob's PR #18 (auth middleware refactor)

## Blockers
- Waiting on design mockups for the profile page (#23)
  — @designer can you share the Figma link?

## Notes
- OOO Friday afternoon
```

**Tips:**
- Reference issue numbers with `#NN` — Scraut links them in summaries
- Use specific details, not vague updates ("Worked on auth" → "Completed login form validation, tests pass")
- If blocked, name the person or dependency — Scraut escalates blockers to the SM

---

## Submitting your standup

Once you've filled in the file, commit and push:

```bash
git add workspace/sprint/01/standup/
git commit -m "standup: 2026-05-24 [skip ci]"
git push
```

The `[skip ci]` in the commit message prevents the standup summary from triggering again mid-day.

:::tip Shortcut
`scraut standup` opens the file directly in GitHub's web editor — no local clone needed.
:::

---

## What happens after you push

**Trigger:** `push` to `workspace/sprint/NN/standup/**`
**Workflow:** `daily-standup.yml` (also runs on cron at 9:00 AM)

```
push detected
  → generate_summary.py reads all standup files for today
  → collects: alice.md, bob.md, charlie.md
  → LLM prompt: "Summarise these standups. Highlight blockers and cross-dependencies."
  → LLM generates structured summary
  → atomic_write → .scraut/sprint/01/standup/summary/2026-05-24.md
  → git commit "[skip ci]"
  → post_to_slack → #scraut-bot
```

---

## The summary output

The summary posted to Slack looks like:

```
📋 Sprint 01 Standup Summary — May 24, 2026

👤 Alice — Working on OAuth integration (#21). Blocked: needs design mockups for #23.
👤 Bob — Finished auth middleware (#18), starting on API rate limiting (#25).
👤 Charlie — Reviewing sprint metrics, updating capacity.md.

🚧 Blockers (1)
  • Alice: Waiting on design mockups for profile page (#23)
    → Flagged to SM for follow-up

📈 Sprint health: 18 of 34 sp completed (53%) — on track.
```

And the full file `.scraut/sprint/01/standup/summary/2026-05-24.md` has more detail.

---

## Scenario: Alice is blocked, escalation happens

**Characters:** Alice (developer), Bob (scrum master)

**Steps:**

1. **Alice** opens her standup file (`scraut standup` or Slack DM link)
2. **Alice** writes in `## Blockers`: `Waiting for API credentials from the platform team — blocked on #28 for 2 days`
3. **Alice** commits and pushes
4. **Scraut** detects the word pattern `blocked` in the Blockers section
5. **Scraut** generates the summary and marks the blocker with a `🚧` flag
6. **Scraut** posts to `#scraut-bot` with the blocker highlighted
7. **Bob** (SM) sees the alert in Slack
8. **Bob** contacts the platform team directly and resolves it
9. **Next day**, Alice writes `None` in her Blockers section — blocker resolved

**Total time for escalation: ~2 minutes. No meeting needed.**

---

## What if you miss a day?

If you don't submit a standup by the time the cron fires (9:00 AM), your file simply won't be in that day's summary. The system won't error — it just summarises whoever submitted.

The template is created fresh each morning, so tomorrow you start clean.

---

## Standup for AI agents

When [Agent Mode](../agent-mode/overview) is enabled, AI agents also submit standups in the same format, in the same directory:

```
workspace/sprint/01/standup/2026-05-24/agent-backend.md
```

This means the team always has full visibility into what both humans and agents are working on, in one place.
