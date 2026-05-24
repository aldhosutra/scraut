# Scraut — Scrum Automation
## Master Implementation Roadmap

> **For Claude Code**: Read this file first and in full before implementing any phase.
> Each phase file is a self-contained implementation spec. Execute phases in order.
> Do not skip phases. Do not combine phases into a single session.

---

## Project Vision

Scraut is a fully automated, text-first Scrum system built entirely on GitHub infrastructure.
It works for human teams, AI agent teams, and hybrid teams using the same file format.

**Core philosophy:**
- **Text files are the source of truth** — not a database, not a board, not a UI
- **GitHub is the infrastructure** — Actions for automation, Issues for ceremonies, Projects for visibility
- **LLMs handle language** — summaries, suggestions, estimation hints, planning
- **Scripts handle logic** — velocity, burndown, state derivation, report generation
- **The board is a derived mirror** — never edited directly; always regenerated from text files
- **One file per contributor** — humans and agents each own their own files; zero conflicts possible
- **Universal interface** — humans use the GitHub pencil icon; agents use the GitHub API; same format

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Version control | Git + GitHub |
| Automation | GitHub Actions (YAML workflows) |
| Scripting | Python 3.11+ |
| LLM | Anthropic Claude (claude-sonnet-4-6) — swappable to OpenAI / Ollama |
| Charts | matplotlib + Pillow (SVG/PNG output) |
| GitHub API | PyGitHub + raw GitHub REST API |
| GitHub Projects | GitHub GraphQL API v4 |
| Slack | Incoming Webhooks + Slack Web API |
| Notifications | GitHub Actions + Slack API |
| CLI tool | Python Click (pip install scraut) |
| Setup wizard | Node.js + Inquirer (npx create-scraut) |
| Stakeholder portal | Static HTML/CSS (published to GitHub Pages) |
| Web form | Vanilla HTML/JS + Cloudflare Worker or Vercel Edge Function |

---

## Repository Structure (complete)

