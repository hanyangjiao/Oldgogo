from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from llm.gemini_client import GeminiClient
from notification.email_notifier import send_email_notification


def save_daily_summary(
    dataset_snapshot: Dict[str, Any],
    contacts: List[Dict[str, str]],
    reports_root: Path,
    client: GeminiClient,
) -> Path:
    summary_text = client.summarize_daily(dataset_snapshot)

    timestamp = datetime.now().strftime("%Y-%m-%d/%H%M%S")
    target_dir = reports_root / timestamp.split("/")[0]
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{timestamp.split('/')[1]}_daily_summary.txt"
    path = target_dir / filename

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(summary_text)

    send_email_notification(
        contacts=contacts,
        subject="Daily Summary",
        body=summary_text,
    )
    return path

