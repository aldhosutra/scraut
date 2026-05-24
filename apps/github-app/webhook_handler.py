"""
github-app/webhook_handler.py
GitHub App webhook handler (Flask).
Processes GitHub webhook events and triggers appropriate Scraut workflows.

Deploy to Fly.io, Railway, or similar. Use smee.io for local development.

Required environment variables:
  GITHUB_APP_WEBHOOK_SECRET  — webhook secret from GitHub App settings
  GITHUB_APP_ID              — numeric App ID from GitHub App settings
  GITHUB_APP_PRIVATE_KEY     — PEM private key (newlines as \\n)
"""
import hashlib
import hmac
import json
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

# Maps a logical trigger name to the workflow file to dispatch.
PUSH_TRIGGERS = {
    "milestone-planning": ".github/workflows/milestone-planning.yml",
    "visibility-engine": ".github/workflows/visibility-engine.yml",
}

# Minimal workspace/scraut.yml written on fresh installation.
SCRAUT_YML_TEMPLATE = """\
# scraut.yml — fill in your team details, then commit.
# Full documentation: https://github.com/aldhosutra/scraut

sprint:
  length_days: 14
  start_day: monday
  start_time: "09:00"
  timezone: "UTC"
  capacity_buffer: 0.85
  current_sprint: 1

team:
  members:
    - login: your-github-login
      display: Your Name
      role: developer
      slack_id: UXXXXXXXXX
      email: you@example.com
  product_owner: your-github-login
  scrum_master: your-github-login
  slack_channel: "#scraut-bot"

ceremonies:
  planning: true
  standup: true
  grooming: true
  review: true
  retrospective: true
  estimation: true

definition_of_done:
  - Tests written for new functionality
  - PR reviewed by at least one team member
  - Acceptance criteria mentioned in PR description
  - No open review comments
  - CI passing

repos: []

llm:
  provider: anthropic               # anthropic | openai | gemini | ollama
  model: claude-sonnet-4-6          # Model name for the chosen provider
  base_url: ""                      # Optional: override API base URL (empty = default)
  max_tokens: 1000
  cost_controls:
    max_daily_tokens: 100000
    batch_where_possible: true

agents:
  enabled: false

paths:
  workspace: workspace
  scraut: .scraut
  portal: apps/portal

notifications:
  slack_webhook: ""
  morning_dm: true
  weekly_email: false
  stakeholder_emails: []

portal:
  enabled: true
  title: "Team Dashboard"
  public: true
  refresh_minutes: 30

suggestions:
  enabled: true
  min_evidence_count: 3
  measurement_sprints: 2
"""


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def verify_webhook_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    expected = "sha256=" + hmac.new(
        secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def _get_app_jwt() -> str:
    """Generate a short-lived GitHub App JWT using the configured private key."""
    try:
        import jwt as pyjwt
    except ImportError as exc:
        raise ImportError("PyJWT is required: pip install PyJWT cryptography") from exc

    app_id = os.environ.get("GITHUB_APP_ID", "")
    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY", "").replace("\\n", "\n")
    if not app_id or not private_key:
        raise ValueError(
            "GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY environment variables must be set"
        )

    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 600, "iss": app_id}
    return pyjwt.encode(payload, private_key, algorithm="RS256")


def get_installation_token(installation_id: str) -> str:
    """Exchange a GitHub App JWT for an installation access token."""
    app_jwt = _get_app_jwt()
    resp = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers={
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github.v3+json",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


# ---------------------------------------------------------------------------
# Workflow dispatch
# ---------------------------------------------------------------------------

def dispatch_workflow(repo_full_name: str, workflow_file: str, token: str,
                      inputs: dict | None = None) -> None:
    """Trigger a workflow_dispatch event on the given repository."""
    resp = requests.post(
        f"https://api.github.com/repos/{repo_full_name}/actions/workflows"
        f"/{workflow_file}/dispatches",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        },
        json={"ref": "main", "inputs": inputs or {}},
        timeout=10,
    )
    resp.raise_for_status()
    logger.info(f"Dispatched {workflow_file} on {repo_full_name}")


# ---------------------------------------------------------------------------
# Repo scaffolding (on installation)
# ---------------------------------------------------------------------------

def _create_or_update_file(repo_full_name: str, path: str, content: str,
                            token: str, message: str) -> None:
    """Create (or silently skip if already exists) a file via the GitHub Contents API."""
    import base64

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    api_url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"

    # Check if the file already exists so we don't overwrite it.
    check = requests.get(api_url, headers=headers, timeout=10)
    if check.status_code == 200:
        logger.debug(f"Skipping existing file: {path}")
        return

    encoded = base64.b64encode(content.encode()).decode()
    resp = requests.put(
        api_url,
        headers=headers,
        json={"message": message, "content": encoded, "branch": "main"},
        timeout=10,
    )
    if resp.status_code in (201, 200):
        logger.info(f"Created {path} in {repo_full_name}")
    else:
        logger.warning(f"Could not create {path}: {resp.status_code} {resp.text[:200]}")


