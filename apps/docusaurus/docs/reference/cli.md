---
sidebar_position: 1
---

# CLI Reference

The `scraut` CLI provides quick terminal shortcuts for common daily tasks. Install it once, use it every day.

---

## Installation

```bash
pip install -r apps/automation/requirements.txt
```

The `scraut` command becomes available after installation.

---

## Commands

### `scraut init`

Interactive first-time setup wizard.

```bash
scraut init
```

**What it does:**
- Asks 9 questions about your team configuration
- Writes `workspace/scraut.yml`
- Creates `workspace/` and `.scraut/` directory skeletons
- Scaffolds template files (standup, retro, meta, capacity, OKR, customer feedback, milestones)
- Optionally creates GitHub labels (if `GITHUB_TOKEN` is set)
- Prints the secrets checklist and next steps

**Example session:**
```
====================================================
  Scraut Setup Wizard
====================================================
GitHub repository (org/repo): myorg/my-repo
Team member GitHub logins (comma-separated): alice,bob
Product owner login [alice]: alice
Scrum master login [alice]: bob
Slack channel [#scraut-bot]: #scraut-bot
Sprint length in days [14]: 14
Timezone (IANA format, e.g. UTC, Asia/Jakarta) [UTC]: Asia/Jakarta
LLM provider (anthropic, openai, gemini, ollama) [anthropic]: anthropic
Slack webhook URL (optional, Enter to skip):
```

---

### `scraut standup`

Opens today's standup file in GitHub's web editor.

```bash
scraut standup
# or, to just print the URL:
scraut standup --no-browser
```

**What it does:**
1. Reads `workspace/scraut.yml` to get current sprint number
2. Detects your GitHub login from the authenticated token
3. Constructs the file URL: `github.com/org/repo/edit/main/workspace/sprint/NN/standup/DATE/login.md`
4. Opens it in your browser (or prints the URL with `--no-browser`)

**Options:**
```
--browser / --no-browser   Open in browser (default) or print URL
```

---

### `scraut status`

Shows current sprint health at a glance.

```bash
scraut status
```

**Output includes:**
- Sprint number and goal (from `workspace/sprint/NN/meta.md`)
- Story point progress
- Active milestone health (from `.scraut/milestones/*/health/forecast.md`)
- Active suggestions (from `.scraut/suggestions/active/`)

**Example output:**
```
==================================================
Sprint 01 Status
==================================================
# Sprint 1
- Period: 2026-05-25 → 2026-06-07
- Goal: Deliver user authentication and basic dashboard
- Committed: 34 story points

Milestone: v1.0
  Status: On track
  Forecast: 2026-08-24

2 active suggestion(s):
  • Blockers are going unresolved for > 2 days
  • PR review cycle averaging 4 days

==================================================
```

---

### `scraut blocker`

Adds a blocker to today's standup file.

```bash
scraut blocker "Waiting for API credentials from platform team — blocked on #28"
```

**What it does:**
1. Finds today's standup file for your login
2. Replaces `None` in the `## Blockers` section with your text
3. Saves the file locally (you still need to commit and push)

**Example:**
```bash
scraut blocker "Design mockup for profile page needed before I can continue #31"
# Output: ✓ Blocker added to alice.md
#   'Design mockup for profile page needed before I can continue #31'
#
# Remember to commit and push: git add . && git commit -m 'standup: blocker [skip ci]' && git push
```

---

### `scraut sync`

Syncs the workspace folder structure with `workspace/scraut.yml`. Run this after any config change that affects workspace layout.

```bash
scraut sync
# preview without writing anything:
scraut sync --dry-run
```

**What it does:**
- Creates today's standup file for any team member who doesn't have one yet
- Creates a retro file for any member who doesn't have one for the current sprint
- Creates sprint folder structure (`standup/`, `retrospective/`, `grooming/`, `decisions/`, `adr/`) if it doesn't exist
- Creates `.scraut/sprint/NN/` output dirs if missing
- Creates `meta.md` and `grooming/backlog-ideas.md` if missing

**What it does NOT do:**
- Never overwrites files that already exist (safe to run repeatedly)
- Does not create GitHub milestones (use the sprint-planning workflow for that)
- Does not require `GITHUB_TOKEN`

**Common scenarios:**

```bash
# Added a new team member to scraut.yml mid-sprint
scraut sync
# → creates their standup file for today and their retro file

# Just changed current_sprint in scraut.yml after sprint transition
scraut sync
# → creates the sprint/NN/ folder structure for the new sprint number

# Check what sync would do without actually doing it
scraut sync --dry-run
```

**Options:**
```
--dry-run   Print what would be created without writing any files
```

---

### `scraut sprint`

Sprint management shortcuts.

```bash
scraut sprint status              # show current sprint number and date range
scraut sprint scaffold            # alias for scraut sync
scraut sprint repad <N>           # widen sprint folder padding to N digits
scraut sprint repad <N> --dry-run # preview what repad would rename
```

**`scraut sprint status` output:**
```
  Current sprint: 001
  Period:         2026-06-09 → 2026-06-22
  Folder:         workspace/sprint/001/
  Padding:        3 digits
  Today:          2026-06-10
```

#### `scraut sprint repad`

Widens the zero-padding width used for sprint folder names and renames all existing `workspace/sprint/NNN/` and `.scraut/sprint/NNN/` directories to the new width.

```bash
# Preview without making changes
scraut sprint repad 4 --dry-run

# Apply — renames sprint/001/ → sprint/0001/, etc.
scraut sprint repad 4
```

**Validation rules:**
- New padding must be **greater than** the current padding (widening only — narrowing breaks lexicographic sort order)
- New padding must fit the current sprint number (e.g. sprint 1000 requires at least 4 digits)

After running `repad`, Scraut prints the GitHub CLI commands to rename the matching sprint labels (e.g. `sprint-001` → `sprint-0001`) and the git commit command to push the renamed folders.

---

### `scraut velocity`

Shows sprint velocity data.

```bash
scraut velocity
# or for a specific sprint:
scraut velocity --sprint 3
```

**Options:**
```
--sprint INTEGER   Sprint number (default: current sprint)
```

**Example output:**
```
Sprint 03: 28 / 34 sp (82%)
Rolling average: 30 sp/sprint (σ=4, 3 sprints sampled)
```

**What it shows:**
- Completed vs. planned story points for the sprint
- Completion rate percentage
- Rolling average velocity (last 5 sprints)
- Standard deviation (consistency metric)
- Number of sprints sampled

---

## Global options

```bash
scraut --version    # Print the installed version
scraut --help       # Show help for any command
scraut COMMAND --help  # Show help for a specific command
```

---

## Running scripts directly

All automation scripts also accept `--help`, `--dry-run`, and `--config` flags:

```bash
# Preview what standup summary would do without making changes
python apps/automation/scraut/scrum/standup/generate_summary.py --dry-run

# Use an alternative config file
python apps/automation/scraut/scrum/sprint/create_sprint.py \
  --config /path/to/alt-scraut.yml \
  --sprint 2 \
  --repo myorg/my-repo

# Preview sprint planning without creating issues
python apps/automation/scraut/scrum/sprint/plan_sprint.py \
  --dry-run \
  --sprint 2 \
  --repo myorg/my-repo
```
