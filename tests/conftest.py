import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def video_paths(repo_root: Path) -> List[Path]:
    videos_dir = repo_root / "data" / "videos"
    videos = sorted(
        [path for path in videos_dir.iterdir() if path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}],
        key=lambda p: p.stat().st_size,
    )
    return videos[:2]


@pytest.fixture(scope="session")
def hr_paths(repo_root: Path) -> Dict[str, Path]:
    hr_dir = repo_root / "data" / "heart_rate"
    return {
        "normal": hr_dir / "normal_hr.json",
        "tachycardia": hr_dir / "tachycardia_hr.json",
    }


@pytest.fixture
def tmp_out_dir(tmp_path: Path) -> Path:
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


@pytest.fixture
def require_api_key():
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set; real API tests skipped.")


@pytest.fixture
def fake_email_notifier(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def _fake_send_email_notification(contacts: List[Dict[str, str]], subject: str, body: str) -> None:
        calls.append({"contacts": contacts, "subject": subject, "body": body})

    monkeypatch.setattr(
        "notification.email_notifier.send_email_notification",
        _fake_send_email_notification,
    )
    return calls


@pytest.fixture
def fake_voice_notifier(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def _fake_send_voice_reminder(message: str, cooldown_tracker: Any) -> bool:
        calls.append({"message": message})
        cooldown_tracker.record_reminder()
        return True

    monkeypatch.setattr(
        "notification.voice_notifier.send_voice_reminder",
        _fake_send_voice_reminder,
    )
    return calls


@pytest.fixture
def fixed_time() -> datetime:
    return datetime(2026, 1, 16, 9, 3, 0)
