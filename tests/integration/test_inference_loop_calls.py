# Covers: F2, F5, F9
from datetime import datetime

import pytest

import app.main as app_main
from llm.gemini_client import GeminiClient
from llm.prompt_templates import build_analysis_prompt
from domain.dataset import Dataset, TaskItem
from scheduler.periodic_job import run_periodic
from validation.schema_validator import SchemaValidationError


def _valid_report():
    return {
        "schema_version": "1.0",
        "window": {
            "start_time": "2026-01-16T09:00:00+08:00",
            "end_time": "2026-01-16T09:03:00+08:00",
        },
        "timestamp": "2026-01-16T09:03:00+08:00",
        "inputs": {"frame_count": 60, "heart_rate_points": 0},
        "tasks": [
            {
                "type": "drink_water",
                "match": False,
                "repeated_count": 0,
                "reason": "No evidence",
            }
        ],
        "anomalies": [
            {
                "type": "falldown",
                "match": False,
                "num_of_happens": 0,
                "reason": "No evidence",
            }
        ],
        "dataset_snapshot": {"task_list": [], "anomaly_list": []},
        "notifications": {
            "voice_reminder": False,
            "email_sent": False,
            "cooldown_active": False,
            "recipients": [],
        },
    }


def _make_dataset():
    return Dataset(
        task_list=[
            TaskItem(
                task_type="drink_water",
                start_time="2026-01-16T09:00:00+08:00",
                end_time="2026-01-16T09:05:00+08:00",
                status="Incomplete",
                if_repeatable=True,
            )
        ],
        anomaly_list=[],
    )


def test_inference_loop_calls_once_per_window(monkeypatch, repo_root, tmp_path, require_api_key):
    calls = []

    class _CountingGemini(GeminiClient):
        def analyze_window(self, **kwargs):
            calls.append(kwargs)
            assert "window_start" in kwargs and "window_end" in kwargs
            assert "dataset_snapshot" in kwargs
            assert "heart_rate_series" in kwargs
            return super().analyze_window(**kwargs)

    monkeypatch.setattr(app_main, "get_llm_client", lambda name: _CountingGemini())
    monkeypatch.setattr("scheduler.periodic_job.time.sleep", lambda *_: None)

    dataset = _make_dataset()
    config = {"anomaly_type_list": ["falldown"]}
    prompt = build_analysis_prompt(
        [t.task_type for t in dataset.task_list],
        config["anomaly_type_list"],
        "2026-01-16T09:00:00+08:00",
        "2026-01-16T09:03:00+08:00",
        180,
        0,
    )
    assert isinstance(prompt, str) and prompt

    def _callback(start, end, idx):
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
            cycle_index=idx,
            window_start=start,
            window_end=end,
            mode="local",
            video_path=repo_root / "data" / "videos" / "drink_water.mp4",
            llm_name="gemini",
        )

    run_periodic(_callback, interval_minutes=3, cycles=2)
    assert len(calls) == 2


def test_invalid_report_blocks_dataset_update(monkeypatch, repo_root, tmp_path, require_api_key):
    dataset = _make_dataset()
    before = dataset.to_dict()

    class _BadGemini(GeminiClient):
        def analyze_window(self, **kwargs):
            report = super().analyze_window(**kwargs)
            report.pop("timestamp", None)
            return report

    monkeypatch.setattr(app_main, "get_llm_client", lambda name: _BadGemini())

    with pytest.raises(SchemaValidationError):
        app_main.run_cycle(
            dataset=dataset,
            config={"anomaly_type_list": []},
            schema_dir=repo_root / "spec" / "schema",
            reports_root=tmp_path / "reports",
            heart_rate_path=None,
            cooldown_tracker=app_main.CooldownTracker(
                cycles_after_reminder=0,
                store=app_main.CooldownStore(tmp_path / "cooldown.json"),
            ),
            cycle_index=0,
            window_start=datetime.fromisoformat("2026-01-16T09:00:00+08:00"),
            window_end=datetime.fromisoformat("2026-01-16T09:03:00+08:00"),
            mode="local",
            video_path=repo_root / "data" / "videos" / "drink_water.mp4",
            llm_name="gemini",
        )

    assert dataset.to_dict() == before


def test_anomaly_email_notification_template(monkeypatch, repo_root, tmp_path, require_api_key):
    sent = []

    def _fake_email(contacts, subject, body):
        sent.append({"contacts": contacts, "subject": subject, "body": body})

    monkeypatch.setattr(app_main, "send_email_notification", _fake_email)

    dataset = _make_dataset()
    config = {
        "anomaly_type_list": ["falldown"],
        "emergency_contact": [{"name": "Test", "relationship": "son", "email": "test@example.com"}],
        "reset_time": {"daily_reset": False},
    }

    app_main.run_cycle(
        dataset=dataset,
        config=config,
        schema_dir=repo_root / "spec" / "schema",
        reports_root=tmp_path / "reports",
        heart_rate_path=repo_root / "data" / "hr" / "hr_tachycardia.json",
        cooldown_tracker=app_main.CooldownTracker(
            cycles_after_reminder=0,
            store=app_main.CooldownStore(tmp_path / "cooldown.json"),
        ),
        cycle_index=0,
        window_start=datetime.fromisoformat("2026-01-16T09:00:00+08:00"),
        window_end=datetime.fromisoformat("2026-01-16T09:03:00+08:00"),
        mode="local",
        video_path=repo_root / "data" / "videos" / "drink_water.mp4",
        llm_name="gemini",
    )

    assert len(sent) == 1
    assert sent[0]["subject"] == "Anomaly Alert"
    assert "Type: falldown" in sent[0]["body"]
    assert "Time:" in sent[0]["body"]