```
.github/
├── workflows/
│   ├── sprint-planning.yml         # Ceremony: sprint start
│   ├── daily-standup.yml           # Ceremony: 9am weekdays
│   ├── backlog-grooming.yml        # Ceremony: mid-sprint
│   ├── sprint-review.yml           # Ceremony: sprint end
│   ├── sprint-retrospective.yml    # Ceremony: day after sprint end
│   ├── issue-triage.yml            # Event: issues.opened
│   ├── pr-linker.yml               # Event: pull_request.opened
│   ├── pr-close-stories.yml        # Event: pull_request.closed + merged
│   ├── estimation-tally.yml        # Event: issue_comment.created (emoji votes)
│   ├── sprint-plan-pr.yml          # Event: pull_request merged (planning PRs)
│   ├── milestone-planning.yml      # Event: push to milestones/**
│   ├── milestone-respond.yml       # Event: issue_comment (planning sessions)
│   ├── repo-sync.yml               # Scheduled: 8am daily
│   ├── template-reset.yml          # Scheduled: 1am daily
│   ├── morning-notification.yml    # Scheduled: 7:55am weekdays
│   ├── visibility-engine.yml       # Event: push + scheduled 30min
│   ├── portal-publish.yml          # Event: push (publishes GitHub Pages)
│   ├── weekly-digest.yml           # Scheduled: Monday 8am
│   ├── suggestion-detect.yml       # Scheduled: sprint end
│   ├── suggestion-measure.yml      # Scheduled: 2 sprints post-implementation
│   ├── dod-check.yml               # Event: issues.closed
│   ├── incident-to-backlog.yml     # Event: push to incidents/**
│   └── agent-orchestrator.yml      # Scheduled: when agent mode enabled
├── ISSUE_TEMPLATE/
│   ├── user-story.md
│   ├── bug.md
│   ├── task.md
│   ├── spike.md
│   └── config.yml
└── pull_request_template.md

scripts/
├── llm/
│   ├── client.py                   # LLM API wrapper (swappable provider)
│   └── prompts.py                  # All LLM prompts (centralised)
├── github/
│   ├── api.py                      # GitHub REST API wrapper
│   └── projects.py                 # GitHub Projects GraphQL API
├── sprint/
│   ├── create_sprint.py            # Create milestone + sprint folder structure
│   ├── close_sprint.py             # Close milestone + archive + velocity
│   ├── assign_to_sprint.py         # Move issues to sprint milestone
│   └── calculate_velocity.py       # Velocity from closed issues + sp labels
├── standup/
│   ├── reset_templates.py          # Create daily standup files (create-if-not-exists)
│   ├── generate_summary.py         # LLM: consolidate all standup files → digest
│   └── prefill_from_activity.py    # Pre-fill Yesterday section from repo activity
├── backlog/
│   ├── triage_issue.py             # LLM: suggest labels + story points on new issue
│   ├── prioritize_backlog.py       # LLM: rank unlabelled issues
│   └── dod_check.py                # Check issue against Definition of Done
├── reports/
│   ├── burndown_chart.py           # Generate burndown SVG/PNG (matplotlib)
│   ├── velocity_chart.py           # Generate velocity chart
│   └── sprint_summary.py           # Collect sprint stats for LLM narrative
├── repo_sync/
│   ├── fetch_activity.py           # Fetch commits/PRs/reviews from connected repos
│   ├── compute_delta.py            # Delta: today vs yesterday activity
│   └── prefill_standups.py         # Write pre-filled standup templates from activity
├── milestone/
│   ├── decompose.py                # LLM: milestone → epics → stories → tasks
│   ├── generate_roadmap.py         # LLM: sprint-by-sprint roadmap from decomposition
│   ├── health_check.py             # Compare planned vs actual; forecast ETA
│   └── planning_session.py         # Parse /answer commands from issue comments
├── visibility/
│   ├── derive_state.py             # Infer issue state from text artifacts
│   ├── sync_board.py               # Update GitHub Projects board via GraphQL
│   └── generate_portal.py          # Render static HTML stakeholder portal
├── suggestions/
│   ├── detectors.py                # All 6 pattern detectors (script-based)
│   ├── generate_suggestion.py      # LLM: draft suggestion from evidence
│   └── measure.py                  # Re-run detector; compare before/after
├── notifications/
│   ├── morning_dm.py               # Send morning Slack DM with standup link
│   ├── slack_post.py               # Post message to Slack channel
│   ├── send_email.py               # Send HTML email via SMTP
│   └── weekly_digest.py            # Generate + send weekly stakeholder digest
├── agents/
│   ├── orchestrator.py             # Orchestrator agent: read roadmap, assign tasks
│   ├── checkpoint.py               # Human checkpoint: detect and escalate
│   └── deadlock_detect.py          # Detect agent coordination deadlocks
└── utils/
    ├── config.py                   # Load and validate scraut.yml
    ├── file_utils.py               # File read/write helpers
    └── date_utils.py               # Sprint date calculations

# Sprint data (created dynamically)
sprint-01/
├── meta.md                         # Sprint manifest (auto-generated at sprint start)
├── standup/
│   ├── 2026-05-23/                 # Daily folder (created by template-reset workflow)
│   │   ├── alice.md                # Human standup (pencil icon or web form)
│   │   ├── bob.md
│   │   └── agent-backend.md        # AI agent standup (same format)
│   └── summary/                    # BOT-ONLY: never human-edited
│       └── 2026-05-23.md           # LLM-generated team digest
├── retrospective/
│   ├── alice.md                    # Human retro (pencil icon)
│   ├── bob.md
│   └── summary.md                  # BOT-ONLY: LLM synthesis
├── review/
│   └── sprint-review.md            # BOT-ONLY: auto-generated from GitHub data + LLM
├── grooming/
│   └── backlog-ideas.md            # Append-only: team adds ideas freely
├── decisions/
│   └── 2026-05-23.md               # Team decisions from meetings
├── incidents/
│   └── 2026-05-23-api-outage/
│       ├── timeline.md             # Human writes: what happened
│       └── action-items.md         # BOT: LLM extracts + creates GitHub issues
├── adr/
│   └── 001-use-redis.md            # Architecture Decision Records
└── code/                           # BOT-ONLY: from repo sync
    └── 2026-05-23/
        ├── activity.json           # Machine-readable activity data
        ├── activity.md             # Human-readable activity log
        └── delta.md                # What changed vs yesterday

milestones/
└── m01-auth-system/
    ├── milestone.md                # Human writes: goal + success criteria
    ├── planning-session.md         # BOT: Q&A log from interactive planning
    ├── breakdown.json              # BOT: structured decomposition (machine-readable)
    ├── breakdown.md                # BOT: human-readable epic/story list
    ├── roadmap.md                  # BOT: sprint-by-sprint plan
    ├── constraints.md              # BOT: captured planning answers
    └── health/
        ├── sprint-01.md            # BOT: post-sprint health report
        └── forecast.md             # BOT: rolling ETA (overwritten each sprint)

suggestions/
├── active/
│   └── s001-pr-review-bottleneck.md
├── implemented/
│   └── s002-standup-reminder.md
└── resolved/
    └── s003-velocity-estimation.md

insights/                           # BOT-ONLY: cross-sprint analysis
├── velocity-trends.md
├── blocker-patterns.md
└── team-health.md

team/
├── capacity.md                     # Who is OOO and when
└── oncall.md                       # On-call rotation

okr/
└── 2026-Q2.md                      # Organizational objectives

customer/
└── feedback.md                     # Weekly digest from support/sales

knowledge/                          # BOT: extracted from PR descriptions
└── 2026-05.md

portal/                             # BOT-ONLY: auto-generated GitHub Pages
├── index.html
├── style.css
└── data.json

scraut.yml                          # Global configuration
requirements.txt                    # Python dependencies
.gitignore
```

