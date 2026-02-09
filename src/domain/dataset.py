from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


TASK_STATUS_INCOMPLETE = "Incomplete"
TASK_STATUS_COMPLETE = "Complete"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_repeated_status(status: str) -> bool:
    return status.startswith("Repeated(") and status.endswith(")")


def parse_repeated_count(status: str) -> int:
    if not is_repeated_status(status):
        return 0
    inner = status[len("Repeated(") : -1]
    try:
        return int(inner)
    except ValueError:
        return 0


def format_repeated_status(count: int) -> str:
    return f"Repeated({max(count, 1)})"


@dataclass
class TaskItem:
    task_type: str
    start_time: str
    end_time: str
    status: str = TASK_STATUS_INCOMPLETE
    if_repeatable: bool = False

    def to_dict(self) -> dict:
        return {
            "type": self.task_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "if_repeatable": self.if_repeatable,
        }


@dataclass
class AnomalyItem:
    anomaly_type: str
    start_time: str
    end_time: str
    status: int

    def to_dict(self) -> dict:
        return {
            "type": self.anomaly_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
        }


@dataclass
class Dataset:
    task_list: List[TaskItem] = field(default_factory=list)
    anomaly_list: List[AnomalyItem] = field(default_factory=list)
    last_updated: Optional[str] = None

    def touch(self) -> None:
        self.last_updated = _now_iso()

    def to_dict(self) -> dict:
        payload = {
            "task_list": [task.to_dict() for task in self.task_list],
            "anomaly_list": [anomaly.to_dict() for anomaly in self.anomaly_list],
        }
        if self.last_updated:
            payload["last_updated"] = self.last_updated
        return payload

    @classmethod
    def from_dict(cls, data: dict) -> "Dataset":
        task_list = [
            TaskItem(
                task_type=item["type"],
                start_time=item["start_time"],
                end_time=item["end_time"],
                status=item.get("status", TASK_STATUS_INCOMPLETE),
                if_repeatable=item.get("if_repeatable", False),
            )
            for item in data.get("task_list", [])
        ]
        anomaly_list = [
            AnomalyItem(
                anomaly_type=item["type"],
                start_time=item["start_time"],
                end_time=item["end_time"],
                status=item["status"],
            )
            for item in data.get("anomaly_list", [])
        ]
        return cls(
            task_list=task_list,
            anomaly_list=anomaly_list,
            last_updated=data.get("last_updated"),
        )

