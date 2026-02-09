# Covers: F7
from domain.dataset import Dataset, TaskItem
from domain.update_rules import apply_analysis_report


def test_multiple_anomalies_append_and_increment():
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
        "tasks": [],
        "anomalies": [
            {
                "type": "falldown",
                "match": True,
                "num_of_happens": 1,
                "reason": "Detected.",
            },
            {
                "type": "tachycardia",
                "match": True,
                "num_of_happens": 1,
                "reason": "Detected.",
            },
        ],
    }
    notifications = apply_analysis_report(dataset, report)
    assert len(dataset.anomaly_list) == 2
    assert {a.anomaly_type for a in dataset.anomaly_list} == {"falldown", "tachycardia"}
    assert all(a.status == 1 for a in dataset.anomaly_list)
    assert len(notifications.email_notifications) == 2

