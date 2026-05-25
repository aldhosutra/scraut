---
sidebar_position: 7
---

# Team Roles

Scraut has three places where you assign roles to people. This page explains what each does — and, importantly, what each does not do.

---

## Overview

| Field | Location in `scraut.yml` | Effect on automation |
|-------|--------------------------|----------------------|
| `members[].role` | Per-member in `team.members` | None — informational label only |
| `product_owner` | `team.product_owner` | None — informational only |
| `scrum_master` | `team.scrum_master` | None — informational only |

**All three role fields are currently informational.** No workflow reads them to decide who gets notified, who can trigger a ceremony, or who gets an alert. Every team member with repository write access can trigger any workflow from the GitHub Actions tab.

---

## `members[].role`

Each entry in `team.members` has an optional `role` field:

```yaml
team:
  members:
    - login: alice
      display: Alice
      role: developer        # developer | product_owner | scrum_master
    - login: bob
      display: Bob
      role: scrum_master
```

This field appears in LLM prompt context so the model understands the team structure when generating summaries, planning documents, and retrospective synthesis. It has no effect on which workflows run or which notifications are sent.

---

## `product_owner`

```yaml
team:
  product_owner: alice
```

Intended use: the person responsible for the product backlog and acceptance criteria. Currently stored in config and available as context for LLM prompts, but not read by any workflow to change behavior.

---

## `scrum_master`

```yaml
team:
  scrum_master: bob
```

Intended use: the person who facilitates ceremonies and unblocks the team. Same status as `product_owner` — stored in config, informational only.

---

## Can `product_owner` and `scrum_master` be the same person?

Yes. This is fully supported and common for small teams:

```yaml
team:
  product_owner: alice
  scrum_master: alice
```

There is no validation that they are different. Solo teams, two-person startups, and anyone wearing multiple hats should feel free to set both to the same login.

---

## Can a role holder be outside `members`?

Yes. `product_owner` and `scrum_master` are free-text GitHub logins — they do not have to appear in `team.members`. This is useful if your PO or SM is an external stakeholder who doesn't participate in daily standups:

```yaml
team:
  members:
    - login: alice
      display: Alice
      role: developer
    - login: bob
      display: Bob
      role: developer
  product_owner: external-po   # not in members — no standup file created
  scrum_master: alice
```

Someone outside `members` will not get standup file templates, morning DMs, or retro templates. They can still access the repository and trigger workflows manually.

---

## Who can trigger workflows?

Any GitHub user with **write access** to the repository can manually trigger `workflow_dispatch` workflows from the Actions tab. There is no role check. The ceremonies that require a manual trigger are:

- Sprint Planning — `sprint-planning.yml`
- Sprint Review — `sprint-review.yml`
- Sprint Retrospective — `sprint-retrospective.yml`
- Milestone Planning — `milestone-planning.yml`

On small teams, any member can kick these off. On larger teams, you may want to restrict this via GitHub's branch protection or environment protection rules outside of Scraut.

---

## Future direction

These fields are designed to support role-based routing in future releases, such as:
- Routing agent escalations to the SM
- Routing backlog priority conflicts to the PO
- Filtering ceremony notifications by role

When that functionality is added, the fields will be read by the relevant scripts. No migration will be required — the config structure will not change.
