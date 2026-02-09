from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Callable


def run_periodic(
    callback: Callable[[datetime, datetime, int], None],
    interval_minutes: int,
    cycles: int = 1,
) -> None:
    for cycle in range(cycles):
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(minutes=interval_minutes)
        callback(window_start, window_end, cycle)
        if cycle < cycles - 1:
            time.sleep(interval_minutes * 60)

