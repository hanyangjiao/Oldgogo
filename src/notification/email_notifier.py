from __future__ import annotations

import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import List, Dict


def send_email_notification(contacts: List[Dict[str, str]], subject: str, body: str) -> None:
    recipients = [c["email"] for c in contacts if c.get("email")]
    if not recipients:
        return

    # Always write a local copy for UI preview/debugging.
    _write_fallback_notification(subject, body, recipients)

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "0"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if smtp_host and smtp_port and smtp_user and smtp_pass and smtp_from:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return

    return


def _write_fallback_notification(subject: str, body: str, recipients: List[str]) -> None:
    base_dir = Path("output/notifications")
    base_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = base_dir / f"email_{timestamp}.txt"

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"To: {', '.join(recipients)}\n")
        handle.write(f"Subject: {subject}\n\n")
        handle.write(body)
