# Scraut — Claude Code Implementation Guide

How to turn the 11 implementation files into a working system using Claude Code.
Estimated total time: 6–8 hours across 8 sessions.

---

## Before you start (one-time, 10 minutes)

### 1. Create the GitHub repository

```bash
# Create a new empty repo on GitHub, then clone it
git clone https://github.com/YOUR-ORG/YOUR-REPO.git
cd YOUR-REPO
```

### 2. Copy all implementation files into the repo

```bash
# Copy the entire scraut-implementation/ folder into your repo root
cp -r /path/to/scraut-implementation/ .
```

Your repo should now look like:
```
YOUR-REPO/
├── CLAUDE.md                      ← Claude Code reads this automatically
└── scraut-implementation/
    ├── 00-ROADMAP.md
    ├── 01-FOUNDATION.md
    ├── ...
    └── 10-TESTING.md
```

### 3. Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

### 4. Start Claude Code from your repo root

```bash
cd YOUR-REPO
claude
```

> **Important:** Always start Claude Code from the repo root.
> It reads `CLAUDE.md` automatically on startup. You will see it say
> "Reading CLAUDE.md..." in the output.

---

## Session strategy: one phase per session

**Why one phase per session?**

Each phase produces 5–15 files. Claude Code's context fills up after about
8–10 complex file creations. If you give it two phases at once, it starts
conflating them, skipping items, or writing placeholder comments instead of
real code. One phase per session keeps Claude Code sharp and focused.

**Why not `/clear` mid-phase?**

The implementation files reference utilities from earlier in the same file
(e.g. `complete_json` is defined in the first half of Phase 2 and called in
the second half). Clearing mid-phase means Claude Code loses that context.
Always finish a phase before clearing.

**The rhythm for each session:**

```
1. Start Claude Code in repo root (CLAUDE.md auto-loaded)
2. Paste the phase prompt (from below)
3. Claude Code implements all files in the phase
4. You verify using the "Done Criteria" checklist in the phase file
5. git add . && git commit -m "feat: phase N complete [skip ci]"
6. Type /clear (or close and reopen Claude Code)
7. Start next session
```

---

## Phase 0 — Prep session (5 minutes)

**Do this once before Phase 1.**

```
Read CLAUDE.md and scraut-implementation/00-ROADMAP.md carefully.

Then do the following setup tasks:
1. Create the directory structure listed in the "Directory tree" section
2. Create an empty scraut.yml at the repo root using the schema from the
   "scraut.yml — full schema" section, populated with placeholder values
3. Create requirements.txt from the packages listed in the ROADMAP
4. Create .gitignore for Python projects

Do not implement any scripts yet. Just the skeleton structure and config files.
Commit with message: "chore: repo skeleton [skip ci]"
```

---

## Phase 1 — Foundation

**Session goal:** Config system, file utilities, GitHub API wrappers, label setup, issue templates.

```
Read CLAUDE.md, then read scraut-implementation/01-FOUNDATION.md.

Implement everything in that file in order:
- scripts/utils/config.py
- scripts/utils/file_utils.py
- scripts/utils/date_utils.py
- scripts/github/api.py
- scripts/github/projects.py
- scripts/setup/create_labels.py
- All .github/ISSUE_TEMPLATE/ files

After implementing:
1. Run: python scripts/setup/create_labels.py --dry-run --repo test/test
   (should print label list without errors)
2. Run: python -c "from scripts.utils.config import load_config; print('OK')"
3. Verify every item in the "Done Criteria" section of 01-FOUNDATION.md

Fix any import errors before finishing.
Commit: "feat: phase 1 - foundation [skip ci]"
```

---

## Phase 2 — Ceremonies

**Session goal:** LLM client, all 5 Scrum ceremonies, standup template system, estimation.

> ⚠️ Longest phase. Give Claude Code the full session for this one.

