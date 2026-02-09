from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any

from domain.dataset import (
    Dataset,
    TaskItem,
    AnomalyItem,
    TASK_STATUS_COMPLETE,
    TASK_STATUS_INCOMPLETE,
    parse_repeated_count,
    format_repeated_status,
)


@dataclass
class EmailNotification:
    anomaly_type: str
    start_time: str
    end_time: str


@dataclass
class NotificationPlan:
    voice_reminder: bool = False
    email_notifications: List[EmailNotification] = field(default_factory=list)
    non_repeatable_violations: List[str] = field(default_factory=list)


def apply_analysis_report(dataset: Dataset, report: Dict[str, Any]) -> NotificationPlan:
    notifications = NotificationPlan()
    window = report.get("window", {})
    window_start = window.get("start_time")
    window_end = window.get("end_time")

    _apply_task_updates(dataset, report.get("tasks", []), notifications)
    _apply_anomaly_updates(dataset, report.get("anomalies", []), window_start, window_end, notifications)

    dataset.touch()
    return notifications


def _apply_task_updates(
    dataset: Dataset,
    tasks_report: List[Dict[str, Any]],
    notifications: NotificationPlan,
) -> None:
    tasks_by_type: Dict[str, List[TaskItem]] = {}
    for task in dataset.task_list:
        tasks_by_type.setdefault(task.task_type, []).append(task)

    for task_result in tasks_report:
        task_type = task_result.get("type")
        if not task_type or task_type not in tasks_by_type:
            continue

        match = task_result.get("match") is True

        for task in tasks_by_type[task_type]:
            if match:
                if task.status == TASK_STATUS_INCOMPLETE:
                    task.status = TASK_STATUS_COMPLETE
                else:
                    if task.if_repeatable:
                        current = parse_repeated_count(task.status)
                        task.status = format_repeated_status(current + 1)
                    else:
                        notifications.voice_reminder = True
                        if task_type not in notifications.non_repeatable_violations:
                            notifications.non_repeatable_violations.append(task_type)


def _apply_anomaly_updates(
    dataset: Dataset,
    anomalies_report: List[Dict[str, Any]],
    window_start: str,
    window_end: str,
    notifications: NotificationPlan,
) -> None:
    for anomaly_result in anomalies_report:
        if anomaly_result.get("match") is not True:
            continue

        anomaly_type = anomaly_result.get("type")
        if not anomaly_type:
            continue

        current_count = _current_anomaly_count(dataset, anomaly_type)
        new_count = current_count + 1
        dataset.anomaly_list.append(
            AnomalyItem(
                anomaly_type=anomaly_type,
                start_time=window_start or "",
                end_time=window_end or "",
                status=new_count,
            )
        )
        notifications.email_notifications.append(
            EmailNotification(
                anomaly_type=anomaly_type,
                start_time=window_start or "",
                end_time=window_end or "",
            )
        )


def _current_anomaly_count(dataset: Dataset, anomaly_type: str) -> int:
    counts = [item.status for item in dataset.anomaly_list if item.anomaly_type == anomaly_type]
    return max(counts, default=0)
