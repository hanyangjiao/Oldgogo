# Covers: F10
from datetime import datetime

import pytest

import reporting.save_report as save_report
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
        "tasks": [],
        "anomalies": [],
        "dataset_snapshot": {"task_list": [], "anomaly_list": []},
        "notifications": {
            "voice_reminder": False,
            "email_sent": False,
            "cooldown_active": False,
            "recipients": [],
        },
    }


def test_report_saved_with_timestamp(monkeypatch, repo_root, tmp_path, fixed_time):
    class _FixedDateTime(datetime):
        @classmethod
        def now(cls):
            return fixed_time

    monkeypatch.setattr(save_report, "datetime", _FixedDateTime)
    report = _valid_report()
    path = save_report.save_analysis_report(report, tmp_path, repo_root / "spec" / "schema")

    assert path.exists()
    assert path.name.endswith("_analysis_report.json")
    assert fixed_time.strftime("%Y-%m-%d") in str(path)
    assert fixed_time.strftime("%H%M%S") in path.name


def test_report_schema_gate(monkeypatch, repo_root, tmp_path):
    report = {"schema_version": "1.0"}
    with pytest.raises(SchemaValidationError):
        save_report.save_analysis_report(report, tmp_path, repo_root / "spec" / "schema")