```
Read CLAUDE.md, then read scraut-implementation/02-CEREMONIES.md.

Implement everything in this file in order. It is a long file — do not skip
or stub any section. Key things to implement:

Scripts:
- scripts/llm/client.py and scripts/llm/prompts.py (implement FIRST)
- scripts/standup/reset_templates.py
- scripts/standup/generate_summary.py
- scripts/standup/generate_burndown.py
- scripts/sprint/calculate_velocity.py
- scripts/backlog/triage_issue.py
- scripts/backlog/dod_check.py
- scripts/notifications/slack_post.py

Workflows (.github/workflows/):
- standup-reset.yml
- standup-summary.yml
- sprint-planning.yml
- sprint-review.yml
- sprint-retrospective.yml
- estimation-tally.yml

After implementing:
1. Run: python -c "from scripts.llm.client import complete; print('LLM client OK')"
2. Run: python -c "from scripts.standup.reset_templates import STANDUP_TEMPLATE; print('OK')"
3. Verify Done Criteria in 02-CEREMONIES.md

Commit: "feat: phase 2 - ceremonies [skip ci]"
```

---

## Phase 3 + 4 — Milestone Planning + Repo Sync

**Session goal:** These two phases are short enough to do together.

```
Read CLAUDE.md.
Then read scraut-implementation/03-MILESTONE-PLANNING.md.
Implement all scripts and workflows in that file.

Then read scraut-implementation/04-REPO-SYNC.md.
Implement all scripts and workflows in that file.

The four scripts are:
- scripts/milestone/decompose.py
- scripts/milestone/planning_session.py
- scripts/milestone/generate_roadmap.py
- scripts/milestone/health_check.py
- scripts/repo_sync/fetch_activity.py
- scripts/repo_sync/compute_delta.py
- scripts/repo_sync/prefill_standups.py
- scripts/repo_sync/notify_aging_prs.py

After implementing:
1. Run: python -c "from scripts.milestone.health_check import score_sprint; print(score_sprint(26,20,[1,2,3],[1,2],100,40,3,8,1))"
   Should print a dict with 'composite', 'status', 'velocity', 'delivery', 'milestone', 'focus'
2. Verify Done Criteria in both 03 and 04 files

Commit: "feat: phases 3+4 - milestone planning and repo sync [skip ci]"
```

---

## Phase 5 — Visibility Portal

**Session goal:** Board sync, state inference, stakeholder portal, morning DMs, email digest.

```
Read CLAUDE.md, then read scraut-implementation/05-VISIBILITY-PORTAL.md.

Pay careful attention to scripts/visibility/derive_state.py — this is the
most complex script in the system. The inference rules must be implemented
exactly as specified (priority order matters):
  1. merged PR / closed issue → Done
  2. open PR → Review
  3. issue in Blockers section today → blocked
  4. agent standup → In Progress
  5. issue in Today section → In Progress
  6. ambiguous (LLM) → classify
  7. in sprint roadmap, no signals → Ready
  8. default → Backlog

After implementing:
1. Run: python -c "from scripts.visibility.derive_state import IssueState, VALID_COLUMNS; print(VALID_COLUMNS)"
2. Run: python scripts/visibility/generate_portal.py --dry-run
   (should not crash, even with no data)
3. Verify Done Criteria in 05-VISIBILITY-PORTAL.md

Commit: "feat: phase 5 - visibility portal [skip ci]"
```

---

## Phase 6 — Suggestion System

**Session goal:** All 6 detectors, suggestion lifecycle, measurement loop.

```
Read CLAUDE.md, then read scraut-implementation/06-SUGGESTIONS.md.

Implement in this order:
1. scripts/suggestions/detectors.py — all 6 detector functions + run_all_detectors()
2. scripts/suggestions/generate_suggestion.py
3. scripts/suggestions/measure.py
4. .github/workflows/suggestion-detect.yml
5. .github/workflows/suggestion-measure.yml

The detectors must:
- Return None when threshold is NOT met (no false positives)
- Return Evidence when threshold IS met
- Never call LLM (except SentimentTrendDetector which uses complete_json)

After implementing:
1. Run: python -c "
from scripts.suggestions.detectors import run_all_detectors
from scripts.utils.config import load_config
cfg = load_config()
# With empty repo, all detectors should return None (not crash)
print('Detectors imported OK')
"
2. Verify Done Criteria in 06-SUGGESTIONS.md

Commit: "feat: phase 6 - suggestion system [skip ci]"
```

---

## Phase 7 + 8 — Agent Mode + Setup CLI

