---
id: scrum-primer
sidebar_position: 2
---

# Scrum Primer

A complete overview of Scrum for teams that are new to the framework — covering concepts, ceremonies, artifacts, visual tools, and the hard rules that make it work. Each section notes how Scraut automates the corresponding piece.

If you already know Scrum well, skip straight to [Getting Started](./getting-started/prerequisites).

---

## What is Scrum?

Scrum is a lightweight **agile framework** for delivering complex work in short, regular cycles called **sprints**. It was codified in the [Scrum Guide](https://scrumguides.org) (Schwaber & Sutherland) and is the most widely-used agile method in software teams worldwide.

The core idea is **empiricism** — you learn by doing, inspect what you built, and adapt your process. Three pillars hold it up:

| Pillar | What it means in practice |
|--------|--------------------------|
| **Transparency** | Everyone sees the same backlog, the same sprint board, the same blockers |
| **Inspection** | The team regularly checks its progress — daily in standup, end-of-sprint in review |
| **Adaptation** | When something is off, the team changes the plan — not the goal |

Scrum also names five values that healthy teams try to live by: **Commitment, Focus, Openness, Respect, and Courage**.

---

## The three roles

| Role | Responsibility |
|------|---------------|
| **Product Owner (PO)** | Owns the product backlog. Decides what gets built and in what order. Single source of business priority. |
| **Scrum Master (SM)** | Facilitates the ceremonies, removes blockers, coaches the team on Scrum. Shields the team from outside interruption. |
| **Developers** | The people doing the work. Self-organize to deliver the sprint goal. |

> Scraut maps these roles to `product_owner` and `scrum_master` in `scraut.yml`. Each role receives different notifications, owns different files, and has different responsibilities in each ceremony.

---

## The sprint

A **sprint** is a fixed-length iteration — usually 1–4 weeks — during which the team builds a potentially releasable increment of the product. Sprints are the heartbeat of Scrum.

Key properties:
- **Fixed length.** Every sprint is the same duration. Never shorten or extend a sprint — if work didn't finish, roll it over.
- **Has a goal.** The sprint goal is agreed at planning. It answers *why* the team is doing this sprint, not just *what*.
- **Ends with an increment.** Something usable is produced every sprint, even if not released.
- **Can be cancelled.** Only the Product Owner can cancel a sprint — and only when the sprint goal has become obsolete (e.g. a pivot). This is rare and disruptive; a new sprint starts immediately after.

### The sprint goal

The sprint goal is a single sentence agreed at planning that describes **why** the team is running this sprint. It is more durable than the list of stories — if a story turns out wrong mid-sprint, the team can substitute another story that still serves the goal.

**Example:** *"By end of sprint, users can create an account and complete their first purchase."*

A sprint without a goal is just a list of tasks. Goals give the team shared direction and make trade-off decisions obvious.

> Scraut captures the sprint goal in `workspace/sprint/NNN/meta.md`. The sprint planning PR is titled with the goal.

---

## The work hierarchy

Scrum work items are organised in a three-level hierarchy:

```
Epic
 └── Story (User Story)
      └── Task
```

### Epic

An **epic** is a large body of work that cannot be completed in a single sprint. Epics are broken down into stories. They typically map to a major feature, capability, or milestone objective.

**Example:** *Epic: "User authentication system"*

### User Story

A **user story** is the primary unit of work in Scrum. It describes a feature from the perspective of the person who will use it:

```
As a [type of user],
I want [a goal],
so that [a reason/benefit].
```

**Example:** *"As a new customer, I want to create an account with my email, so that I can save my cart and order history."*

Stories should be small enough to complete within a single sprint (ideally in a few days). If a story cannot fit in one sprint, split it.

### Acceptance Criteria

Each story has **acceptance criteria (AC)** — a concrete checklist that defines when the story is done. AC is written by the PO, refined with the team during grooming.

**Example AC for the story above:**
- User can register with email + password
- Duplicate emails are rejected with a clear error message
- Confirmation email is sent within 60 seconds
- Account persists across sessions

:::warning Acceptance criteria must be written before sprint planning
Stories without AC should not enter the sprint. Without clear AC, developers don't know when to stop building, and the PO doesn't know what to test.
:::

### Task

A **task** is a technical step a developer creates during sprint planning to complete a story. Tasks are internal to the team — not visible to stakeholders. They typically take a few hours each.

**Example tasks for the story above:**
- Create `POST /api/register` endpoint
- Write registration form component
- Add email validation and duplicate check
- Set up transactional email service
- Write integration tests for registration flow

> In Scraut, epics and stories are GitHub Issues with the `epic` or `story` label. Tasks use the `task` label. Story points are tracked with `sp:N` labels.

---

## Estimation and story points

### What are story points?

**Story points** are a unit of measure for the *complexity and effort* of a story — not the number of hours. The team agrees on a relative scale (Scraut uses Fibonacci: **1, 2, 3, 5, 8, 13**).

> A story estimated at 8 points is roughly twice as complex as one at 3 points — but "8 points" doesn't mean "8 hours." Story points are relative, not absolute.

This matters because:
- Hour estimates are systematically optimistic (people forget testing, code review, rework)
- Relative sizing is more accurate and converges quickly in team discussions
- Over time, the team's "points per sprint" stabilises into a **velocity** that makes planning reliable

### How estimation works

The team uses **Planning Poker** (or emoji reactions in Scraut):
1. The PO presents a story and answers clarifying questions
2. Each developer privately picks an estimate
3. All estimates are revealed simultaneously
4. If there is wide disagreement, the highest and lowest estimators explain their reasoning
5. The team re-estimates until convergence
6. The agreed estimate is attached to the story

Revealing estimates simultaneously prevents anchoring bias (where the first number said influences everyone else).

### The Fibonacci scale explained

| Points | Meaning |
|--------|---------|
| 1 | Trivial — well-understood, minimal risk |
| 2 | Simple — straightforward, few unknowns |
| 3 | Small — some complexity, mostly clear |
| 5 | Medium — meaningful complexity or some uncertainty |
| 8 | Large — significant complexity, multiple moving parts |
| 13 | Very large — high uncertainty; should be split before sprint |

> Stories estimated at 13 points are almost always too big for one sprint. The team should split them during grooming before they enter planning.

> Scraut automates emoji-reaction estimation in GitHub Issues using the `estimation.yml` workflow and the `sp:N` label system.

---

## Velocity

**Velocity** is the number of story points the team completes per sprint, averaged over the last 3–6 sprints.

It is used exclusively for **planning** — to predict how much work the team can commit to in the next sprint. It is never used to compare teams or judge individual performance.

```
Sprint 1: 24 sp  Sprint 2: 28 sp  Sprint 3: 22 sp  → Rolling average: 25 sp
```

### Capacity planning

Raw velocity assumes a full team for the full sprint. Capacity adjusts for reality:

```
Available capacity = velocity × capacity_buffer × (available_days / sprint_days)
```

Factors that reduce capacity:
- Team member on leave or OOO
- Public holidays (see [holidays config](./reference/configuration#holidays))
- Planned work outside the sprint (on-call, conferences, interviews)
- Sprint 1 of a new team (no historical velocity yet — start conservatively)

> Scraut tracks capacity in `workspace/team/capacity.md` and applies `sprint.capacity_buffer` (default 0.85 = plan to 85% of velocity) to avoid over-committing.

---

## The Definition of Ready

The **Definition of Ready (DoR)** is the counterpart to the Definition of Done — it defines when a backlog item is *ready to be pulled into a sprint*.

A typical DoR checklist:
- [ ] User story is written in the standard format
- [ ] Acceptance criteria are defined and agreed with PO
- [ ] Story is estimated by the team
- [ ] Dependencies are identified (and resolved or accepted)
- [ ] Story fits within one sprint (≤ 8 sp recommended)
- [ ] UI mockups or technical design attached (if applicable)

:::tip Use the DoR as a grooming exit gate
An item that doesn't pass the DoR should not enter sprint planning. It goes back to grooming. This keeps planning fast and prevents mid-sprint confusion.
:::

---

## Ceremonies

Scrum has six recurring ceremonies. Each exists for a specific reason — removing any one of them weakens the whole system.

### 1. Backlog Grooming (Refinement)

**When:** Mid-sprint, typically once or twice per sprint  
**Who:** PO + Developers (SM optional)  
**Duration:** ≤ 10% of sprint capacity (e.g. ~1 hour/week for a 2-week sprint)

The PO and team review upcoming backlog items, clarify requirements, split large stories, write acceptance criteria, and estimate. Items exit grooming ready for planning (DoR met).

**Benefit:** Teams that skip grooming spend half of sprint planning arguing about unclear requirements. Grooming separates the "what do we build?" conversation from the "when do we build it?" decision.

**Scraut output:** `workspace/sprint/NNN/grooming/backlog-ideas.md` — a team-maintained file for grooming notes and new story ideas.

→ [How Scraut automates grooming](./ceremonies/backlog-grooming)

---

### 2. Estimation

**When:** During or just after grooming  
**Who:** Developers (PO available for questions)  
**Duration:** Included in grooming session

The team assigns story points to backlog items using Planning Poker (see [Estimation and story points](#estimation-and-story-points) above).

**Benefit:** Individual estimates are optimistic. Team estimation surfaces hidden complexity, distributes knowledge, and builds shared ownership of the work.

**Scraut output:** GitHub Issues are labelled `sp:N` automatically from emoji-reaction votes.

→ [How Scraut automates estimation](./ceremonies/estimation)

---

### 3. Sprint Planning

**When:** First day of the sprint  
**Who:** Entire team  
**Duration:** ≤ 2 hours per sprint week (e.g. 4 hours for a 2-week sprint)

The team selects items from the top of the groomed backlog and commits to a sprint goal. Developers break selected stories into tasks and collectively agree the plan is achievable within capacity.

**Benefit:** Planning aligns the whole team on what success looks like for this sprint. Without it, individuals optimise locally instead of toward a shared goal.

**Scraut output:** A sprint planning PR is opened with `workspace/sprint/NNN/meta.md` pre-filled with velocity data, capacity, and suggested stories.

→ [How Scraut automates sprint planning](./ceremonies/sprint-planning)

---

### 4. Daily Standup

**When:** Every working day, same time  
**Who:** Developers (SM facilitates, PO optional)  
**Duration:** ≤ 15 minutes (strictly)

Each person answers three questions:
1. What did I complete since the last standup?
2. What will I work on today?
3. What is blocking me?

The standup is a **synchronisation meeting**, not a status report to management. Blockers raised here are resolved *after* the meeting by the SM.

**Benefit:** Problems surface daily instead of festering for two weeks. The team stays aligned on sprint progress without lengthy meetings.

**Scraut outputs:**
- `workspace/sprint/NNN/standup/YYYY-MM-DD/[login].md` — template created automatically each morning
- `.scraut/sprint/NNN/standup/summary/YYYY-MM-DD.md` — LLM-generated daily summary
- Slack message posted to team channel with summary
- Morning Slack DM to each team member with their standup link

→ [How Scraut automates standups](./daily-workflows/standup)

---

### 5. Sprint Review

**When:** Last day of the sprint (or day before retrospective)  
**Who:** Entire team + stakeholders  
**Duration:** ≤ 1 hour per sprint week

The team **demonstrates** what was built. Stakeholders give feedback. The PO updates the backlog based on what was learned. This is an informal working session — not a presentation.

**Benefit:** Real stakeholder feedback every sprint, not once a quarter. The team builds the right thing because they validate direction regularly.

**Scraut outputs:**
- `.scraut/sprint/NNN/review/review.md` — LLM-generated review document summarising completed work, stories closed, velocity, and stakeholder notes
- Slack message posted with sprint summary

→ [How Scraut automates sprint review](./ceremonies/sprint-review)

---

### 6. Sprint Retrospective

**When:** After review, before the next sprint starts  
**Who:** Entire team (no stakeholders)  
**Duration:** ≤ 45 min per sprint week

The team inspects its own process: what went well, what could improve, and what *one or two concrete actions* to take next sprint. Each action gets an owner and a due date.

**Benefit:** Continuous process improvement. Teams that retro consistently get measurably faster and healthier over 3–6 months.

**Scraut outputs:**
- `workspace/sprint/NNN/retrospective/[login].md` — template created per team member
- `.scraut/sprint/NNN/retrospective/summary.md` — LLM-synthesised retro summary with recurring themes and action items
- Slack message posted with synthesis

→ [How Scraut automates retrospectives](./ceremonies/retrospective)

---

## Artifacts

### Product Backlog

The ordered list of everything that might be built — features, bugs, technical debt, spikes. The **Product Owner** owns and prioritises it. It is never frozen; it evolves as the team learns.

> In Scraut: GitHub Issues without a sprint label. The PO prioritises by milestone and label.

### Sprint Backlog

The subset of the product backlog selected for this sprint, plus the sprint goal and the tasks the team created during planning. The **Developers** own it and update it daily.

> In Scraut: GitHub Issues labelled `sprint-NNN` + `in-sprint`. The team updates issue state as work progresses.

### Increment

The sum of all completed work this sprint (and all previous sprints). Must meet the **Definition of Done** to count. The increment is the tangible output of every sprint — a potentially releasable product.

> In Scraut: Closed GitHub Issues that passed the DoD check workflow.

### Definition of Done (DoD)

A shared checklist that defines what "Done" actually means for your team. Every story must pass all criteria before it can be marked complete.

**Typical DoD items:**
- [ ] Tests written for new functionality
- [ ] PR reviewed by at least one team member
- [ ] Acceptance criteria mentioned in PR description
- [ ] No open review comments
- [ ] CI passing

> In Scraut: Defined in `definition_of_done` in `scraut.yml`. The `dod-check.yml` workflow automatically verifies PRs against this list.

### Definition of Ready (DoR)

The entry gate for sprint planning — see [The Definition of Ready](#the-definition-of-ready) above.

---

## Visual tracking artifacts

These tools give the team and stakeholders a quick picture of sprint health without reading every issue.

### Burndown Chart

A **burndown chart** tracks the amount of work remaining in the sprint over time. The X-axis is calendar days; the Y-axis is story points remaining.

```
SP remaining
 30 │╲  ← ideal line (linear burn)
    │ ╲
 20 │  ╲____   ← actual line
    │       ╲__
 10 │          ╲
    │            ╲
  0 └─────────────────── days
    Day 1        Day 14
```

Two lines are plotted:
- **Ideal line** — straight line from total committed SP on day 1 to zero on the last day. Accounts for weekends, public holidays, and `work_days` config.
- **Actual line** — story points remaining as issues are closed. If the actual line is above the ideal, the sprint is at risk.

**What it tells you:**
- Actual above ideal line → team is behind; may not finish sprint
- Actual below ideal line → team is ahead; PO may pull in extra stories
- Flat actual line mid-sprint → team is blocked or not closing issues promptly
- Steep drop then flat → work is being completed in batches (waterfall smell)

> Scraut generates the burndown PNG with the `burndown-chart.yml` workflow. Ideal line automatically excludes weekends, public holidays, and non-work days configured in `sprint.work_days`. Saved to `.scraut/sprint/NNN/review/burndown.png`.

### Velocity Chart

A **velocity chart** shows story points completed per sprint over the last N sprints. It is the primary input to capacity planning.

```
SP completed
 34 │         ██
 30 │   ██    ██    ██
    │   ██    ██    ██    ██
 20 │   ██    ██    ██    ██
    └────────────────────────
       Sp1   Sp2   Sp3   Sp4
```

Use it to:
- Set realistic sprint commitments (commit to average, not max)
- Spot trends — is the team speeding up, slowing down, or erratic?
- Flag abnormal sprints (onboarding, holidays, incidents)

> Scraut calculates rolling velocity with `scraut velocity` (CLI) or `calculate_velocity.py`. Available in `.scraut/sprint/NNN/review/review.md`.

### Milestone Health Report

A forecast of whether an upcoming product milestone will be delivered on time, based on current velocity and remaining work.

**Inputs:** remaining story points in the milestone, current velocity, team capacity, sprint end date  
**Output:** estimated delivery sprint/date, confidence level, risk flags

> Scraut generates milestone health reports in `.scraut/milestones/{name}/health/` on each sprint close. The visibility portal shows a live forecast for each milestone.

---

## Scraut-generated outputs — complete map

Every Scrum artifact and ceremony produces a file, a label change, or a Slack message in Scraut:

| Scrum concept | Scraut output | Where |
|---------------|--------------|-------|
| Product Backlog | GitHub Issues (open, no sprint label) | GitHub Issues tab |
| Sprint Backlog | Issues labelled `sprint-NNN` + `in-sprint` | GitHub Issues / Projects board |
| Sprint Goal | `sprint/NNN/meta.md` → planning PR title | `workspace/sprint/NNN/meta.md` |
| Story estimation | `sp:N` label on each issue | GitHub Issue labels |
| Standup template | Per-member `.md` file created each morning | `workspace/sprint/NNN/standup/DATE/` |
| Standup summary | LLM digest of all standups | `.scraut/sprint/NNN/standup/summary/DATE.md` |
| Standup Slack post | Team channel message | Slack |
| Morning DM | Personal standup link per member | Slack DM |
| Sprint planning PR | Pre-filled meta.md with velocity + capacity | GitHub PR |
| Sprint review | Completed stories + velocity summary | `.scraut/sprint/NNN/review/review.md` |
| Retrospective synthesis | Themes + action items from all retro files | `.scraut/sprint/NNN/retrospective/summary.md` |
| Burndown chart | Sprint progress PNG | `.scraut/sprint/NNN/review/burndown.png` |
| Velocity report | Rolling average + trend | `.scraut/sprint/NNN/review/review.md` |
| Milestone health | Delivery forecast + risk flags | `.scraut/milestones/{name}/health/` |
| Definition of Done check | Per-PR compliance report | GitHub PR comment |
| Suggestions | Process improvement proposals from pattern detection | `.scraut/suggestions/active/` |
| Insights | Cross-sprint patterns and team health metrics | `.scraut/insights/` |
| Weekly digest | Email or Slack summary across all sprints | Email / Slack |
| Visibility portal | HTML dashboard for stakeholders | `apps/portal/` (GitHub Pages) |
| GitHub Projects board | Auto-synced sprint board | GitHub Projects |

---

## Hard rules

These are the non-negotiable constraints that make Scrum work. Violating them produces a process that looks like Scrum but loses its benefits — sometimes called **"ScrumBut"** ("We do Scrum, *but* we…").

:::danger No new scope mid-sprint
Once sprint planning is complete, the sprint backlog is **locked**. New requests go on the product backlog for the *next* sprint. The only exception is a genuine emergency that changes the sprint goal — in which case the sprint may be cancelled and replanned.

**Why it matters:** Mid-sprint additions destroy focus, blow the sprint goal, and make velocity measurements meaningless.
:::

:::danger Definition of Done is not negotiable
An item is not "Done" unless it meets every criterion in the DoD. "Done but not tested" or "Done but not deployed" does not count. Undone work accumulates as **technical debt** and surprises the team in future sprints.
:::

:::danger Stories without acceptance criteria don't enter the sprint
If a story doesn't have clear, agreed acceptance criteria at the start of planning, it goes back to grooming. Without AC, developers don't know when to stop and QA can't verify the work.
:::

:::warning The sprint length is fixed
You cannot shorten a sprint because "we finished early" or extend one because "we need more time." Unfinished items roll to the next sprint. The fixed cadence is what makes planning, velocity, and ceremonies predictable.
:::

:::warning Only the PO reprioritises the backlog
Developers, stakeholders, and managers do not unilaterally move items to the top of the backlog. They request it from the PO. This keeps the team from being pulled in multiple directions by competing stakeholders.
:::

:::warning Blockers are raised daily — not at the end of the sprint
If you are blocked, it goes in today's standup. Not in a private Slack message. Not in the review. The Scrum Master's job is to clear blockers within 24 hours.
:::

:::warning Velocity is not a performance metric
Never use velocity to compare teams, set targets, or evaluate individuals. It is a planning input for one team only. Teams that are evaluated on velocity inflate estimates and game the system.
:::

:::tip Estimation is a team sport
No single person estimates a story. The whole development team estimates together because *they* will do the work and each person may see a different risk. Estimates made by one person and accepted silently are not commitments — they're guesses.
:::

:::tip Retrospective actions need an owner and a sprint
An action item without an owner is a wish. Write each retro action as: **"[Owner] will [specific change] by sprint [N]."** Open every retro by reviewing last sprint's actions.
:::

:::tip The standup is for the team, not for management
Developers should talk to each other in standup, not report upward. If a manager attends, they listen — they do not ask questions or redirect work. Turning standup into a status report kills psychological safety and causes people to hide problems.
:::

:::tip Split stories larger than 8 points before sprint planning
13-point stories almost always contain hidden complexity that will blow the sprint. Force the split in grooming. Smaller stories produce faster feedback, earlier integration, and less merge conflict.
:::

---

## Common Scrum mistakes

| Mistake | What goes wrong | The fix |
|---------|----------------|---------|
| Grooming is skipped | Planning takes all day; stories are unclear | Schedule grooming as a recurring calendar event |
| Sprint goal is vague or absent | The team has no shared direction; any work feels "on track" | Write one sentence: "By end of sprint, users can do X" |
| Stories have no acceptance criteria | Developers build the wrong thing; PO rejects work at review | AC is written before grooming ends; DoR enforces this |
| Velocity is used to compare teams | Teams game estimates; psychological safety drops | Velocity is a planning tool for one team only |
| Retro actions are never revisited | Nothing improves; team stops believing in retros | Open every retro by reviewing last sprint's actions |
| Standup runs 45 minutes | People stop coming | Park detailed discussions — resolve them after standup |
| PO is unavailable during sprint | Developers make assumptions; wrong things get built | PO must be reachable within a few hours for questions |
| Burndown is never looked at | Sprint failures are a surprise on the last day | Review the burndown at each standup; act when actual diverges from ideal |
| 13-point stories enter the sprint | Story gets stuck; nothing is "Done" by Friday | Enforce split-before-planning as a team norm |
| DoD is ignored under deadline pressure | Technical debt accumulates; quality degrades | DoD is non-negotiable — close the sprint with less scope instead |

---

## How Scraut fits in

Scraut automates the mechanical parts of Scrum so your team can focus on the human parts:

| Scraut does automatically | You still need to do |
|--------------------------|---------------------|
| Create standup templates each morning | Fill them in (takes ~2 min/day) |
| Generate LLM standup summary + Slack post | Read the summary, act on blockers |
| Calculate velocity and capacity | Interpret the numbers, adjust the plan |
| Open the sprint planning PR with data pre-filled | Have the planning conversation |
| Generate burndown chart (ideal vs actual) | Review it daily, pull in work if ahead |
| Run DoD checks on PRs | Fix the gaps before merging |
| Synthesise retrospective themes | Decide on actions, commit to owners |
| Detect process patterns (late closures, blocker clusters) | Evaluate and vote on suggestions |
| Forecast milestone health | Make strategic decisions on scope |
| Post sprint review notes | Present to stakeholders, gather feedback |

Scrum is a framework for human collaboration. Scraut removes the friction — it doesn't replace the thinking.
