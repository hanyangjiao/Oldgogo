from __future__ import annotations

from datetime import datetime

from domain.dataset import Dataset, TASK_STATUS_INCOMPLETE


def should_reset(now_local: datetime, reset_time_local: str) -> bool:
    target = datetime.strptime(reset_time_local, "%H:%M").time()
    return now_local.time().hour == target.hour and now_local.time().minute == target.minute


def perform_reset(dataset: Dataset) -> None:
    for task in dataset.task_list:
        task.status = TASK_STATUS_INCOMPLETE
    dataset.anomaly_list.clear()
    dataset.touch()