**Session goal:** Agent orchestration (disabled by default), setup wizard, CLI tool.

```
Read CLAUDE.md.
Then read scraut-implementation/07-AGENT-MODE.md.
Implement all agent scripts and workflows.
Note: agents.enabled is false by default — all agent workflows must check
this flag and skip entirely if false.

Then read scraut-implementation/08-SETUP-CLI.md.
Implement:
- create-scraut/ Node.js package (bin/create-scraut.js)
- scraut_cli/cli.py and scraut_cli/setup.py
- portal/form.html
- portal/api/standup.js (edge function)
- scripts/setup/setup_github_projects.py
- INSTALL.md

After implementing:
1. Run: python scraut_cli/cli.py --help (should show commands)
2. Run: python -c "from scripts.agents.orchestrator import run_orchestrator_cycle; print('OK')"
3. Verify Done Criteria in both 07 and 08 files

Commit: "feat: phases 7+8 - agent mode and setup cli [skip ci]"
```

---

## Phase 9 — Completions

**Session goal:** All scripts and workflows that were referenced but not yet implemented.

> This is a critical phase. Every item in Phase 9 fills a gap that would
> cause a workflow to crash at runtime.

```
Read CLAUDE.md, then read scraut-implementation/09-COMPLETIONS.md.

This file fills gaps from earlier phases. Implement everything in the
"Gap Audit" table at the top of the file — do not skip any item.

Key scripts to implement:
- scripts/backlog/tally_estimation.py
- scripts/sprint/close_sprint.py (full version)
- scripts/sprint/create_planning_pr.py
- scripts/sprint/generate_review.py
- scripts/sprint/synthesise_retrospective.py
- scripts/backlog/prioritize_backlog.py
- scripts/sprint/check_scope_creep.py
- scripts/insights/generate_insights.py
- scripts/backlog/pr_auto_describe.py
- scripts/backlog/pr_knowledge_extract.py

Key workflows to implement:
- .github/workflows/backlog-grooming.yml
- .github/workflows/pr-linker.yml
- .github/workflows/pr-close-stories.yml
- .github/workflows/dod-check.yml
- .github/workflows/incident-to-backlog.yml
- .github/workflows/sprint-plan-pr.yml

Also apply the two updates:
- Add breadcrumb navigation comment to STANDUP_TEMPLATE in reset_templates.py
- Add complete_batch() to scripts/llm/client.py
- Add generate_form_html() to scripts/visibility/generate_portal.py

After implementing:
1. Run: python -c "from scripts.backlog.tally_estimation import EMOJI_TO_SP, determine_winner; print(determine_winner({1:2, 5:3}))"
   Expected output: 5
2. Run: python -c "from scripts.sprint.generate_review import generate_review; print('OK')"
3. Verify the Final Completeness Checklist at the bottom of 09-COMPLETIONS.md

Commit: "feat: phase 9 - all completions [skip ci]"
```

---

## Phase 10 — Testing

**Session goal:** Full pytest suite. This phase is also verification that everything works.

```
Read CLAUDE.md, then read scraut-implementation/10-TESTING.md.

Implement in this order:
1. requirements-test.txt
2. pytest.ini
3. All files under tests/fixtures/ (copy content exactly as shown)
4. tests/mocks/github_mocks.py
5. tests/mocks/llm_mocks.py
6. tests/conftest.py
7. All tests/unit/test_*.py files
8. All tests/integration/test_*.py files
9. .github/workflows/test-ci.yml

After implementing, run the full test suite:
  pip install -r requirements-test.txt
  pytest tests/unit/ -v

Expected: all unit tests pass.

If any test fails:
- Read the failure message carefully
- Fix the SCRIPT being tested, not the test
- Tests describe correct behaviour — the scripts must match them
- Re-run until all pass

Then run integration tests:
  pytest tests/integration/ -v

Commit: "feat: phase 10 - full test suite [skip ci]"
```

---

## After all phases: end-to-end smoke test

Run this after all 10 phases are committed:

