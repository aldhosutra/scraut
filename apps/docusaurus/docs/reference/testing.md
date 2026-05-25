---
sidebar_position: 9
---

# Testing

Scraut has three layers of tests, each targeting a different failure mode.

---

## Layer 1 — Unit tests (Python)

**What they cover:** Individual Python functions with all external calls mocked. No real API calls, no file I/O to real paths, no Docker.

**Run locally:**
```bash
cd apps/automation
pytest test/unit/ -m unit -v
```

**Run in CI:** Every push to `main` or `develop` via `test-ci.yml`.

**What they catch:** Logic bugs, wrong argument handling, fallback provider routing, `use_small_model` selection, token tracking.

---

## Layer 2 — Integration tests (Python)

**What they cover:** Every script's `--help` flag — verifies all scripts are importable and their CLI argument parsers are syntactically valid.

**Run locally:**
```bash
cd apps/automation
pytest test/integration/ -m integration -v
```

**Run in CI:** Every push, same `test-ci.yml` job.

**What they catch:** Import errors, broken argparse configs, missing `__init__.py` files.

---

## Layer 3 — Workflow lint (`actionlint`)

**What they cover:** All 25+ `.github/workflows/*.yml` files statically. No Docker, no credentials.

**Run locally:**
```bash
# Install
brew install actionlint            # macOS
# or: https://github.com/rhysd/actionlint/releases

actionlint                         # runs from repo root
```

**Run in CI:** Every push via the `lint` job in `test-ci.yml`.

**What they catch:**
- YAML syntax errors
- Invalid workflow/job/step structure
- Broken `${{ }}` expression syntax
- References to secrets or contexts that don't exist
- Shell script errors (via integrated shellcheck)
- Incorrect action input/output wiring

---

## Layer 4 — `act` workflow tests (local, Docker)

**What they cover:** The actual GitHub Actions workflow files running in a Docker container. This is the only layer that exercises:
- The composite `setup-ollama` action
- That `pip install` resolves correctly
- That env vars and workflow inputs flow through to Python scripts
- That the `--dry-run` path works end-to-end through the YAML → script chain

**Prerequisites:**
```bash
# Install act
brew install act                   # macOS
# or: https://github.com/nektos/act/releases

# Docker must be running
docker info

# Optional but recommended: GitHub CLI for GITHUB_TOKEN
gh auth login
```

**Set up secrets (one-time):**
```bash
cp apps/automation/test/act/.secrets.example .secrets
# Edit .secrets and fill in GITHUB_TOKEN (minimum required)
# Other secrets are optional — LLM falls back to github provider if unset
```

**Run all act tests:**
```bash
./scripts/test-act.sh
```

**Run a single workflow:**
```bash
./scripts/test-act.sh daily-standup
./scripts/test-act.sh sprint-planning
./scripts/test-act.sh template-reset
./scripts/test-act.sh backlog-grooming
./scripts/test-act.sh issue-triage
```

**What `act` tests verify (dry-run mode):**

| Workflow | Event | dry_run covers |
|---------|-------|---------------|
| `template-reset.yml` | `workflow_dispatch` | standup template creation, no commit |
| `daily-standup.yml` | `workflow_dispatch` | summary + coach steps, no commit |
| `sprint-planning.yml` | `workflow_dispatch` | sprint folder + planning PR, no writes |
| `backlog-grooming.yml` | `workflow_dispatch` | prioritisation + scope check, no posts |
| `issue-triage.yml` | `workflow_dispatch` | triage script, no label/comment writes |

All tests pass `dry_run=true` — scripts receive `--dry-run` and skip all writes, GitHub mutations, and Slack posts. LLM calls use the fallback chain (github provider → empty string) so no API key is strictly required.

:::note Why act tests are local-only
Running `act` inside GitHub Actions requires Docker-in-Docker (`--privileged` mode), which is not available on GitHub-hosted runners. `actionlint` (Layer 3) provides automated YAML validation in CI. Run `act` tests locally before pushing workflow changes.
:::

---

## How the layers complement each other

```
Unit tests        → Python logic is correct
Integration tests → Scripts are importable, CLI args valid
actionlint        → Workflow YAML is valid, expressions correct
act tests         → Workflows actually execute end-to-end
```

No single layer replaces another. A broken composite action (`setup-ollama`) would only be caught by the `act` layer. A logic bug in `_resolve_model()` would only be caught by unit tests.

---

## `act` image and architecture

Scraut ships a `.actrc` at the repo root that configures `act` to use the lightweight `ghcr.io/catthehacker/ubuntu:act-latest` image (~500 MB vs ~18 GB for the full GitHub runner image) and forces `linux/amd64` architecture for consistency on Apple Silicon Macs.

```
# .actrc
-P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest
--container-architecture linux/amd64
```

First run pulls the Docker image once (~500 MB). Subsequent runs use the cached image.

---

## Test file map

```
apps/automation/
  test/
    unit/                            ← pytest unit tests (mock everything)
    integration/                     ← pytest integration tests (--help smoke tests)
    act/
      events/
        issues_opened.json           ← issue payload for issue-triage act test
        pull_request_opened.json     ← PR payload for pr-linker/dod-check act tests
      .secrets.example               ← copy to .secrets, fill in GITHUB_TOKEN

scripts/
  test-act.sh                        ← act test runner (./scripts/test-act.sh)

.actrc                               ← act platform + architecture config
.secrets                             ← gitignored; your local act secrets
```
