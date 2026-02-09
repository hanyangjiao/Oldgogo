from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

import yaml

sys.path.append(str(Path("src")))

from domain.dataset import Dataset, TaskItem
from domain.update_rules import apply_analysis_report
from ingestion.video_stream import slice_video_window
from ingestion.heart_rate import load_heart_rate_points, filter_heart_rate_window, HeartRatePoint
from ingestion.sync import strict_sync
from llm.client_factory import get_llm_client
from notification.cooldown import CooldownStore, CooldownTracker
from notification.email_notifier import send_email_notification
from notification.voice_notifier import send_voice_reminder
from reporting.daily_summary import save_daily_summary
from reporting.save_report import save_analysis_report
from scheduler.periodic_job import run_periodic
from scheduler.reset_job import should_reset, perform_reset
from validation.schema_validator import validate_analysis_report, validate_dataset


def load_config(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_dataset(config: Dict[str, Any]) -> Dataset:
    tasks = []
    for item in config.get("task_list", []):
        tasks.append(
            TaskItem(
                task_type=item["type"],
                start_time=item["start_time"],
                end_time=item["end_time"],
                status=item.get("status", "Incomplete"),
                if_repeatable=item.get("if_repeatable", False),
            )
        )
    dataset = Dataset(task_list=tasks, anomaly_list=[])
    dataset.touch()
    return dataset


def load_dataset_state(path: Path, config: Dict[str, Any]) -> Dataset:
    if path.exists():
        with open(path, "r", encoding="utf-8") as handle:
            return Dataset.from_dict(json.load(handle))
    return build_dataset(config)


def save_dataset_state(dataset: Dataset, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(dataset.to_dict(), handle, ensure_ascii=False, indent=2)


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


def validate_time_alignment(
    video_start: datetime,
    required_end: datetime,
    hr_points: list[HeartRatePoint],
) -> None:
    if not hr_points:
        raise ValueError("Heart rate data is empty; cannot align with video.")

    hr_times = sorted(datetime.fromisoformat(p.timestamp) for p in hr_points)
    hr_start = hr_times[0]
    hr_end = hr_times[-1]

    if hr_start > video_start or hr_end < required_end:
        raise ValueError(
            "Heart rate timestamps do not cover the video window. "
            f"HR range: {hr_start.isoformat()} ~ {hr_end.isoformat()}, "
            f"video range: {video_start.isoformat()} ~ {required_end.isoformat()}."
        )


def run_cycle(
    dataset: Dataset,
    config: Dict[str, Any],
    schema_dir: Path,
    reports_root: Path,
    heart_rate_path: Path | None,
    cooldown_tracker: CooldownTracker,
    cycle_index: int,
    window_start: datetime,
    window_end: datetime,
    mode: str,
    video_path: Path | None,
    llm_name: str,
    dataset_state_path: Path | None,
) -> None:
    if mode == "local":
        if not video_path or not video_path.exists():
            raise ValueError("Local mode requires a valid --video path.")
    if mode == "online":
        if not video_path or not video_path.exists():
            raise ValueError("Online mode requires a valid video path from --video-dir.")

    print(f"  Mode: {mode}")
    if video_path:
        print(f"  Video: {video_path.name}")
    print(f"  HR Source: {heart_rate_path.name if heart_rate_path else 'none'}")

    frames = slice_video_window(window_start, window_end, frame_rate=1.0)
    hr_points_all = load_heart_rate_points(heart_rate_path)
    hr_points = filter_heart_rate_window(hr_points_all, window_start, window_end)
    synced = strict_sync(frames, hr_points, window_start.isoformat())

    print(f"  Frames: {len(synced.frames)} | HR points: {len(synced.heart_rate)}")

    # Show heart rate statistics
    if synced.heart_rate:
        hr_values = [p.bpm for p in synced.heart_rate]
        avg_hr = sum(hr_values) / len(hr_values)
        min_hr = min(hr_values)
        max_hr = max(hr_values)
        print(f"  HR Stats: avg={avg_hr:.0f} bpm, range={min_hr}-{max_hr} bpm")

    client = get_llm_client(llm_name)
    print(f"  → Analyzing with {llm_name.upper()}...")
    report = client.analyze_window(
        task_types=[t.task_type for t in dataset.task_list],
        anomaly_types=config.get("anomaly_type_list", []),
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        frame_count=len(synced.frames),
        heart_rate_points=len(synced.heart_rate),
        dataset_snapshot=dataset.to_dict(),
        heart_rate_series=[{"timestamp": p.timestamp, "bpm": p.bpm} for p in synced.heart_rate],
        video_path=video_path,
    )
    print(f"  ← Analysis complete")

    # Show detected anomalies in current window
    detected_in_window = [a for a in report.get("anomalies", []) if a.get("match")]
    if detected_in_window:
        print(f"  ⚠ Anomalies detected in this window:")
        for anom in detected_in_window:
            print(f"     • {anom['type'].upper()}")
    else:
        print(f"  ✓ No anomalies detected in this window")

    for anomaly in report.get("anomalies", []):
        if anomaly.get("match") is False:
            anomaly["num_of_happens"] = 0
    validate_analysis_report(report, schema_dir)
    notifications = apply_analysis_report(dataset, report)
    validate_dataset(dataset.to_dict(), schema_dir)
    if dataset_state_path:
        save_dataset_state(dataset, dataset_state_path)

    report_path = save_analysis_report(report, reports_root, schema_dir, overwrite=(mode == "online"))
    print(f"  💾 Report: {report_path.name}")

    reminded = False
    if notifications.voice_reminder:
        reminded = send_voice_reminder(
            message="Repeated task detected but the task is not repeatable.",
            cooldown_tracker=cooldown_tracker,
        )

    for email in notifications.email_notifications:
        send_email_notification(
            contacts=config.get("emergency_contact", []),
            subject="Anomaly Alert",
            body=(
                "Anomaly detected\n"
                f"Type: {email.anomaly_type}\n"
                f"Time: {email.start_time} ~ {email.end_time}"
            ),
        )

    if not reminded:
        cooldown_tracker.tick()

    now_local = datetime.now()
    reset_cfg = config.get("reset_time", {})
    if reset_cfg.get("daily_reset") and should_reset(now_local, reset_cfg.get("time_local", "23:59")):
        summary_path = save_daily_summary(
            dataset.to_dict(), config.get("emergency_contact", []), reports_root, client
        )
        print(f"[INFO] Daily summary saved: {summary_path}")
        perform_reset(dataset)


def main() -> None:
    parser = argparse.ArgumentParser(description="Elder monitoring scheduler")
    parser.add_argument(
        "--config",
        default="src/config/default.yaml",
        help="Path to config yaml",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "online"],
        default="local",
        help="Data source mode: local uses files, online uses live streams",
    )
    parser.add_argument("--cycles", type=int, default=1, help="Number of inference cycles")
    parser.add_argument(
        "--llm",
        choices=["gemini", "gpt"],
        default="gemini",
        help="LLM provider (gemini or gpt)",
    )
    parser.add_argument("--hr", type=str, default=None, help="Optional heart rate json path")
    parser.add_argument("--video", type=str, default=None, help="Local video path (local mode)")
    parser.add_argument(
        "--video-dir",
        type=str,
        default=None,
        help="Directory with videos for online mode (simulated)",
    )
    parser.add_argument(
        "--video-start",
        type=str,
        default=None,
        help="Video start time ISO8601 (local mode)",
    )
    parser.add_argument(
        "--dataset-state",
        type=str,
        default="output/state_out/dataset_state.json",
        help="Dataset state path for cross-video accumulation (online mode)",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Reset dataset state before running (online mode)",
    )
    args = parser.parse_args()

    print(f"[INFO] Config: {args.config}")
    config = load_config(Path(args.config))
    dataset = build_dataset(config)
    schema_dir = Path("spec/schema")
    reports_root = Path("reports")
    print(f"[INFO] Schema directory: {schema_dir}")
    print(f"[INFO] Reports directory: {reports_root}")

    cooldown_cfg = config.get("cooldown", {})
    cooldown_tracker = CooldownTracker(
        cycles_after_reminder=cooldown_cfg.get("cooldown_cycles_after_voice_reminder", 0),
        store=CooldownStore(Path("output/state_out/cooldown_state.json")),
    )

    interval_minutes = cooldown_cfg.get("inference_cycle_minutes", 3)
    if args.mode == "online":
        if not args.video_dir or not args.video_start:
            raise ValueError("Online mode requires --video-dir and --video-start.")
        video_dir = Path(args.video_dir)
        if not video_dir.exists() or not video_dir.is_dir():
            raise ValueError("Online mode requires a valid --video-dir directory.")

        dataset_state_path = Path(args.dataset_state)
        if args.reset_state and dataset_state_path.exists():
            dataset_state_path.unlink()
        dataset = load_dataset_state(dataset_state_path, config)

        # Filter to only videos with "_first" suffix (e.g., drink_water_first.mp4, falldown_first.mp4)
        videos = sorted([
            p for p in video_dir.iterdir()
            if p.is_file() and p.stem.endswith('_first')
        ])
        if not videos:
            raise ValueError("No video files with '_first' suffix found in --video-dir.")

        limit = args.cycles if args.cycles > 0 else len(videos)
        current_start = datetime.fromisoformat(args.video_start)

        print("\n" + "=" * 70)
        print(f"ONLINE MODE: Processing {min(limit, len(videos))} videos")
        print("=" * 70)

        for idx, video_path in enumerate(videos[:limit]):
            duration_seconds = _video_duration_seconds(video_path)
            window_start = current_start
            window_end = window_start + timedelta(seconds=duration_seconds)

            # Enhanced progress display
            print(f"\n{'─' * 70}")
            print(f"[VIDEO {idx + 1}/{min(limit, len(videos))}] {video_path.name}")
            print(f"{'─' * 70}")
            print(f"  Duration: {duration_seconds}s")
            print(f"  Window: {window_start.strftime('%H:%M:%S')} → {window_end.strftime('%H:%M:%S')}")
            run_cycle(
                dataset,
                config,
                schema_dir,
                reports_root,
                Path(args.hr) if args.hr else None,
                cooldown_tracker,
                idx,
                window_start,
                window_end,
                args.mode,
                video_path,
                args.llm,
                dataset_state_path,
            )

            print(f"  ✓ Video {idx + 1} processed successfully")
            current_start = window_end

        print(f"\n{'═' * 70}")
        print(f"PROCESSING COMPLETE: {min(limit, len(videos))} videos analyzed")
        print(f"{'═' * 70}\n")
        return

    if not args.video or not args.video_start:
        raise ValueError("Local mode requires --video and --video-start.")

    base_start = datetime.fromisoformat(args.video_start)
    print(f"[INFO] Video start: {base_start.isoformat()}")
    video_duration_seconds = _video_duration_seconds(Path(args.video))
    video_end = base_start + timedelta(seconds=video_duration_seconds)
    requested_end = base_start + timedelta(minutes=interval_minutes * args.cycles)
    effective_end = min(video_end, requested_end)

    if args.hr:
        hr_points_all = load_heart_rate_points(Path(args.hr))
        print(f"[INFO] Total heart rate points loaded: {len(hr_points_all)}")
        validate_time_alignment(base_start, effective_end, hr_points_all)

    if video_end < requested_end:
        print(
            "[INFO] Video shorter than configured window; "
            "using video duration for window end."
        )

    for idx in range(args.cycles):
        window_start = base_start + timedelta(minutes=interval_minutes * idx)
        if window_start >= video_end:
            break
        window_end = min(window_start + timedelta(minutes=interval_minutes), video_end)
        run_cycle(
            dataset,
            config,
            schema_dir,
            reports_root,
            Path(args.hr) if args.hr else None,
            cooldown_tracker,
            idx,
            window_start,
            window_end,
            args.mode,
            Path(args.video),
            args.llm,
            None,
        )


if __name__ == "__main__":
    main()