```
Read CLAUDE.md.

Run these end-to-end smoke tests and fix any failures:

1. Config loads cleanly:
   python -c "from scripts.utils.config import load_config; cfg = load_config(); print(f'Team: {len(cfg[\"team\"][\"members\"])} members, Sprint: {cfg[\"sprint\"][\"current_sprint\"]}')"

2. All scripts import without errors:
   python -c "
   from scripts.llm.client import complete, complete_json, complete_batch
   from scripts.standup.reset_templates import reset_templates
   from scripts.standup.generate_summary import generate_summary
   from scripts.milestone.decompose import decompose_milestone
   from scripts.milestone.health_check import score_sprint
   from scripts.visibility.derive_state import derive_all_states
   from scripts.suggestions.detectors import run_all_detectors
   from scripts.backlog.tally_estimation import tally_estimation
   from scripts.sprint.generate_review import generate_review
   from scripts.sprint.synthesise_retrospective import synthesise_retrospective
   from scripts.insights.generate_insights import generate_all_insights
   print('All imports OK')
   "

3. Full test suite passes:
   pytest --tb=short -q
   (Expected: all tests pass, coverage ≥ 70%)

4. Dry-run the standup workflow:
   python scripts/standup/reset_templates.py --dry-run
   python scripts/visibility/generate_portal.py --dry-run

Report any failures. Fix the script, not the test.
```

---

## If a phase fails or produces wrong output

**Don't start the next phase until the current one passes its Done Criteria.**

Common issues and fixes:

| Problem | Cause | Fix |
|---------|-------|-----|
| `ImportError: No module named 'scripts.utils.config'` | Running from wrong directory | `cd` to repo root first |
| `KeyError: 'sprint'` in config | scraut.yml missing a key | Add the missing key to scraut.yml |
| Test fails with `FileNotFoundError` | Fixture file missing | Check `tests/fixtures/` has all files from Phase 10 |
| LLM call fails in test | Test is not mocking LLM | Patch `scripts.llm.client.complete` in the test |
| Workflow fails with `[skip ci]` loop | Bot commit triggering workflow | Verify all bot commits have `[skip ci]` in message |
| `AttributeError: MockRepository has no method X` | Script calling PyGitHub method not in mock | Add method to `tests/mocks/github_mocks.py` |

**If Claude Code gets confused mid-session:**

```
Stop. Do not continue.
Re-read CLAUDE.md.
Re-read scraut-implementation/[CURRENT_PHASE].md from the beginning.
List every file you have already created in this session.
List every file you still need to create.
Then continue implementing the remaining files only.
```

---

## Secrets checklist (configure before running workflows)

Set these in GitHub → Settings → Secrets and variables → Actions:

| Secret | Required | Description |
|--------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ Yes | Anthropic API key |
| `SLACK_WEBHOOK` | Recommended | Slack incoming webhook for channel posts |
| `SLACK_BOT_TOKEN` | Recommended | Slack bot token for personal DMs |
| `SCRAUT_GITHUB_TOKEN` | If using repo sync | PAT with read access to connected repos |
| `SMTP_HOST` | If using email | SMTP server hostname |
| `SMTP_PORT` | If using email | Usually 587 |
| `SMTP_USER` | If using email | SMTP username/email |
| `SMTP_PASS` | If using email | SMTP password or app password |

---

## Quick reference: all phases

| Session | Phase | Files created | Time estimate |
|---------|-------|--------------|--------------|
| 0 | Prep | scraut.yml, .gitignore, requirements.txt, directories | 10 min |
| 1 | Foundation | ~12 Python files, 5 issue templates | 45 min |
| 2 | Ceremonies | ~14 Python files, 6 workflow YAMLs | 75 min |
| 3+4 | Milestone + Repo Sync | ~8 Python files, 5 workflow YAMLs | 50 min |
| 5 | Visibility Portal | ~6 Python files, 4 workflow YAMLs | 50 min |
| 6 | Suggestions | ~3 Python files, 2 workflow YAMLs | 45 min |
| 7+8 | Agents + Setup | ~10 files mixed, 3 workflows | 60 min |
| 9 | Completions | ~10 Python files, 6 workflow YAMLs | 75 min |
| 10 | Testing | ~20 test files, fixtures, mocks, 1 workflow | 60 min |
| — | Smoke test | No new files | 15 min |
