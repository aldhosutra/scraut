"""
lib/notifications/slack_post.py
Post messages to Slack channels via Incoming Webhook or Bot API.
"""
import os
import logging
import requests
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def post_to_slack(webhook_url: str, text: str,
                  blocks: Optional[list] = None) -> bool:
    """Post a message to a Slack channel via webhook."""
    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error(f"Slack post failed: {e}")
        return False


def send_slack_dm(user_id: str, text: str, bot_token: Optional[str] = None) -> bool:
    """Send a direct message to a Slack user."""
    token = bot_token or os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set. Skipping DM.")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    resp = requests.post(
        "https://slack.com/api/conversations.open",
        json={"users": user_id},
        headers=headers,
        timeout=10,
    )
    data = resp.json()
    if not data.get("ok"):
        logger.error(f"Failed to open DM channel: {data.get('error')}")
        return False

    channel_id = data["channel"]["id"]

    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        json={"channel": channel_id, "text": text, "mrkdwn": True},
        headers=headers,
        timeout=10,
    )
    data = resp.json()
    if not data.get("ok"):
        logger.error(f"Failed to send DM: {data.get('error')}")
        return False

    return True