---

## Global Configuration Schema (`scraut.yml`)

```yaml
# scraut.yml — Scraut Global Configuration
# All fields documented. Minimal required: sprint, team.members, llm.provider

sprint:
  length_days: 14                   # Sprint duration in calendar days
  start_day: monday                 # Day of week sprints start
  start_time: "09:00"               # Local time for ceremony triggers
  timezone: "Asia/Jakarta"          # IANA timezone (affects cron schedules)
  capacity_buffer: 0.85             # Plan to 85% of historical velocity (safety)
  current_sprint: 1                 # Auto-incremented by close_sprint.py

team:
  members:
    - login: alice-gh               # GitHub username (exact match)
      display: Alice                # Human-readable name
      role: developer               # developer | product_owner | scrum_master
      slack_id: U012AB3CD           # Slack member ID (for DMs)
      email: alice@example.com      # For email digest
    - login: bob-codes
      display: Bob
      role: scrum_master
      slack_id: U034EF5GH
      email: bob@example.com
  product_owner: alice-gh           # Login of PO (gets backlog approval step)
  scrum_master: bob-codes           # Login of SM (gets suggestion system alerts)
  slack_channel: "#scraut-bot"      # Main channel for ceremony posts

ceremonies:
  planning: true
  standup: true
  grooming: true
  review: true
  retrospective: true
  estimation: true                  # Emoji reaction-based story point voting

definition_of_done:
  - Tests written for new functionality
  - PR reviewed by at least one team member
  - Acceptance criteria mentioned in PR description
  - No open review comments
  - CI passing

repos:                              # Connected GitHub repos for code activity sync
  - name: product-api               # Display name
    url: acme/product-api           # org/repo format
    branch_filter: [main, develop]  # Only watch these branches
    enabled: true
  - name: product-frontend
    url: acme/frontend
    branch_filter: [main]
    enabled: true

llm:
  provider: anthropic               # anthropic | openai | ollama
  model: claude-sonnet-4-6          # Model name (provider-specific)
  max_tokens: 1000                  # Per-call token limit
  cost_controls:
    max_daily_tokens: 100000        # Fail-safe daily limit
    batch_where_possible: true      # Batch multiple issues in one call

agents:
  enabled: false                    # Enable AI agent coordination mode
  roles:
    - id: orchestrator
      type: orchestrator
      enabled: false
    - id: agent-backend
      type: specialist
      specialty: backend
      enabled: false
    - id: agent-frontend
      type: specialist
      specialty: frontend
      enabled: false
    - id: agent-test
      type: specialist
      specialty: testing
      enabled: false
  human_checkpoints:
    - event: sprint_boundary        # Pause before each new sprint
    - event: milestone_eta_slip     # ETA drifts > 1 sprint from target
    - event: escalation_count       # >2 unresolved agent escalations
    - event: agent_failure          # Any agent errors repeatedly
  autonomy_level: supervised        # supervised | semi-auto | full-auto

notifications:
  slack_webhook: ""                 # Set via SLACK_WEBHOOK secret
  morning_dm: true                  # Daily standup link DM at 7:55am
  weekly_email: false               # Weekly email digest
  stakeholder_emails: []            # Email list for weekly digest

portal:
  enabled: true
  title: "Team Dashboard"
  public: true                      # false = private GitHub Pages
  refresh_minutes: 30               # How often board syncs from artifacts

suggestions:
  enabled: true
  min_evidence_count: 3             # Min pattern occurrences before suggesting
  measurement_sprints: 2            # Sprints after implementation to measure
```

