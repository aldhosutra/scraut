"""
lib/notifications/send_email.py
Send HTML email via SMTP. Used by weekly_digest.py.
Reads SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS from environment.
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


def send_email(
    to_addresses: list[str],
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    from_address: Optional[str] = None,
) -> bool:
    """Send an HTML email via SMTP. Returns True on success."""
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    from_addr = from_address or smtp_user or "scraut-bot@noreply.example.com"

    if not smtp_host or not smtp_user:
        logger.warning("SMTP_HOST/SMTP_USER not configured — skipping email")
        return False

    if not to_addresses:
        logger.warning("No recipient addresses provided — skipping email")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addresses)

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_addr, to_addresses, msg.as_string())
        logger.info(f"Email '{subject}' sent to {to_addresses}")
        return True
    except smtplib.SMTPException as e:
        logger.error(f"Failed to send email '{subject}': {e}")
        return False
