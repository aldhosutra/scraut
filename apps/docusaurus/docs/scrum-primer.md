---
id: scrum-primer
sidebar_position: 2
---

# Scrum Primer

A short but complete overview of Scrum for teams that are new to the framework. If you already know Scrum well, skip straight to [Getting Started](./getting-started/prerequisites).

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

> Scraut maps these directly to `product_owner` and `scrum_master` in `scraut.yml`. All three roles receive different notifications and have different responsibilities in each ceremony.

---

## The sprint

A **sprint** is a fixed-length iteration — usually 1–4 weeks — during which the team builds a potentially releasable increment of the product. Sprints are the heartbeat of Scrum.

Key properties:
- **Fixed length.** Every sprint is the same duration. Never shorten or extend a sprint — if work didn't finish, roll it over.
- **Has a goal.** The sprint goal is agreed at planning. It answers *why* the team is doing this sprint, not just *what*.
- **Ends with an increment.** Something usable is produced every sprint, even if not released.

---

## Ceremonies

Scrum has six recurring ceremonies. Each exists for a specific reason — removing any one of them weakens the whole system.

### 1. Backlog Grooming (Refinement)

**When:** Mid-sprint, typically once or twice per sprint  
**Who:** PO + Developers (SM optional)  
**Duration:** ≤ 10% of sprint capacity (e.g. ~1 hour/week for a 2-week sprint)

The PO and team review upcoming backlog items, clarify requirements, split large stories, and attach acceptance criteria. Items are refined *before* they enter planning — so planning can move fast.

**Benefit:** Teams that skip grooming spend half of sprint planning arguing about unclear requirements. Grooming separates the "what do we build?" conversation from the "when do we build it?" decision.

→ [How Scraut automates grooming](./ceremonies/backlog-grooming)

---

### 2. Estimation

**When:** During or just after grooming  
**Who:** Developers (PO available for questions)  
**Duration:** Included in grooming session

The team assigns **story points** to backlog items using relative sizing (e.g. Fibonacci: 1, 2, 3, 5, 8, 13). Story points measure *complexity*, not hours.

**Benefit:** Individual hour estimates are notoriously inaccurate. Relative sizing — "this is twice as hard as that" — converges quickly and gives the team a shared understanding of effort. Over multiple sprints, story-point velocity becomes a reliable planning tool.

→ [How Scraut automates estimation](./ceremonies/estimation)

---

### 3. Sprint Planning

**When:** First day of the sprint  
**Who:** Entire team  
**Duration:** ≤ 2 hours per sprint week (e.g. 4 hours for a 2-week sprint)

The team selects items from the top of the groomed backlog and commits to a sprint goal. Developers break selected stories into tasks and collectively agree the plan is achievable.

**Benefit:** Planning aligns the whole team on *what success looks like* for this sprint. Without it, individuals optimise locally instead of toward a shared goal.

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

The standup is a **synchronisation meeting**, not a status report to management. Blockers raised here are resolved *after* the meeting.

**Benefit:** Problems surface daily instead of festering for two weeks. The team stays aligned on sprint progress without lengthy status emails.

→ [How Scraut automates standups](./daily-workflows/standup)

---

### 5. Sprint Review

**When:** Last day of the sprint (or day before retrospective)  
**Who:** Entire team + stakeholders  
**Duration:** ≤ 1 hour per sprint week

The team **demonstrates** what was built. Stakeholders give feedback. The PO updates the backlog based on what was learned.

**Benefit:** Real stakeholder feedback every sprint, not once a quarter. The team builds the right thing because they validate direction regularly.

→ [How Scraut automates sprint review](./ceremonies/sprint-review)

---

### 6. Sprint Retrospective

**When:** After review, before the next sprint starts  
**Who:** Entire team (no stakeholders)  
**Duration:** ≤ 45 min per sprint week

The team inspects its own process: what went well, what could improve, and what *one or two concrete actions* to take next sprint. Each action gets an owner and a due date.

