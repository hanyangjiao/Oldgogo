import argparse
import json
import math
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from random import randint


def generate_series(
    start_time: str,
    duration_seconds: int,
    interval_seconds: int,
    base_bpm: int,
    jitter: int,
) -> list[dict]:
    start = datetime.fromisoformat(start_time)
    end = start + timedelta(seconds=max(duration_seconds, 1))
    points = []
    current = start
    while current <= end:
        bpm = base_bpm + randint(-jitter, jitter)
        points.append({"timestamp": current.isoformat(), "bpm": bpm})
        current += timedelta(seconds=interval_seconds)
    return points


def _video_duration_seconds(path: Path) -> int:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    duration_str = result.stdout.strip()
    if not duration_str:
        raise RuntimeError(f"Failed to read duration for {path}")
    return math.ceil(float(duration_str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic heart rate data")
    parser.add_argument("--start", required=True, help="ISO8601 start time")
    parser.add_argument("--minutes", type=int, default=15, help="Duration in minutes")
    parser.add_argument("--interval-sec", type=int, default=60, help="Sampling interval in seconds")
    parser.add_argument("--video", type=str, default=None, help="Optional video path to derive duration")
    parser.add_argument("--base-bpm", type=int, default=75, help="Base bpm value")
    parser.add_argument("--jitter", type=int, default=5, help="Random jitter per point")
    parser.add_argument("--out", required=True, help="Output json path")
    args = parser.parse_args()

    duration_seconds = args.minutes * 60
    interval_seconds = args.interval_sec
    if args.video:
        duration_seconds = _video_duration_seconds(Path(args.video))
        interval_seconds = 1

    data = generate_series(
        args.start,
        duration_seconds,
        interval_seconds,
        args.base_bpm,
        args.jitter,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    print(f"[INFO] Heart rate data generated and saved to {out_path}")


if __name__ == "__main__":
    main()

