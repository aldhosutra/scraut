---
sidebar_position: 1
---

# Morning Routine

Every weekday morning, Scraut kicks off a routine that prepares each team member for the day.

---

## The automated morning sequence

```
7:55 AM  → Morning notification workflow fires
           Sends each team member a personal Slack DM with their standup link

8:00 AM  → Repo sync workflow fires
           Pulls code activity from connected repos into standup context

9:00 AM  → Template reset workflow fires
           Creates standup template files for anyone who hasn't submitted yet
           (idempotent — won't overwrite existing files)

~9:30 AM → Standup summary workflow fires
           After everyone has pushed their standup files
           Summarises all submissions → posts to #scraut-bot
```

---

## Morning Slack DM

**Trigger:** Scheduled at `55 0 * * 1-5` (7:55 AM Jakarta / UTC+7)
**Workflow:** `morning-notification.yml`

Each team member with a `slack_id` configured receives a personal DM:

```
Good morning Alice! 🌅

It's standup time for Sprint 01.

📝 Your standup file:
   workspace/sprint/01/standup/2026-05-24/alice.md

Quick options:
• Run `scraut standup` to open it in GitHub
• Or edit it directly and push

Sprint 01 ends in 8 days. Current velocity: 18 sp/sprint avg.
```

:::info No Slack bot token?
Without `SLACK_BOT_TOKEN`, this DM step is skipped. The rest of the morning sequence (summary, template creation) still runs. Consider setting up Slack even if only for the channel posts — it significantly improves team adoption.
:::

---

## What to do each morning

### Option 1: Use the CLI (fastest)

```bash
scraut standup
```

This opens your standup file directly in GitHub's web editor for today's date. Edit and commit there.

### Option 2: Edit locally

```bash
# The file is already created — just open it
code workspace/sprint/01/standup/$(date +%Y-%m-%d)/$(git config user.name | tr ' ' '-' | tr '[:upper:]' '[:lower:]').md

# Edit, then commit
git add workspace/sprint/01/standup/
git commit -m "standup: $(date +%Y-%m-%d) [skip ci]"
git push
```

### Option 3: Via GitHub web UI

Click the link in your Slack DM → GitHub opens the file in the pencil editor → fill in → click **Commit changes**.

---

## Checking what your teammates are working on

Once the standup summary runs (typically by 9:30 AM), check:

- **Slack:** the `#scraut-bot` channel has the daily summary post
- **File:** `.scraut/sprint/01/standup/summary/2026-05-24.md`
- **CLI:** `scraut status` (shows current sprint health + recent blockers)

---

## Scenario: A typical Monday morning

**Who:** Alice (developer), Bob (developer), Charlie (scrum master)

**Timeline:**

| Time | What happens |
|------|-------------|
| 7:55 AM | All three get a Slack DM with their standup link |
| 8:00 AM | Alice opens the link, fills in Yesterday/Today/Blockers, commits |
| 8:15 AM | Bob runs `scraut standup`, fills in his file, commits |
| 8:30 AM | Charlie's internet is slow — he edits directly on GitHub from the DM link |
| 9:00 AM | Scraut standup summary workflow fires. All 3 files exist. |
| 9:05 AM | LLM reads all 3 standup files, generates a unified summary |
| 9:07 AM | Summary is committed to `.scraut/sprint/01/standup/summary/2026-05-27.md` |
| 9:08 AM | Summary is posted to `#scraut-bot` in Slack |
| 9:08 AM | Team sees: Alice is working on auth, Bob on API, Charlie flagged a blocker (waiting for design) |
| 9:09 AM | Charlie DMs the designer directly — blocker resolved without a meeting |

**Total ceremony time for the team: ~5 minutes each. No standup call needed.**