**Benefit:** Continuous process improvement. Teams that retro consistently get measurably faster and healthier over 3–6 months. Teams that skip it plateau or regress.

→ [How Scraut automates retrospectives](./ceremonies/retrospective)

---

## Artifacts

| Artifact | Owner | What it is |
|----------|-------|-----------|
| **Product Backlog** | Product Owner | The ordered list of everything that might be built. The PO prioritises it; the team refines it. Never "frozen." |
| **Sprint Backlog** | Developers | The subset of the product backlog committed for this sprint, plus the sprint goal and the tasks the team created during planning. |
| **Increment** | Developers | The sum of all completed work this sprint (plus all previous sprints). Must meet the Definition of Done to count. |
| **Definition of Done (DoD)** | Team | A shared checklist of what "Done" actually means — tests written, PR reviewed, CI green, deployed to staging, etc. |

> In Scraut, the product backlog lives as GitHub Issues. The sprint backlog is issues labelled `sprint-NNN`. The DoD is defined in `scraut.yml` under `definition_of_done`.

---

## The hard rules

These are the non-negotiable constraints that make Scrum work. Violating them produces a process that looks like Scrum but loses its benefits — sometimes called **"ScrumBut"** ("We do Scrum, *but* we…").

:::danger No new scope mid-sprint
Once sprint planning is complete, the sprint backlog is **locked**. New requests go on the product backlog for the *next* sprint. The only exception is a genuine emergency that changes the sprint goal — in which case the sprint may be cancelled and replanned.

**Why it matters:** Mid-sprint additions destroy focus, blow the sprint goal, and make velocity measurements meaningless.
:::

:::danger Definition of Done is not negotiable
An item is not "Done" unless it meets every criterion in the DoD. "Done but not tested" or "Done but not deployed" does not count. Undone work accumulates as **technical debt** and surprises the team in future sprints.
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

:::tip Estimation is a team sport
No single person estimates a story. The whole development team estimates together because *they* will do the work and each person may see a different risk. Estimates made by one person and accepted silently are not commitments — they're guesses.
:::

:::tip Retrospective actions need an owner and a sprint
An action item without an owner is a wish. Write each retro action as: **"[Owner] will [specific change] by [sprint N]."** Review it at the next retro.
:::

:::tip The standup is for the team, not for management
Developers should talk to each other in standup, not report upward. If a manager attends, they listen — they do not ask questions or redirect work. Turning standup into a status report kills psychological safety and causes people to hide problems.
:::

---

## Common Scrum mistakes

| Mistake | What goes wrong | The fix |
|---------|----------------|---------|
| Grooming is skipped | Planning takes all day; stories are unclear | Schedule grooming as a recurring calendar event |
| Sprint goal is vague or absent | The team has no shared direction; any work feels "on track" | Write one sentence: "By end of sprint, users can do X" |
| Velocity is used to compare teams | Teams game estimates; psychological safety drops | Velocity is a planning tool for one team only |
| Retro actions are never revisited | Nothing improves; team stops believing in retros | Open every retro by reviewing last sprint's actions |
| Standup runs 45 minutes | People stop coming | Park detailed discussions — resolve them after standup |
| PO is unavailable during sprint | Developers make assumptions; wrong things get built | PO must be reachable within a few hours for questions |

---

## How Scraut fits in

Scraut automates the mechanical parts of Scrum so your team can focus on the human parts:

| Scraut does this automatically | You still need to do this |
|-------------------------------|--------------------------|
| Create standup template files daily | Fill them in (2 min/day) |
| Summarise standups with LLM | Read the summary, act on blockers |
| Open the sprint planning PR | Have the planning conversation |
| Generate sprint review notes | Present to stakeholders, gather feedback |
| Synthesise retrospective themes | Decide on actions, commit to owners |
| Calculate velocity and health | Interpret the numbers, adjust the plan |

Scrum is a framework for human collaboration. Scraut removes the friction — it doesn't replace the thinking.
