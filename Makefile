.PHONY: help init test test-unit test-integration test-act lint install

PYTHON := python3
PYTEST  := cd apps/automation && python -m pytest

help:          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Init ─────────────────────────────────────────────────────────────────────

# Use Make's dependency tracking: npm install only reruns when package.json changes.
apps/create-scraut/node_modules: apps/create-scraut/package.json
	cd apps/create-scraut && npm install

init: apps/create-scraut/node_modules  ## Run the interactive setup wizard
	node apps/create-scraut/bin/create-scraut.js

# ── Install ──────────────────────────────────────────────────────────────────

install:       ## Install Python dependencies
	pip install -r apps/automation/requirements.txt \
	            -r apps/automation/requirements-test.txt

# ── Tests ────────────────────────────────────────────────────────────────────

test:          ## Run unit + integration tests
	$(PYTEST) test/unit/        -m unit        -v --tb=short
	$(PYTEST) test/integration/ -m integration -v --tb=short

test-unit:     ## Run unit tests only
	$(PYTEST) test/unit/ -m unit -v --tb=short

test-integration: ## Run integration tests only
	$(PYTEST) test/integration/ -m integration -v --tb=short

test-act:      ## Run act workflow tests locally (requires Docker + act)
	./scripts/test-act.sh

# ── Lint ─────────────────────────────────────────────────────────────────────

lint:          ## Lint Python code (flake8) and workflow YAML (actionlint)
	flake8 apps/automation/scraut/ --max-line-length=100 --ignore=E501,W503
	actionlint

# ── Docs ─────────────────────────────────────────────────────────────────────

docs:          ## Build documentation
	cd apps/docusaurus && npm run build

docs-serve:    ## Serve docs locally at http://localhost:3000
	cd apps/docusaurus && npm run start
