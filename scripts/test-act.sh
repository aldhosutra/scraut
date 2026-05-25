#!/usr/bin/env bash
# test-act.sh — Run Scraut GitHub Actions workflows locally using act.
#
# Prerequisites:
#   brew install act          (macOS)
#   curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | bash  (Linux)
#   Docker must be running.
#
# Usage:
#   ./scripts/test-act.sh                   # run all act tests
#   ./scripts/test-act.sh daily-standup     # run one workflow by name
#   GITHUB_TOKEN=xxx ./scripts/test-act.sh  # explicit token
#
# All tests run with dry_run=true — no real writes, no GitHub mutations.
# LLM calls use the github fallback (GITHUB_TOKEN) or return "" gracefully.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
EVENTS_DIR="$REPO_ROOT/apps/automation/test/act/events"
SECRETS_FILE="$REPO_ROOT/.secrets"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Preflight checks ────────────────────────────────────────────────────────

if ! command -v act &>/dev/null; then
    echo -e "${RED}ERROR: act is not installed.${NC}"
    echo "  macOS:  brew install act"
    echo "  Linux:  curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | bash"
    exit 1
fi

if ! docker info &>/dev/null 2>&1; then
    echo -e "${RED}ERROR: Docker is not running. Start Docker Desktop and retry.${NC}"
    exit 1
fi

# Resolve GITHUB_TOKEN: env var > gh CLI > empty (tests still run, LLM returns "")
if [ -z "${GITHUB_TOKEN:-}" ]; then
    GITHUB_TOKEN="$(gh auth token 2>/dev/null || echo '')"
fi
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${YELLOW}WARNING: No GITHUB_TOKEN. LLM calls will return empty strings (tests still run).${NC}"
    echo "  Fix: gh auth login  OR  export GITHUB_TOKEN=your_token"
    echo ""
else
    echo -e "${GREEN}LLM: GitHub Models fallback active (gpt-4o-mini via GITHUB_TOKEN)${NC}"
    echo "  Scripts call LLM before the dry_run gate — real LLM output is generated,"
    echo "  but nothing is written to files or posted to GitHub/Slack."
    echo ""
fi

# ── Test runner ─────────────────────────────────────────────────────────────

pass_count=0
fail_count=0
failed_names=()

run_test() {
    local name="$1"
    local workflow="$2"
    local event="${3:-workflow_dispatch}"
    shift 3
    local extra_args=("$@")

    echo -n "  $name ... "

    local act_cmd=(
        act "$event"
        -W ".github/workflows/$workflow"
        --secret "GITHUB_TOKEN=${GITHUB_TOKEN}"
        --no-cache-server
        "${extra_args[@]}"
    )
    [ -f "$SECRETS_FILE" ] && act_cmd+=(--secret-file "$SECRETS_FILE")

    local log_file="/tmp/act-${name}.log"
    if "${act_cmd[@]}" >"$log_file" 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((pass_count++)) || true
    else
        echo -e "${RED}FAIL${NC}"
        echo "    ↳ last 20 lines of log (full log: $log_file):"
        tail -20 "$log_file" | sed 's/^/      /'
        ((fail_count++)) || true
        failed_names+=("$name")
    fi
}

# ── Test matrix ─────────────────────────────────────────────────────────────

# Allow running a single workflow by name: ./scripts/test-act.sh daily-standup
FILTER="${1:-all}"

echo ""
echo "Scraut act tests (dry-run mode — no real writes or API mutations)"
echo "=================================================================="

if [[ "$FILTER" == "all" || "$FILTER" == "template-reset" ]]; then
    run_test "template-reset" "template-reset.yml" "workflow_dispatch" \
        --input "dry_run=true"
fi

if [[ "$FILTER" == "all" || "$FILTER" == "daily-standup" ]]; then
    run_test "daily-standup" "daily-standup.yml" "workflow_dispatch" \
        --input "dry_run=true"
fi

if [[ "$FILTER" == "all" || "$FILTER" == "sprint-planning" ]]; then
    REPO="${GITHUB_REPOSITORY:-test-org/test-repo}"
    run_test "sprint-planning" "sprint-planning.yml" "workflow_dispatch" \
        --input "sprint_num=1" \
        --input "repo=$REPO" \
        --input "dry_run=true"
fi

if [[ "$FILTER" == "all" || "$FILTER" == "backlog-grooming" ]]; then
    run_test "backlog-grooming" "backlog-grooming.yml" "workflow_dispatch" \
        --input "dry_run=true"
fi

if [[ "$FILTER" == "all" || "$FILTER" == "issue-triage" ]]; then
    run_test "issue-triage" "issue-triage.yml" "workflow_dispatch" \
        --input "issue=99" \
        --input "repo=test-org/test-repo" \
        --input "dry_run=true"
fi

# ── Summary ─────────────────────────────────────────────────────────────────

echo ""
echo "=================================================================="
echo -e "Results: ${GREEN}${pass_count} passed${NC}, ${RED}${fail_count} failed${NC}"

if [ "${#failed_names[@]}" -gt 0 ]; then
    echo "Failed: ${failed_names[*]}"
    exit 1
fi
