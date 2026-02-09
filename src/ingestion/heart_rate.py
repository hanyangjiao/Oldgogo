from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class HeartRatePoint:
    timestamp: str
    bpm: int


def load_heart_rate_points(path: Optional[Path]) -> List[HeartRatePoint]:
    if path is None:
        return []
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    points = []
    for item in data:
        points.append(HeartRatePoint(timestamp=item["timestamp"], bpm=int(item["bpm"])))
    return points


def filter_heart_rate_window(
    points: List[HeartRatePoint],
    window_start: datetime,
    window_end: datetime,
) -> List[HeartRatePoint]:
    if not points:
        return []

    start = window_start
    end = window_end

    filtered = []
    for point in points:
        ts = datetime.fromisoformat(point.timestamp)
        if start <= ts <= end:
            filtered.append(point)
    return filtered

