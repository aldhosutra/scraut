# Scraut — Claude Code Context

> This file is read automatically by Claude Code at the start of every session.
> It contains the non-negotiable rules and architecture for Scraut.
> **Always read this file before writing any code.**

---

## What is Scraut

Scraut is a fully automated, text-file-first Scrum system built on GitHub
infrastructure. Every piece of data lives in markdown files committed to this
repository. GitHub Actions workflows read those files, call an LLM when needed,
and write back summaries and derived views.

**One sentence:** text files in, automation out.

---

## Non-negotiable architecture rules

These rules must never be violated, regardless of what seems convenient.

### 1. Text files are the ONLY source of truth
The GitHub Projects board is a **derived view**. It is regenerated from text
files by `scripts/visibility/sync_board.py`. Never write code that reads the
board to make decisions — always read the text files.

### 2. Never overwrite human-edited files
Use `create_if_not_exists()` from `scripts/utils/file_utils.py` for any file
a human might write. Use `atomic_write()` only for bot-generated files.
Bot-generated files always start with `<!-- BOT-GENERATED -->`.

### 3. One file per contributor — zero git conflicts
Standup files: `sprint-N/standup/YYYY-MM-DD/[login].md`
Retro files:   `sprint-N/retrospective/[login].md`
One human = one file. Bots write to `summary/`, `review/`, `insights/`, `portal/`.

### 4. Bot commits always include `[skip ci]`
Every `git commit` message from a script or workflow must end with `[skip ci]`
to prevent infinite workflow loops. Without this, a bot commit triggers another
workflow, which triggers another commit, infinitely.

### 5. LLM is called only for language tasks
Pattern detection, velocity calculation, file routing, issue labelling logic —
these are deterministic scripts. LLM is only called when the task genuinely
requires language understanding: summarisation, sentiment, narrative generation,
suggestion drafting, planning session questions.

### 6. Every script accepts `--dry-run` and `--config`
`--dry-run`: print proposed changes, make no writes or API calls
`--config`:  path to an alternative `scraut.yml` (default: `./scraut.yml`)

---

## Three file zones

| Zone | Who writes | Examples | Rule |
|------|-----------|---------|------|
| Human input | Humans (GitHub pencil) | `standup/DATE/login.md` | `create_if_not_exists` only |
| Agent input | AI agents | `standup/DATE/agent-*.md` | Same format as humans |
| Bot-generated | GitHub Actions | `summary/`, `review/`, `insights/`, `portal/` | `atomic_write` OK |

---

## Core utilities (always use these, never reimplement)

```python
from scripts.utils.config import load_config, get_repo_root, get_current_sprint, get_team_logins
from scripts.utils.file_utils import atomic_write, create_if_not_exists, read_file, extract_section
from scripts.utils.date_utils import get_sprint_dates, is_working_day, days_until_sprint_end
from scripts.github.api import get_github_client, get_issues, get_sp_from_issue
from scripts.github.projects import get_project_id, get_project_items, get_field_ids
from scripts.llm.client import complete, complete_json
from scripts.notifications.slack_post import post_to_slack, send_slack_dm
```

---

## Story point labels

Issues use `sp:1`, `sp:2`, `sp:3`, `sp:5`, `sp:8`, `sp:13` labels.
`get_sp_from_issue(issue)` returns the integer value. Returns 0 if no label.

---

## Sprint labels

Each sprint issue has label `sprint-{N:02d}` (e.g. `sprint-01`, `sprint-14`).
Also `in-sprint` while active. `deferred` when rolled over to next sprint.

---

## scraut.yml location

Always at repo root. Loaded via `load_config()` which caches after first call.
`current_sprint` is the authoritative sprint number. Incremented by `close_sprint.py`.

---

## Implementation files

The full implementation spec lives in `scraut-implementation/`:

| File | What it implements |
|------|--------------------|
| `00-ROADMAP.md` | Global file tree, schemas, canonical formats — read first in every session |
| `01-FOUNDATION.md` | Config system, GitHub wrappers, label setup, issue templates |
| `02-CEREMONIES.md` | LLM client, all 5 Scrum ceremonies, standup system, burndown charts |
| `03-MILESTONE-PLANNING.md` | Milestone decompose, planning session, roadmap, health check |
| `04-REPO-SYNC.md` | Connected repo sync, activity fetch, standup pre-fill |
| `05-VISIBILITY-PORTAL.md` | Board sync, state inference, GitHub Pages portal, morning DMs |
| `06-SUGGESTIONS.md` | 6 detectors, suggestion lifecycle, measurement loop |
| `07-AGENT-MODE.md` | AI agent orchestrator, checkpoints, deadlock detection |
| `08-SETUP-CLI.md` | `npx create-scraut`, `pip install scraut`, web form, GitHub App |
| `09-COMPLETIONS.md` | All missing scripts and workflows from gaps audit |
| `10-TESTING.md` | Full pytest suite, mocks, fixtures, CI workflow |

---

## How to implement a phase

1. Read `scraut-implementation/00-ROADMAP.md` for global context
2. Read the specific phase file (e.g. `scraut-implementation/02-CEREMONIES.md`)
3. Create every file at the exact path shown — do not rename or reorganise
4. Scripts go in `scripts/`, workflows go in `.github/workflows/`
5. After implementing, check every item in the "Done Criteria" section
6. Run `pytest tests/unit/` if test files exist

---

## What NOT to do

- Do not create `scraut/` or `src/` subdirectories — all scripts are flat under `scripts/`
- Do not use `print()` for errors — use `logging.error()`
- Do not hardcode repo names — always read from config or `GITHUB_REPOSITORY` env var
- Do not make real API calls in tests — use mocks from `tests/mocks/`
- Do not commit without `[skip ci]` in bot-generated commit messages
- Do not ask for confirmation on individual files — implement everything in the phase