---

## GitHub Secrets Required

Set these in **Settings → Secrets and variables → Actions** before running any workflow.

| Secret | Description | Required |
|--------|-------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | Yes (if provider=anthropic) |
| `OPENAI_API_KEY` | OpenAI API key | Yes (if provider=openai) |
| `SLACK_WEBHOOK` | Slack Incoming Webhook URL | For channel posts |
| `SLACK_BOT_TOKEN` | Slack Bot Token (xoxb-...) | For personal DMs |
| `SCRAUT_GITHUB_TOKEN` | PAT with repo:read for connected repos | For repo sync |
| `SMTP_HOST` | SMTP server hostname | For email digest |
| `SMTP_PORT` | SMTP port (usually 587) | For email digest |
| `SMTP_USER` | SMTP username/email | For email digest |
| `SMTP_PASS` | SMTP password | For email digest |
| `PORTAL_TOKEN` | Token for web form submissions | For non-dev web form |

---

## Labels to Create

Run `scripts/setup/create_labels.py` after phase 1 to create all labels.

```
Story points: sp:1, sp:2, sp:3, sp:5, sp:8, sp:13
Type:         story, bug, task, spike, chore
Status:       in-sprint, in-review, blocked, escalate:human
Priority:     p:high, p:medium, p:low
Sprint:       sprint-01, sprint-02, sprint-03 ... (created dynamically)
Ceremony:     standup, retrospective, sprint-review, sprint-planning
Agent:        agent-assigned, agent-blocked
DoD:          dod:pending, dod:approved
```

---

## Implementation Phases

| Phase | File | Builds | Depends On |
|-------|------|--------|-----------|
| 1 | `01-FOUNDATION.md` | Repo skeleton, config system, GitHub API wrappers, issue templates, label setup | None |
| 2 | `02-CEREMONIES.md` | 5 Scrum ceremonies, LLM client, standup system, reports, estimation ceremony, planning PR | Phase 1 |
| 3 | `03-MILESTONE-PLANNING.md` | Milestone format, decomposition, interactive planning session, roadmap generator, health check | Phase 1, 2 |
| 4 | `04-REPO-SYNC.md` | Connected repo activity fetch, delta analysis, standup pre-fill from commits | Phase 1, 2 |
| 5 | `05-VISIBILITY-PORTAL.md` | Board sync, state inference, stakeholder portal, weekly digest | Phase 1, 2, 4 |
| 6 | `06-SUGGESTIONS.md` | 6 pattern detectors, suggestion lifecycle, measurement loop | Phase 1, 2, 3, 5 |
| 7 | `07-AGENT-MODE.md` | AI agent coordination, orchestrator, checkpoints, deadlock detection | Phase 1–6 |
| 8 | `08-SETUP-CLI.md` | Setup CLI (npx create-scraut), GitHub App, non-dev web form, scraut CLI tool | Phase 1–7 |

