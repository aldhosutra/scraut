> **This file is never read by Scraut.** It exists to show the format.
> The real file Scraut reads is `feedback.md` in this folder.
> Scraut's grooming agent uses feedback.md to suggest backlog priorities.

---

# Customer Feedback

<!-- Record customer feedback, support tickets, user research findings, NPS comments.
     The grooming agent reads this to recommend which issues to prioritise.
     Add new rows to the table as feedback arrives — no need to reformat. -->

## Feedback Log

| Date       | Source              | Summary                                        | Priority | Linked Issue |
|------------|---------------------|------------------------------------------------|----------|--------------|
| 2026-05-10 | Support ticket #47  | Can't reset password from mobile Safari        | high     | #23          |
| 2026-05-14 | User interview (3)  | Dashboard takes 8s to load on first visit      | medium   | —            |
| 2026-05-18 | NPS survey comment  | "API docs are confusing — examples are wrong"  | medium   | —            |
| 2026-05-20 | Slack DM from @dave | CSV export cuts off at 500 rows                | high     | #31          |

## Themes

<!-- Recurring patterns the team has identified across multiple feedback sources -->

- **Auth friction** — 5 separate tickets about login/password issues this quarter. Users expect SSO.
- **Performance on first load** — 3 interviews flagged dashboard speed; likely cold-start of the data aggregation job.
- **Documentation gaps** — Code examples in Getting Started guide reference v0.8 API, not v1.0.
