# Covers: F3, F11
from datetime import datetime, timedelta

import app.main as app_main
import reporting.daily_summary as daily_summary
from domain.dataset import Dataset, TaskItem, AnomalyItem


def test_reset_time_summary_flow(monkeypatch, repo_root, tmp_path, fixed_time, require_api_key):
    class _FixedDateTime(datetime):
        @classmethod
        def now(cls):
            return fixed_time

    email_calls = []

    def _fake_email(contacts, subject, body):
        email_calls.append({"contacts": contacts, "subject": subject, "body": body})

    monkeypatch.setattr(app_main, "datetime", _FixedDateTime)
    monkeypatch.setattr(daily_summary, "datetime", _FixedDateTime)
    monkeypatch.setattr(daily_summary, "send_email_notification", _fake_email)

    dataset = Dataset(
        task_list=[
            TaskItem(
                task_type="drink_water",
                start_time="2026-01-16T09:00:00+08:00",
                end_time="2026-01-16T09:05:00+08:00",
                status="Complete",
                if_repeatable=True,
            )
        ],
        anomaly_list=[
            AnomalyItem(
                anomaly_type="falldown",
                start_time="2026-01-16T09:01:00+08:00",
                end_time="2026-01-16T09:02:00+08:00",
                status=1,
            )
        ],
    )

    config = {
        "anomaly_type_list": ["falldown"],
        "emergency_contact": [{"name": "Test", "relationship": "son", "email": "test@example.com"}],
        "reset_time": {"daily_reset": True, "time_local": fixed_time.strftime("%H:%M")},
    }

    app_main.run_cycle(
        dataset=dataset,
        config=config,
        schema_dir=repo_root / "spec" / "schema",
        reports_root=tmp_path / "reports",
        heart_rate_path=None,
        cooldown_tracker=app_main.CooldownTracker(
            cycles_after_reminder=0,
            store=app_main.CooldownStore(tmp_path / "cooldown.json"),
        ),
        cycle_index=0,
        window_start=fixed_time,
        window_end=fixed_time + timedelta(minutes=3),
        mode="local",
        video_path=repo_root / "data" / "videos" / "drink_water.mp4",
        llm_name="gemini",
    )

    assert dataset.task_list[0].status == "Incomplete"
    assert dataset.anomaly_list == []
    assert email_calls
    summary_dir = tmp_path / "reports" / fixed_time.strftime("%Y-%m-%d")
    assert summary_dir.exists()
    assert any(path.name.endswith("_daily_summary.txt") for path in summary_dir.iterdir())

