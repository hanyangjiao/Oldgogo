from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List


@dataclass
class VideoFrame:
    frame_id: int
    timestamp: str


def slice_video_window(
    window_start: datetime,
    window_end: datetime,
    frame_rate: float = 1.0,
) -> List[VideoFrame]:
    if window_end <= window_start:
        raise ValueError("window_end must be after window_start")

    total_seconds = (window_end - window_start).total_seconds()
    frame_count = max(1, int(total_seconds * frame_rate))

    frames: List[VideoFrame] = []
    for idx in range(frame_count):
        timestamp = window_start + timedelta(seconds=idx / frame_rate)
        frames.append(VideoFrame(frame_id=idx, timestamp=timestamp.isoformat()))
    return frames

