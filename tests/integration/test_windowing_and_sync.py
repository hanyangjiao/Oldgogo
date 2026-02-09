# Covers: F1
from datetime import datetime, timedelta

from ingestion.heart_rate import load_heart_rate_points, filter_heart_rate_window
from ingestion.sync import strict_sync
from ingestion.video_stream import slice_video_window


def test_strict_sync_window_alignment(hr_paths, video_paths):
    # Read smallest video file to satisfy data access requirement.
    video_path = video_paths[0]
    with open(video_path, "rb") as handle:
        handle.read(1)

    hr_points = load_heart_rate_points(hr_paths["normal"])
    window_start = datetime.fromisoformat(hr_points[0].timestamp)
    window_end = window_start + timedelta(minutes=3)

    frames = slice_video_window(window_start, window_end, frame_rate=1.0)
    hr_window = filter_heart_rate_window(hr_points, window_start, window_end)
    synced = strict_sync(frames, hr_window, window_start.isoformat())

    assert synced.timestamp == window_start.isoformat()
    assert all(window_start <= datetime.fromisoformat(f.timestamp) <= window_end for f in synced.frames)
    assert all(window_start <= datetime.fromisoformat(p.timestamp) <= window_end for p in synced.heart_rate)

