---
sidebar_position: 4
---

# Adding Blockers

Blockers can be added to your standup file manually or via the `scraut blocker` command for a quick terminal shortcut.

---

## Via the CLI

```bash
scraut blocker "Waiting for API credentials from platform team — blocked on #28"
```

This command:
1. Finds today's standup file for your GitHub login
2. Replaces the `None` placeholder in `## Blockers` with your blocker text
3. Saves the file locally

Then you commit and push as usual:
```bash
git add workspace/sprint/01/standup/
git commit -m "standup: added blocker [skip ci]"
git push
```

---

## Via direct file edit

Open your standup file and fill in the `## Blockers` section:

```markdown
## Blockers
- Waiting on API credentials from the platform team (#28) — day 2
- Design review for the profile page is overdue (#31)
```

---

## How Scraut handles blockers

When the standup summary runs, Scraut:

1. **Detects** blocker entries (any non-"None" content under `## Blockers`)
2. **Highlights** them in the Slack summary with a `🚧` icon
3. **Flags** them to the Scrum Master via the summary post
4. **Tracks** blocker duration across multiple days — if the same blocker appears for 3+ consecutive days, the Suggestions system flags it as a pattern

---

## Scenario: Multi-day blocker triggers a suggestion

**Who:** Alice (developer), Bob (scrum master)

**Day 1:**
- Alice writes: `Waiting for AWS IAM permissions from DevOps`
- Summary is posted; Bob sees it but assumes it will resolve quickly

**Day 2:**
- Alice writes the same blocker again (copy from yesterday)
- Summary flags it again; Bob plans to follow up

**Day 3:**
- Same blocker for the third day in a row
- Summary posts the blocker with `(day 3)` annotation
- After the sprint review, **Suggestion Detection** sees this pattern across the sprint history
- A suggestion is written to `.scraut/suggestions/active/s003-repeated-external-blocker.md`:
  > "Alice has had the same external dependency blocker for 3+ days in Sprint 1. Consider: (1) pre-sprint dependency resolution checklist, (2) daily SM escalation policy for external blockers."

**Day 4 (resolved):**
- Alice writes `None` in Blockers — the blocker is gone
- The suggestion remains active until the SM implements or dismisses it

---

## Best practices for writing blockers

| Instead of | Write |
|------------|-------|
| `blocked` | `Waiting for design mockup for #23 — @sarah can you share the Figma?` |
| `PR not reviewed` | `PR #18 open for 2 days — needs review before I can continue #21` |
| `unclear requirements` | `Story #25 AC unclear — need SM to clarify what "export" means` |

The more specific you are, the more actionable the Slack summary becomes for your SM and teammates.

---

## Clearing a blocker

In your next standup, simply write `None` or remove the blocker entry. Scraut does not require explicit "resolved" notation — absence is treated as resolved.
