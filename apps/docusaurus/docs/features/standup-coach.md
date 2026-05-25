---
sidebar_position: 11
---

# Standup Coach

The Standup Coach is an opt-in daily assistant that detects when a team member's standup `Today` section is light on specifics — no issue references, no concrete tasks — and sends them a **private Slack DM** with personalised task recommendations. Nothing is posted to the team channel.

It is disabled by default. The SM turns it on when the team is ready.

---

## How it works

**Trigger:** Runs as a step in `daily-standup.yml`, after the team summary is generated
**Workflow:** `daily-standup.yml` (coach step)

```
Daily standup summary generated
  │
  └─ coach.py runs
        │
        ├─ For each team member who submitted a standup:
        │     is_today_vague()?
        │       — Under min_today_words (default: 20)?
        │       — No #NN issue reference?
        │       — No exempt phrase (code review, OOO, ceremony, etc.)?
        │
        ├─ Flagged members only:
        │     Fetch their open sprint issues from GitHub
        │     Read sprint goal from sprint/NNN/meta.md
        │     Read OKRs from workspace/okr/
        │     LLM: "Given these open issues and this sprint goal,
        │            what should Alice focus on today?"
        │
        └─ Private Slack DM to each flagged member
              (optional: DM summary to SM if notify_sm: true)
```

**Detection is deterministic.** No LLM is called until a vague standup is found — the check is just text length and issue reference presence.

**Recommendations are personalised.** The LLM sees only that individual's open sprint issues, the sprint goal, and the team OKRs. It doesn't have visibility into other team members' standups or history.

---

## What "vague" means

A `Today` section is flagged only when **all** of these are true:

1. It is under `min_today_words` words (default: 20)
2. It contains no `#NN` issue reference (when `require_issue_ref: true`)
3. It does not contain any of the exempt phrases below

### Exempt phrases (never flagged)

| Category | Phrases recognised |
|----------|-------------------|
| Reviews | `code review`, `pr review`, `pull request review` |
| Collaboration | `pairing`, `pair programming` |
| Ceremonies | `sprint planning`, `sprint review`, `retrospective`, `grooming`, `backlog` |
| Company events | `all-hands`, `interview` |
| Leave | `out of office`, `ooo`, `sick`, `sick leave`, `medical`, `holiday`, `travel` |
| Onboarding | `onboarding` |

This list errs on the side of caution — false positives (coaching someone who had a legitimate update) are worse than false negatives (missing a genuinely vague standup).

---

## Example DM

When Alice submits:
```markdown
## Today
working on things
```

Scraut detects this is vague (5 words, no issue reference), then fetches her open sprint issues and sends a private DM:

```
Looks like today could use a bit of focus! Given the sprint goal of shipping
the OAuth integration, #21 (OAuth: Google provider — 8 sp) would be the
most impactful thing to push forward — it's on the critical path for the v1.0
milestone. If that's blocked waiting on anything, #15 (rate limiting — 5 sp)
is self-contained and ready to go. Adding issue numbers in tomorrow's standup
helps the team spot dependencies early — keep it up!
```

The tone is always supportive. The prompt explicitly forbids the word "vague" and any implication that the person did something wrong.

---

## Configuration

```yaml
standup_coach:
  enabled: false                # off by default — SM opts in
  min_today_words: 20           # flag Today sections shorter than this
  require_issue_ref: true       # also require at least one #NN reference
  skip_sprint_start_days: 1     # skip coaching on the first N sprint working days
  notify_sm: false              # DM the SM a daily summary of who was coached
```

See [Configuration Reference → standup_coach](../reference/configuration#standup_coach) for full field descriptions.

---

## Privacy model

| What | Who sees it |
|------|------------|
| Individual recommendation DM | Only the team member |
| SM daily summary (if `notify_sm: true`) | Only the SM, as a DM |
| Public team channel (`slack_channel`) | Nothing — coach never posts here |
| `.scraut/` files | Nothing written — ephemeral, no stored history |

---

## Requirements

| Requirement | Why |
|-------------|-----|
| `SLACK_BOT_TOKEN` GitHub Secret | Required to send DMs. Without it, detection still runs but DMs are silently skipped. |
| Sprint issues assigned in GitHub | Without assignees on issues, the coach can't personalise recommendations. |
| `workspace/okr/okr.md` populated | Optional, but improves recommendation quality. |
| Sprint goal set in `sprint/NNN/meta.md` | Strongly recommended — the single most important input to the recommendation. |

---

## When to enable

**Good fit for your team if:**
- Your sprint backlog is well-labelled and issues are assigned to individuals
- The team is large enough that the SM can't check in individually every day
- You already use the morning DM standup links

**Hold off if:**
- Your backlog is messy or issues are rarely assigned to individuals — recommendations will be too generic to be useful
- Your team is small (2–3 people) and the SM already has daily 1:1 context

:::tip Start with the sprint goal
Even before enabling the coach, make sure `sprint/NNN/meta.md` has a clear, specific sprint goal. The LLM uses this as the primary ranking signal for recommendations. "Deliver rate limiting and OAuth to staging" produces far better recommendations than "continue development work".
:::

---

## Scenario: Coach helps a new team member

**Characters:** Charlie (new developer, joined mid-sprint), Bob (SM)

**Situation:** Charlie is ramping up and isn't sure which open issues to pick up.

**Charlie's standup:**
```markdown
## Today
Ramping up, going to look at the backlog
```

**What happens:**
1. Coach detects: 9 words, no issue reference → flagged
2. Coach fetches Charlie's assigned open issues: `#31 (API error handling, sp:3)`, `#34 (unit tests for auth, sp:2)`
3. Sprint goal: "Ship rate limiting and OAuth to staging"
4. LLM generates a recommendation ranking `#34` first (auth tests needed before OAuth can ship)
5. Charlie receives a private DM with specific next steps
6. Bob is not notified unless `notify_sm: true`

**Charlie sees clear guidance without needing a 1:1 with Bob.**
