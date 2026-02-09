from pathlib import Path

import pytest

from notification.email_notifier import send_email_notification


def test_email_fallback_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)

    send_email_notification(
        contacts=[{"name": "Test", "email": "test@example.com"}],
        subject="Anomaly Alert",
        body="Body line 1\nBody line 2",
    )

    out_dir = tmp_path / "output" / "notifications"
    files = list(out_dir.glob("email_*.txt"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "To: test@example.com" in content
    assert "Subject: Anomaly Alert" in content
    assert "Body line 1" in content


def test_email_no_recipients_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    send_email_notification(contacts=[], subject="Nope", body="Ignored")

    out_dir = tmp_path / "output" / "notifications"
    assert not out_dir.exists()
