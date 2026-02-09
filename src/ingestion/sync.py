from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ingestion.video_stream import VideoFrame
from ingestion.heart_rate import HeartRatePoint


@dataclass
class SyncedWindow:
    frames: List[VideoFrame]
    heart_rate: List[HeartRatePoint]
    timestamp: str


def strict_sync(
    frames: List[VideoFrame],
    heart_rate: List[HeartRatePoint],
    timestamp: str,
) -> SyncedWindow:
    if not frames:
        raise ValueError("frames must be non-empty for strict sync")
    return SyncedWindow(frames=frames, heart_rate=heart_rate, timestamp=timestamp)

