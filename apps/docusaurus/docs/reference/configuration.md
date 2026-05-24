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
```

| Field | Default | Notes |
|-------|---------|-------|
| `length_days` | `14` | Calendar days, not working days |
| `start_day` | `monday` | Affects morning notification scheduling |
| `start_time` | `"09:00"` | Combined with timezone for cron scheduling |
| `timezone` | `"UTC"` | Use `pytz`-compatible IANA string |
| `capacity_buffer` | `0.85` | `planning_capacity = velocity × buffer` |
| `current_sprint` | `1` | Incremented automatically by `close_sprint.py` |

---

## `team`

```yaml
team:
  members:
    - login: string        # required — exact GitHub username
      display: string      # required — human-readable name
      role: string         # required — developer | product_owner | scrum_master
      slack_id: string     # optional — Slack member ID for morning DMs
      email: string        # optional — email for weekly digest
  product_owner: string    # required — login of the PO
  scrum_master: string     # required — login of the SM
  slack_channel: string    # required — e.g. "#scraut-bot"
```

`product_owner` and `scrum_master` do not need to be in `members` (for external stakeholders), but typically are.

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
  enabled: boolean      # Enable visibility portal
  title: string         # Dashboard title
  public: boolean       # false = private GitHub Pages (requires Team/Enterprise plan)
  refresh_minutes: int  # How often board state syncs from text files
```

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
