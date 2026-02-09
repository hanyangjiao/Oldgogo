# Covers: F5
import pytest

from validation.schema_validator import SchemaValidationError, validate_analysis_report


def test_report_schema_valid(repo_root):
    schema_dir = repo_root / "spec" / "schema"
    report = {
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
    validate_analysis_report(report, schema_dir)


def test_report_schema_invalid(repo_root):
    schema_dir = repo_root / "spec" / "schema"
    report = {"schema_version": "1.0", "tasks": [], "anomalies": []}
    with pytest.raises(SchemaValidationError):
        validate_analysis_report(report, schema_dir)

