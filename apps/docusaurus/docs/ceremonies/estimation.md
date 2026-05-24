---
sidebar_position: 5
---

# Estimation

Scraut supports async story point estimation using GitHub emoji reactions — no planning poker tool required.

---

## How it works

1. A team member comments on an issue with: `estimate this`
2. The **Estimation Tally** workflow fires
3. The issue gets a voting comment with emoji options
4. Team members react with the appropriate emoji
5. After the voting period, the workflow tallies votes and applies the winning `sp:N` label

---

## Triggering an estimation vote

### Option 1: Comment on the issue
On any GitHub issue, add a comment:
```
estimate this
```

### Option 2: Trigger from the Actions UI
1. Go to **Actions** → **Scraut — Estimation Tally**
2. Run workflow with the issue number

---

## The voting comment

Scraut posts a comment to the issue:

```
🗳️ Story Point Estimation

Vote using reactions on this comment:

👍 = 1 sp    ❤️ = 2 sp    😄 = 3 sp
🎉 = 5 sp    🚀 = 8 sp    👀 = 13 sp

Votes close when the SM applies a label manually,
or trigger `estimation-tally` again to tally current votes.
```

Team members react to the comment — one reaction per person.

---

## Tallying votes

When the SM is satisfied with participation, trigger the tally:

1. Go to **Actions** → **Scraut — Estimation Tally**
2. Fill in the **issue number**
3. Run workflow

Scraut counts the reactions, determines the winner (majority or median), and applies the `sp:N` label.

**Example tally:**
- 2 votes for `😄` (3 sp)
- 1 vote for `🎉` (5 sp)
- Result: `sp:3` label applied

---

## Scenario: Team estimates a new story async

**Characters:** Alice (dev), Bob (dev), Charlie (SM), and a new issue #52

**Steps:**

1. **Charlie** creates issue #52: "As a user, I can export my data as CSV"
2. **Charlie** comments: `estimate this`
3. Scraut posts the voting comment with emoji options
4. **Alice** sees the issue in her GitHub notifications, reacts with `😄` (3 sp)
5. **Bob** checks the issue during his coffee break, reacts with `🎉` (5 sp)
6. **Charlie** reacts with `😄` (3 sp)
7. After everyone votes, **Charlie** triggers the tally
8. 2 votes for 3 sp, 1 vote for 5 sp → `sp:3` label applied
9. Issue is ready for sprint planning

**Total time: ~5 minutes async per person. Zero meetings.**

---

## Tips for good async estimation

- **Vote independently** — react before reading others' reactions to avoid anchoring
- **Discuss outliers** — if votes are split 1 vs 8, drop a comment explaining your reasoning
- **Re-estimate after clarification** — if the story changes significantly, trigger a new vote
- **Use the LLM** — comment `what complexity is this?` and the bot will give its analysis before voting