---

## Global Python Conventions

- All scripts accept `--dry-run` flag (prints actions without executing)
- All scripts accept `--config` flag pointing to `scraut.yml` (default: repo root)
- All scripts log to stdout using Python `logging` at INFO level
- All scripts return exit code 0 on success, 1 on error
- All GitHub API calls are wrapped in retry logic (3 attempts, exponential backoff)
- All LLM calls are wrapped in try/except with fallback to rule-based output
- All file writes use atomic patterns (write to temp, rename to final)
- All bot commits include `[skip ci]` to avoid triggering workflows

## Global Workflow Conventions

- All workflows run on `ubuntu-latest`
- All workflows use `actions/checkout@v4`
- Python version: `3.11`
- All workflows install dependencies: `pip install -r requirements.txt`
- All workflows load config: `python scripts/utils/config.py --validate`
- Bot commit author: `Scraut Bot <scraut-bot@noreply.github.com>`

## File Zone Rules (CRITICAL — enforce in all code)

| Zone | Path Pattern | Who Writes | Who Reads |
|------|-------------|------------|-----------|
| Human input | `sprint-N/standup/date/[name].md` | Human only | Bot, LLM, agents |
| Agent input | `sprint-N/standup/date/agent-*.md` | Agent only | Bot, LLM, humans |
| Bot-generated | `sprint-N/*/summary/`, `sprint-N/review/`, `sprint-N/code/`, `insights/`, `portal/` | Bot only | Humans, agents |
| Shared append-only | `sprint-N/grooming/`, `sprint-N/decisions/`, `customer/feedback.md` | Everyone (append) | Bot, humans |
| Config | `scraut.yml`, `team/`, `okr/` | Human only | Bot, agents |

---

## Standup File Format (canonical — used by humans AND agents)

```markdown
# Standup — [Display Name]
<!-- 
  Sprint: sprint-NN
  Date: YYYY-MM-DD
  Author: github-login | agent-role
  Generated: [timestamp if bot-prefilled] | manual
-->

## Yesterday
- [What was completed, with issue/PR references where available]
- [e.g. Merged PR #89: "Refactor auth module" — closes #42]

## Today
- [What is planned for today]
- [e.g. Start issue #46: "Session management"]

## Blockers
- [Anything blocking progress — Scraut tracks these automatically]
- [Or: None]

## Notes
- [Optional: availability, context, anything relevant]

<!-- AGENT ONLY SECTION — humans leave this block out -->
## Agent State
- Tasks completed this sprint: N of M assigned
- Velocity: X sp delivered of Y sp claimed  
- CI status: ✅ | ⚠️ | 🔴
- Last commit: [sha] at [timestamp]
- Escalation needed: [yes/no — if yes, explain]
```

---

## Suggestion File Format (canonical)

```markdown
# S[NNN]: [Title]

**Status:** proposed | accepted | implemented | measured | resolved
**Priority:** High | Medium | Low
**Category:** Process | Capacity | Quality | Milestone | Team Health
**Detected:** YYYY-MM-DD
**Detector:** [BlockerFrequencyDetector | VelocityDropDetector | etc.]
**Evidence count:** N mentions across M sprints
**Est. impact:** [description]

---

## Evidence trail
| Sprint | Date | File | Quote |
|--------|------|------|-------|
| Sprint N | YYYY-MM-DD | path/to/file.md | "exact quote" |

## Suggested actions
**Option A (Recommended):** [specific action]
**Option B:** [alternative]

## Expected impact
- [Metric]: [current] → [expected]

## How Scraut will measure (auto-scheduled Sprint N+2)
- Re-runs [DetectorName]
- Expects: [specific measurable outcome]

## Baseline metrics (captured at detection time)
```json
{ "metric": "value" }
```

---
*Reply: `/accept A` · `/accept B` · `/modify [notes]` · `/decline [reason]`*
```

