---
sidebar_position: 2
---

# Configuration Reference

Full reference for every field in `workspace/scraut.yml`.

---

## `sprint`

```yaml
sprint:
  length_days: 14         # int — Sprint duration in calendar days
  start_day: monday       # string — monday | tuesday | wednesday | thursday | friday
  start_time: "09:00"     # string — HH:MM in 24-hour format
  timezone: "UTC"         # string — IANA timezone identifier
  capacity_buffer: 0.85   # float 0–1 — Sprint capacity safety factor
  current_sprint: 1       # int — Auto-managed; do not edit manually
  folder_padding: 3       # int — Zero-padding width for sprint folder names
```

| Field | Default | Notes |
|-------|---------|-------|
| `length_days` | `14` | Calendar days, not working days |
| `start_day` | `monday` | Affects morning notification scheduling |
| `start_time` | `"09:00"` | Combined with timezone for cron scheduling |
| `timezone` | `"UTC"` | Use `pytz`-compatible IANA string |
| `capacity_buffer` | `0.85` | `planning_capacity = velocity × buffer` |
| `current_sprint` | `1` | Incremented automatically by `close_sprint.py` |
| `folder_padding` | `3` | Digits in sprint folder names: `3` → `sprint/001/`, `4` → `sprint/0001/`. Widen with `scraut sprint repad <N>`. Never reduce. |
| `work_days` | Mon–Fri | List of day names your team works. Affects `is_working_day()`, burndown ideal line, and ceremony skip logic. See examples below. |

**`work_days` examples:**

```yaml
# Standard Mon–Fri (default — field can be omitted)
work_days: [monday, tuesday, wednesday, thursday, friday]

# Middle East / Gulf Sun–Thu
work_days: [sunday, monday, tuesday, wednesday, thursday]

# 4-day week (Mon–Thu)
work_days: [monday, tuesday, wednesday, thursday]
```

Day names are case-insensitive. Unknown names are ignored with a warning. If the list is empty or the field is absent, Mon–Fri is assumed.

---

## `team`

```yaml
team:
  members:
    - login: string        # required — exact GitHub username
      display: string      # required — human-readable name
      role: string         # optional — developer | product_owner | scrum_master
      slack_id: string     # optional — Slack member ID for morning DMs
      email: string        # optional — email for weekly digest
  product_owner: string    # optional — login of the PO (informational)
  scrum_master: string     # optional — login of the SM (informational)
  slack_channel: string    # required — e.g. "#scraut-bot"
```

| Field | Required? | Notes |
|-------|-----------|-------|
| `members[].login` | Yes | Exact GitHub username — used for standup file paths |
| `members[].display` | Yes | Human-readable name shown in summaries and reports |
| `members[].role` | No | Informational label in LLM prompts; does not gate any action |
| `members[].slack_id` | No | Required for morning DMs; silently skipped if absent |
| `members[].email` | No | Required for weekly email digest; skipped if absent |
| `product_owner` | No | Informational — not read by any current workflow |
| `scrum_master` | No | Informational — not read by any current workflow |
| `slack_channel` | Yes | Channel for all ceremony posts (e.g. `#scraut-bot`) |

:::note Role fields are informational
`product_owner`, `scrum_master`, and `members[].role` do not currently change what automation runs. Any team member with repo write access can trigger any workflow. The fields exist as documentation of intent and as a foundation for future role-based routing. **They can all be set to the same person** — common for small teams and solo setups.
:::

---

## `ceremonies`

```yaml
ceremonies:
  planning: true      # Sprint planning workflow
  standup: true       # Daily standup summarisation
  grooming: true      # Mid-sprint backlog grooming
  review: true        # Sprint review generation
  retrospective: true # Retrospective synthesis
  estimation: true    # Emoji-based story point voting
```

Set to `false` to disable an entire ceremony's automation.

---

## `definition_of_done`

```yaml
definition_of_done:
  - string   # Each item is a DoD criterion checked by the LLM when issues close
```

The LLM checks each criterion against the closed issue's linked PRs. Write criteria in plain English — be specific about what "done" means.

---

## `repos`

```yaml
repos:
  - name: string          # Display name for this repo
    url: string           # org/repo format (e.g. myorg/backend-api)
    branch_filter:        # List of branch names to watch
      - string
    enabled: boolean      # true | false
```

Multiple repos can be configured. Set `enabled: false` to temporarily pause sync without removing the config.

Requires `SCRAUT_GITHUB_TOKEN` secret with `repo:read` permission.

---

## `llm`

```yaml
llm:
  provider: string      # anthropic | openai | gemini | ollama
  model: string         # Provider-specific model name
  base_url: string      # Optional: custom API endpoint
  max_tokens: integer   # Per-call output token limit
  cost_controls:
    max_daily_tokens: integer    # Hard daily limit across all calls
    batch_where_possible: bool  # Combine multiple LLM calls where safe
```

See [LLM Providers](./llm-providers) for model options and base_url examples.

---

## `agents`

```yaml
agents:
  enabled: boolean      # Master switch for agent mode

  roles:
    - id: string               # Unique identifier (e.g. agent-backend)
      type: string             # orchestrator | specialist
      specialty: string        # backend | frontend | testing | review
      enabled: boolean         # Per-agent enable/disable
      github_workflow: string  # Path to the agent's workflow file
      description: string      # Human-readable description

  human_checkpoints:
    - event: string            # sprint_boundary | milestone_eta_slip |
                               # escalation_count | agent_failure

  autonomy_level: string       # supervised | semi-auto | full-auto
```

