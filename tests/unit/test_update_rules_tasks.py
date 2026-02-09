# Covers: F6, F8
from domain.dataset import Dataset, TaskItem
from domain.update_rules import apply_analysis_report


def test_task_incomplete_to_complete():
    dataset = Dataset(
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
    report = {
        "window": {
            "start_time": "2026-01-16T09:00:00+08:00",
            "end_time": "2026-01-16T09:03:00+08:00",
        },
        "tasks": [
            {
                "type": "drink_water",
                "match": True,
                "repeated_count": 1,
                "reason": "Detected once.",
            }
        ],
        "anomalies": [],
    }
    notifications = apply_analysis_report(dataset, report)
    assert dataset.task_list[0].status == "Complete"
    assert notifications.voice_reminder is False


def test_repeatable_task_increments():
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
        anomaly_list=[],
    )
    report = {
        "window": {
            "start_time": "2026-01-16T09:00:00+08:00",
            "end_time": "2026-01-16T09:03:00+08:00",
        },
        "tasks": [
            {
                "type": "drink_water",
                "match": True,
                "repeated_count": 1,
                "reason": "Repeated detected.",
            }
        ],
        "anomalies": [],
    }
    notifications = apply_analysis_report(dataset, report)
    assert dataset.task_list[0].status == "Repeated(1)"
    assert notifications.voice_reminder is False


def test_non_repeatable_task_triggers_voice():
    dataset = Dataset(
        task_list=[
            TaskItem(
                task_type="take_medicine",
                start_time="2026-01-16T09:00:00+08:00",
                end_time="2026-01-16T09:05:00+08:00",
                status="Complete",
                if_repeatable=False,
            )
        ],
        anomaly_list=[],
    )
    report = {
        "window": {
            "start_time": "2026-01-16T09:00:00+08:00",
            "end_time": "2026-01-16T09:03:00+08:00",
        },
        "tasks": [
            {
                "type": "take_medicine",
                "match": True,
                "repeated_count": 1,
                "reason": "Repeated detected.",
            }
        ],
        "anomalies": [],
    }
    notifications = apply_analysis_report(dataset, report)
    assert dataset.task_list[0].status == "Complete"
    assert notifications.voice_reminder is True

