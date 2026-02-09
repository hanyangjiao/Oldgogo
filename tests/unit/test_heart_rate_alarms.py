from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from domain.dataset import Dataset, TaskItem
from notification.cooldown import CooldownStore, CooldownTracker


@pytest.fixture
def temp_cooldown_path():
    """Create a temporary cooldown state file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        # Initialize with valid cooldown state
        json.dump({"remaining_cycles": 0}, f)
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def cooldown_tracker(temp_cooldown_path):
    """Create a cooldown tracker for testing."""
    store = CooldownStore(temp_cooldown_path)
    return CooldownTracker(cycles_after_reminder=2, store=store)


def test_tachycardia_triggers_voice_alarm(cooldown_tracker):
    """Test that tachycardia (high heart rate) triggers voice alarm."""
    from notification.voice_notifier import send_voice_reminder

    with patch('notification.voice_notifier._emit_voice') as mock_emit:
        result = send_voice_reminder(
            message="Warning! Your heart rate is too high. Please sit down and take deep breaths.",
            cooldown_tracker=cooldown_tracker,
        )

        assert result is True
        assert mock_emit.call_count == 1
        assert "heart rate is too high" in mock_emit.call_args[0][0]


def test_bradycardia_triggers_voice_alarm(cooldown_tracker):
    """Test that bradycardia (low heart rate) triggers voice alarm."""
    from notification.voice_notifier import send_voice_reminder

    with patch('notification.voice_notifier._emit_voice') as mock_emit:
        result = send_voice_reminder(
            message="Warning! Your heart rate is too low. Please rest and seek medical attention if needed.",
            cooldown_tracker=cooldown_tracker,
        )

        assert result is True
        assert mock_emit.call_count == 1
        assert "heart rate is too low" in mock_emit.call_args[0][0]


def test_repeated_unrepeatable_task_triggers_voice_alarm(cooldown_tracker):
    """Test that repeating an unrepeatable task triggers voice alarm."""
    from notification.voice_notifier import send_voice_reminder

    with patch('notification.voice_notifier._emit_voice') as mock_emit:
        result = send_voice_reminder(
            message="Warning! You are doing a task that should not be repeated.",
            cooldown_tracker=cooldown_tracker,
        )

        assert result is True
        assert mock_emit.call_count == 1
        assert "should not be repeated" in mock_emit.call_args[0][0]


def test_cooldown_prevents_consecutive_alarms(cooldown_tracker):
    """Test that cooldown prevents spam of voice alarms."""
    from notification.voice_notifier import send_voice_reminder

    with patch('notification.voice_notifier._emit_voice') as mock_emit:
        # First alarm should succeed
        result1 = send_voice_reminder(
            message="Warning! Your heart rate is too high.",
            cooldown_tracker=cooldown_tracker,
        )
        assert result1 is True
        assert mock_emit.call_count == 1

        # Second alarm should be blocked by cooldown
        result2 = send_voice_reminder(
            message="Warning! Your heart rate is too high.",
            cooldown_tracker=cooldown_tracker,
        )
        assert result2 is False
        assert mock_emit.call_count == 1  # Still only 1 call


def test_cooldown_resets_after_cycles(cooldown_tracker, temp_cooldown_path):
    """Test that cooldown resets after configured cycles."""
    from notification.voice_notifier import send_voice_reminder

    with patch('notification.voice_notifier._emit_voice') as mock_emit:
        # First alarm
        result1 = send_voice_reminder("Test alarm", cooldown_tracker)
        assert result1 is True

        # Blocked during cooldown
        result2 = send_voice_reminder("Test alarm", cooldown_tracker)
        assert result2 is False

        # Tick down cooldown (2 cycles configured)
        cooldown_tracker.tick()
        result3 = send_voice_reminder("Test alarm", cooldown_tracker)
        assert result3 is False  # Still blocked

        cooldown_tracker.tick()
        result4 = send_voice_reminder("Test alarm", cooldown_tracker)
        assert result4 is True  # Now allowed again

        assert mock_emit.call_count == 2


def test_voice_alarm_integration_with_apply_analysis_report():
    """Test that anomalies in analysis report trigger voice alarms correctly."""
    from domain.update_rules import apply_analysis_report

    dataset = Dataset(
        task_list=[],
        anomaly_list=[],
    )

    # Report with tachycardia detected
    report_tachycardia = {
        "window": {
            "start_time": "2026-01-16T09:00:00+08:00",
            "end_time": "2026-01-16T09:03:00+08:00",
        },
        "tasks": [],
        "anomalies": [
            {
                "type": "tachycardia",
                "match": True,
                "num_of_happens": 1,
                "reason": "Heart rate consistently above 120 bpm"
            },
            {
                "type": "bradycardia",
                "match": False,
                "num_of_happens": 0,
                "reason": "No low heart rate detected"
            }
        ]
    }

    notifications = apply_analysis_report(dataset, report_tachycardia)

    # Should have email notification for tachycardia
    assert len(notifications.email_notifications) == 1
    assert notifications.email_notifications[0].anomaly_type == "tachycardia"
    assert notifications.voice_reminder is False  # Not set by update_rules


def test_voice_alarm_for_bradycardia_in_report():
    """Test that bradycardia in report creates email notification."""
    from domain.update_rules import apply_analysis_report

    dataset = Dataset(
        task_list=[],
        anomaly_list=[],
    )

    report_bradycardia = {
        "window": {
            "start_time": "2026-01-16T09:00:00+08:00",
            "end_time": "2026-01-16T09:03:00+08:00",
        },
        "tasks": [],
        "anomalies": [
            {
                "type": "bradycardia",
                "match": True,
                "num_of_happens": 1,
                "reason": "Heart rate consistently below 50 bpm"
            }
        ]
    }

    notifications = apply_analysis_report(dataset, report_bradycardia)

    assert len(notifications.email_notifications) == 1
    assert notifications.email_notifications[0].anomaly_type == "bradycardia"


def test_repeated_unrepeatable_task_sets_voice_reminder():
    """Test that repeating an unrepeatable task sets voice_reminder flag."""
    from domain.update_rules import apply_analysis_report

    dataset = Dataset(
        task_list=[
            TaskItem(
                task_type="take_medicine",
                start_time="2026-01-16T08:00:00+08:00",
                end_time="2026-01-16T09:00:00+08:00",
                status="Complete",  # Already done once
                if_repeatable=False,
            )
        ],
        anomaly_list=[],
    )

    report = {
        "window": {
            "start_time": "2026-01-16T08:00:00+08:00",
            "end_time": "2026-01-16T09:00:00+08:00",
        },
        "tasks": [
            {
                "type": "take_medicine",
                "match": True,  # Detected again
                "repeated_count": 2,
                "reason": "Person is taking medicine again"
            }
        ],
        "anomalies": []
    }

    notifications = apply_analysis_report(dataset, report)

    # Should trigger voice reminder for repeating unrepeatable task
    assert notifications.voice_reminder is True


def test_no_voice_alarm_when_no_anomalies():
    """Test that no voice alarm is triggered when no anomalies detected."""
    from domain.update_rules import apply_analysis_report

    dataset = Dataset(task_list=[], anomaly_list=[])

    report = {
        "window": {
            "start_time": "2026-01-16T09:00:00+08:00",
            "end_time": "2026-01-16T09:03:00+08:00",
        },
        "tasks": [],
        "anomalies": [
            {
                "type": "tachycardia",
                "match": False,
                "num_of_happens": 0,
                "reason": "Heart rate normal"
            }
        ]
    }

    notifications = apply_analysis_report(dataset, report)

    assert len(notifications.email_notifications) == 0
    assert notifications.voice_reminder is False


def test_gtts_backend_produces_speech():
    """Test that gTTS backend can generate speech (integration test)."""
    from notification.voice_notifier import _try_gtts

    # This is an integration test - it actually uses gTTS
    # Skip if gTTS or ffplay not available
    pytest.importorskip("gtts")

    import shutil
    if not shutil.which("ffplay"):
        pytest.skip("ffplay not available")

    result = _try_gtts("Test message")
    # If both are available, should succeed
    assert result is True