---

## `notifications`

```yaml
notifications:
  slack_webhook: string        # Leave empty — use SLACK_WEBHOOK secret
  morning_dm: boolean          # Send personal DM at 7:55am
  weekly_email: boolean        # Send Monday email digest
  stakeholder_emails:          # Email list for weekly digest
    - string
```

**Important:** Never put the webhook URL directly in `scraut.yml`. Leave `slack_webhook: ""` and use the `SLACK_WEBHOOK` GitHub Secret instead.

---

## `portal`

```yaml
portal:
  enabled: boolean        # Enable visibility portal
  title: string           # Dashboard title
  public: boolean         # false = private GitHub Pages (requires Team/Enterprise plan)
  refresh_minutes: int    # How often board state syncs from text files
  sync_board: boolean     # Sync GitHub Projects board alongside HTML portal (default: true)
  project_number: int     # GitHub Projects board number — required for board sync
                          # Find it in the URL: github.com/orgs/your-org/projects/N
```

| Field | Default | Notes |
|-------|---------|-------|
| `enabled` | `true` | Master switch for portal generation |
| `title` | `"<org> Dashboard"` | Shown in the portal header |
| `public` | `true` | Private Pages requires GitHub Team/Enterprise plan |
| `refresh_minutes` | `30` | Cron interval for the visibility engine |
| `sync_board` | `true` | Set to `false` to disable GitHub Projects board sync while keeping the HTML portal |
| `project_number` | *(unset)* | Required when `sync_board: true`. Without it, board sync is skipped with a warning. HTML portal always generates regardless. |

:::tip Board sync is on by default
When `sync_board: true`, the visibility engine updates your GitHub Projects board on every run. Set `project_number` to the board number from the URL (e.g. `https://github.com/orgs/myorg/projects/5` → `project_number: 5`).

To turn off board sync entirely without disabling the portal:
```yaml
portal:
  sync_board: false
```
:::

:::info HTML portal vs. GitHub Projects board
These are two separate outputs from the same pipeline:
- **HTML portal** (`apps/portal/index.html`) — always generated, deployed to GitHub Pages
- **GitHub Projects board** — only updated if `sync_board: true` AND `project_number` is set

Both are derived from text files. The board is never read to make decisions.
:::

---

## `suggestions`

```yaml
suggestions:
  enabled: boolean            # Enable pattern detection
  min_evidence_count: int     # Min occurrences before generating a suggestion (default: 3)
  measurement_sprints: int    # Sprints to measure after implementation (default: 2)
```

---

## `paths`

```yaml
paths:
  workspace: string    # Root for human-editable files (default: workspace)
  scraut: string       # Root for bot-generated files (default: .scraut)
  portal: string       # Portal application path (default: apps/portal)
```

Do not change `paths` unless you are restructuring the repository.

---

## `holidays`

Controls which days Scraut treats as non-working. Two sources are merged:

1. **Nager.Date API** — automatic public holidays by country (free, no API key)
2. **Manual overrides** — `extra_dates` adds company/team days; `skip_dates` removes API dates your team works anyway

**Merged rule:** `(api_holidays ∪ extra_dates) − skip_dates`

```yaml
holidays:
  country_code: "ID"    # ISO 3166-1 alpha-2 (e.g. US, ID, GB, AU). Blank = no API lookup
  extra_dates:          # Company/team holidays not covered by the API (YYYY-MM-DD)
    - "2026-12-26"
    - "2026-08-17"
  skip_dates:           # API-provided dates your team works anyway (YYYY-MM-DD)
    - "2026-01-02"
```

| Field | Default | Notes |
|-------|---------|-------|
| `country_code` | `""` | ISO 3166-1 alpha-2. Leave blank to disable API lookup. |
| `extra_dates` | `[]` | Additional non-working dates. Useful for company-wide days, bridge days, regional observances not in the API. |
| `skip_dates` | `[]` | Override API holidays — treat these as normal working days. |

**Effect on Scraut ceremonies:**

| What skips on holidays | What is not affected |
|------------------------|----------------------|
| Daily standup template creation | Sprint planning (manual trigger) |
| Morning Slack DMs | Retrospective / review (manual trigger) |
| Burndown chart (holidays excluded from ideal line) | Sprint velocity calculations |

**API caching:** Results are cached in `.scraut/holidays/{CC}/{YEAR}.json` on first fetch and reused for all subsequent runs. Delete the file to force a refresh.

:::tip Supported countries
Nager.Date covers 100+ countries. Check the full list at [date.nager.at/Country](https://date.nager.at/Country).
:::

---

## Environment variables reference

All secrets are GitHub repository secrets — never committed to files.

| Variable | Used by | Required? |
|----------|---------|----------|
| `GITHUB_TOKEN` | All workflows | Auto-provided |
| `ANTHROPIC_API_KEY` | LLM workflows | If using Anthropic |
| `OPENAI_API_KEY` | LLM workflows | If using OpenAI |
| `GOOGLE_API_KEY` | LLM workflows | If using Gemini |
| `SLACK_WEBHOOK` | Notification workflows | Recommended |
| `SLACK_BOT_TOKEN` | Morning DM workflow | Optional |
| `SCRAUT_GITHUB_TOKEN` | Repo sync workflow | Optional |
| `SMTP_HOST` | Weekly email digest | Optional |
| `SMTP_PORT` | Weekly email digest | Optional |
| `SMTP_USER` | Weekly email digest | Optional |
| `SMTP_PASS` | Weekly email digest | Optional |