---

## Sprint Meta File Format (canonical)

```markdown
# Sprint [N]
- Period: YYYY-MM-DD → YYYY-MM-DD (N working days)
- Goal: [Sprint goal — agreed in planning]
- Team: [comma-separated display names]
- Committed: [X] story points across [Y] issues
- Milestone: [milestone link if applicable]
- Capacity note: [any OOO or reduced capacity]

## Issues in sprint
| Issue | Title | Epic | SP | Assignee |
|-------|-------|------|----|---------|
| #101 | [title] | [epic] | N | [name] |
```

---

## Milestone File Format (canonical)

```markdown
# Milestone: [Name]

## Goal
[1–3 sentences describing what this milestone achieves]

## Success criteria
- [ ] [Measurable outcome 1]
- [ ] [Measurable outcome 2]
- [ ] [Measurable outcome 3]

## Out of scope
- [Explicitly excluded items — prevents scope creep]

## Known risks
- [Risk 1]: [mitigation approach]
- [Risk 2]: [mitigation approach]

## Constraints
<!-- The interactive planning session populates this section automatically.
     Do not edit manually after the session is complete. -->
```

---

## Activity File Format (`activity.json` — machine-readable)

```json
{
  "date": "2026-05-23",
  "repos": ["acme/product-api", "acme/frontend"],
  "team_filter": ["alice-gh", "bob-codes"],
  "generated_at": "2026-05-23T08:00:00Z",
  "members": {
    "alice-gh": {
      "commits": [
        {"sha": "abc1234", "message": "Fix JWT expiry", "branch": "feature/auth", "repo": "product-api"}
      ],
      "prs_opened": [],
      "prs_merged": [
        {"number": 89, "title": "Refactor auth module", "repo": "product-api", "closes_issues": [42]}
      ],
      "prs_reviewed": [
        {"number": 91, "title": "Rate limiting", "repo": "product-api", "review_type": "approved"}
      ],
      "ci_failures": []
    }
  },
  "team_summary": {
    "prs_opened": 1,
    "prs_merged": 2,
    "prs_reviewed": 3,
    "total_commits": 11,
    "aging_prs": [{"number": 88, "age_days": 4, "repo": "product-api"}],
    "ci_status": "green"
  }
}
```

---

## Board State (GitHub Projects custom fields)

Create these custom fields in GitHub Projects:

| Field | Type | Options |
|-------|------|---------|
| Status | Select | Backlog, Ready, In Progress, Review, Testing, Done |
| Agent | Text | github login of assigned agent |
| Health | Select | on-track, watch, blocked |
| SP Remaining | Number | story points remaining |
| Last Activity | Date | timestamp of most recent file write |
| Sprint | Text | sprint-NN |
| Blocker | Text | extracted blocker description |

---

## How to Use These Files with Claude Code

1. Open Claude Code in the Scraut repository root (empty or new repo)
2. Pass `00-ROADMAP.md` first: `claude < 00-ROADMAP.md`
3. Then execute phases in order, one session per phase:
   ```
   claude < 01-FOUNDATION.md
   claude < 02-CEREMONIES.md
   ...
   ```
4. After each phase, review the generated files and run the done criteria checks
5. Commit each phase separately with message: `feat: scraut phase N — [phase name]`
6. Do NOT skip phases — each phase builds on the previous

---

*End of master roadmap. Proceed to `01-FOUNDATION.md`.*
