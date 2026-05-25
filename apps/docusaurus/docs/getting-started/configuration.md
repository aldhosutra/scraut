---
sidebar_position: 3
---

# Configuration

All configuration lives in `workspace/scraut.yml`. This file is the single source of truth for your team settings, sprint configuration, and feature toggles.

---

## Full annotated example

```yaml
# workspace/scraut.yml

sprint:
  length_days: 14         # Sprint duration in calendar days (7, 14, or 21)
  start_day: monday       # Day of week sprints begin
  start_time: "09:00"     # Local time for ceremony triggers (HH:MM, 24h)
  timezone: "Asia/Jakarta" # IANA timezone — affects all cron schedules
  capacity_buffer: 0.85   # Plan to 85% of historical velocity (safety margin)
  current_sprint: 1       # Auto-incremented by close_sprint.py — don't edit manually

team:
  members:
    - login: alice          # GitHub username (exact case match)
      display: Alice Smith  # Human-readable name shown in summaries
      role: developer       # developer | product_owner | scrum_master — informational only
      slack_id: U0123456789 # Slack member ID (for morning DMs — see below)
      email: alice@example.com # For weekly email digest
    - login: bob
      display: Bob Jones
      role: developer
      slack_id: U9876543210
      email: bob@example.com
  product_owner: alice      # Informational — not used by automation today
  scrum_master: bob         # Informational — not used by automation today
  slack_channel: "#scraut-bot" # Main channel for ceremony posts

ceremonies:
  planning: true      # Sprint planning
  standup: true       # Daily standup summarisation
  grooming: true      # Mid-sprint backlog grooming
  review: true        # Sprint review
  retrospective: true # Sprint retrospective synthesis
  estimation: true    # Emoji reaction-based story point voting

definition_of_done:
  - Tests written for new functionality
  - PR reviewed by at least one team member
  - Acceptance criteria mentioned in PR description
  - No open review comments
  - CI passing

repos:
  # Connected repos for code activity sync (optional)
  - name: Backend API       # Display name
    url: myorg/backend-api  # org/repo format
    branch_filter: [main]   # Only watch these branches
    enabled: true

llm:
  provider: anthropic       # anthropic | openai | gemini | ollama
  model: claude-sonnet-4-6  # Model name — provider-specific (see LLM Providers)
  base_url: ""              # Optional: custom endpoint (Groq, DeepSeek, LM Studio, etc.)
  max_tokens: 1000          # Per-call output token limit
  cost_controls:
    max_daily_tokens: 100000  # Hard daily limit — workflows fail-safe beyond this
    batch_where_possible: true # Batch multiple issues in one LLM call

agents:
  enabled: false            # Set to true to activate Agent Mode
  # See Agent Mode docs for full agent configuration

notifications:
  slack_webhook: ""         # Set via SLACK_WEBHOOK secret — never put here directly
  morning_dm: true          # 7:55am DM with standup link
  weekly_email: false       # Monday 8am stakeholder email digest
  stakeholder_emails: []    # Email addresses for weekly digest

portal:
  enabled: true
  title: "My Team Dashboard"
  public: true              # false = private GitHub Pages (requires auth)
  refresh_minutes: 30       # How often the board syncs from text files

suggestions:
  enabled: true
  min_evidence_count: 3     # Min occurrences before pattern becomes a suggestion
  measurement_sprints: 2    # Sprints to measure impact after implementation

paths:
  workspace: workspace      # Root for human-editable files
  scraut: .scraut           # Root for bot-generated files
  portal: apps/portal       # Portal application path
```

---

## Team roles

Scraut has three configurable role fields in the `team` section: `members[].role`, `product_owner`, and `scrum_master`.

**Important: none of these fields currently change what automation runs.** All 28 workflows treat every team member the same — standup summaries include everyone, planning considers the full team, and any member with repo write access can manually trigger ceremonies from the Actions tab.

The fields exist as documentation of intent inside the config file, and as a foundation for future role-based features (routing escalations, priority decisions, etc.).

### `product_owner` and `scrum_master`

These fields accept a GitHub login. They can be:

- **Different people** — the typical Scrum setup
- **The same person** — works perfectly for small teams or solo founders running Scrum-of-one:
  ```yaml
  product_owner: alice
  scrum_master: alice
  ```
- **A person not in `members`** — allowed if your PO or SM is an external stakeholder who doesn't participate in standups

### `members[].role`

The `role` field on each team member (`developer`, `product_owner`, `scrum_master`) is purely a label used in LLM prompt context and generated summaries. It does not gate any action or notification.

---

## Finding your Slack member ID

The `slack_id` field enables personal morning DMs. To find it:

1. Open Slack, click on a team member's profile
2. Click **⋮ More** → **Copy member ID**
3. It looks like `U0123456789`

Without `slack_id`, morning DMs for that member are silently skipped (the rest of the system still works).

---

## Choosing a timezone

Use an IANA timezone string. Common examples:

| Region | Timezone |
|--------|----------|
| Jakarta / WIB | `Asia/Jakarta` |
| Singapore / SGT | `Asia/Singapore` |
| New York / ET | `America/New_York` |
| London / GMT | `Europe/London` |
| San Francisco / PT | `America/Los_Angeles` |
| UTC | `UTC` |

The timezone affects when scheduled workflows run. For example, with `Asia/Jakarta` and `start_time: "09:00"`, the daily standup summary fires at 09:00 WIB (02:00 UTC).

---

## LLM provider selection

See [LLM Providers](../reference/llm-providers) for the full list of supported models and how to configure custom endpoints.

---

## What NOT to put in `scraut.yml`

- **Secrets** (API keys, tokens, webhook URLs): Always use GitHub Secrets
- **Slack webhook URL**: Use `SLACK_WEBHOOK` secret, leave `slack_webhook: ""` in the file
- **API keys**: Use `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc. as GitHub Secrets

---

Next: [GitHub Setup →](./github-setup)
