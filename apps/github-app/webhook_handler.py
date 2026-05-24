"""
github-app/webhook_handler.py
GitHub App webhook handler (Flask or FastAPI).
Processes GitHub webhook events and triggers appropriate Scraut workflows.
This runs as a small web service, separate from the GitHub Actions workflows.

For development: Use smee.io to proxy webhooks to localhost.
For production: Deploy to Fly.io, Railway, or similar.
"""
import hashlib
import hmac
import json
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def verify_webhook_signature(payload_body: bytes, signature: str,
                              secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    expected = "sha256=" + hmac.new(
        secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def handle_push(payload: dict) -> None:
    """Handle push events: trigger appropriate Scraut workflows."""
    ref = payload.get("ref", "")
    if ref != "refs/heads/main":
        return

    commits = payload.get("commits", [])
    changed_files = []
    for commit in commits:
        changed_files.extend(commit.get("added", []))
        changed_files.extend(commit.get("modified", []))

    triggers = []
    if any("milestone.md" in f for f in changed_files):
        triggers.append("milestone-planning")
    if any("standup/" in f or "code/" in f for f in changed_files):
        triggers.append("visibility-engine")

    logger.info(f"Push to main: {len(changed_files)} files changed. Triggers: {triggers}")


def handle_installation(payload: dict) -> None:
    """
    Handle GitHub App installation: scaffold Scraut into the installed repo.
    Creates directory structure and initial scraut.yml if not present.
    """
    installation_id = payload.get("installation", {}).get("id")
    repos = payload.get("repositories", [])

    for repo in repos:
        repo_full_name = repo.get("full_name")
        logger.info(f"Scraut installed on {repo_full_name} (installation #{installation_id})")
        # In production: use GitHub App installation token to create initial files
        # This mirrors what npx create-scraut does, but automated


# Flask example
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
        payload = request.json

        if event == "push":
            handle_push(payload)
        elif event == "installation":
            handle_installation(payload)

        return jsonify({"status": "ok"}), 200

except ImportError:
    pass  # Flask not available; use FastAPI or other framework