def scaffold_repo(repo_full_name: str, token: str) -> None:
    """Create the minimal Scraut workspace skeleton in a newly installed repo."""
    commit_msg = "chore: initialise Scraut workspace [skip ci]"

    # Core config
    _create_or_update_file(
        repo_full_name, "workspace/scraut.yml", SCRAUT_YML_TEMPLATE, token, commit_msg
    )

    # Workspace skeleton — one .gitkeep per directory so git tracks them
    skeleton_dirs = [
        "workspace/team",
        "workspace/customer",
        "workspace/knowledge",
        "workspace/milestones",
        "workspace/okr",
        "workspace/sprint/01/standup",
        "workspace/sprint/01/retrospective",
        "workspace/sprint/01/grooming",
        "workspace/sprint/01/decisions",
        "workspace/sprint/01/adr",
        ".scraut/sprint/01/standup/summary",
        ".scraut/sprint/01/review",
        ".scraut/sprint/01/code",
        ".scraut/sprint/01/incidents",
        ".scraut/insights",
        ".scraut/milestones",
        ".scraut/suggestions/active",
        ".scraut/suggestions/implemented",
        ".scraut/suggestions/resolved",
    ]
    for directory in skeleton_dirs:
        _create_or_update_file(
            repo_full_name,
            f"{directory}/.gitkeep",
            "",
            token,
            commit_msg,
        )

    logger.info(f"Scaffold complete for {repo_full_name}")


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

def handle_push(payload: dict) -> None:
    """Handle push events: detect changed files and dispatch relevant workflows."""
    ref = payload.get("ref", "")
    if ref != "refs/heads/main":
        return

    installation_id = str(payload.get("installation", {}).get("id", ""))
    repo_full_name = payload.get("repository", {}).get("full_name", "")

    commits = payload.get("commits", [])
    changed_files: list[str] = []
    for commit in commits:
        changed_files.extend(commit.get("added", []))
        changed_files.extend(commit.get("modified", []))

    triggers: set[str] = set()
    if any("workspace/milestones/" in f and f.endswith("milestone.md")
           for f in changed_files):
        triggers.add("milestone-planning")
    if any(("workspace/sprint/" in f and "/standup/" in f)
           or ".scraut/sprint/" in f
           for f in changed_files):
        triggers.add("visibility-engine")

    if not triggers:
        logger.debug(f"Push to {repo_full_name}: no Scraut triggers in changed files")
        return

    logger.info(f"Push to {repo_full_name}: triggering {triggers}")
    try:
        token = get_installation_token(installation_id)
    except Exception as exc:
        logger.error(f"Could not get installation token: {exc}")
        return

    for trigger in triggers:
        workflow_file = PUSH_TRIGGERS.get(trigger)
        if workflow_file:
            try:
                dispatch_workflow(repo_full_name, workflow_file, token)
            except Exception as exc:
                logger.error(f"Failed to dispatch {workflow_file}: {exc}")


def handle_installation(payload: dict) -> None:
    """Handle GitHub App installation: scaffold Scraut workspace into each new repo."""
    installation_id = str(payload.get("installation", {}).get("id", ""))
    repos = payload.get("repositories", [])

    if not repos:
        return

    try:
        token = get_installation_token(installation_id)
    except Exception as exc:
        logger.error(f"Could not get installation token for installation {installation_id}: {exc}")
        return

    for repo in repos:
        repo_full_name = repo.get("full_name", "")
        logger.info(f"Scraut installed on {repo_full_name}")
        try:
            scaffold_repo(repo_full_name, token)
        except Exception as exc:
            logger.error(f"Scaffold failed for {repo_full_name}: {exc}")


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

try:
    from flask import Flask, request, jsonify

    app = Flask(__name__)

    @app.route("/webhooks/github", methods=["POST"])
    def github_webhook():
        secret = os.environ.get("GITHUB_APP_WEBHOOK_SECRET", "")
        signature = request.headers.get("X-Hub-Signature-256", "")

        if not verify_webhook_signature(request.data, signature, secret):
            return jsonify({"error": "Invalid signature"}), 401

        event = request.headers.get("X-GitHub-Event")
        payload = request.json or {}

        if event == "push":
            handle_push(payload)
        elif event in ("installation", "installation_repositories"):
            handle_installation(payload)
        else:
            logger.debug(f"Unhandled event: {event}")

        return jsonify({"status": "ok"}), 200

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy"}), 200

except ImportError:
    pass  # Flask not installed; wire up your own ASGI/WSGI framework
