from __future__ import annotations

from pathlib import Path

import pytest

import app.main as app_main


def test_online_mode_processes_first_videos_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("task_list: []\nanomaly_type_list: []\n", encoding="utf-8")

    video_dir = tmp_path / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    (video_dir / "drink_water_first.mp4").write_bytes(b"")
    (video_dir / "falldown_first.mp4").write_bytes(b"")
    (video_dir / "other.mp4").write_bytes(b"")

    calls = []

    def _fake_run_cycle(*args, **kwargs):
        if "video_path" in kwargs:
            calls.append(kwargs.get("video_path"))
        else:
            calls.append(args[10])

    monkeypatch.setattr(app_main, "_video_duration_seconds", lambda _p: 2)
    monkeypatch.setattr(app_main, "run_cycle", _fake_run_cycle)

    monkeypatch.setattr(
        "sys.argv",
        [
            "main.py",
            "--config",
            str(config_path),
            "--mode",
            "online",
            "--video-dir",
            str(video_dir),
            "--video-start",
            "2026-01-16T09:00:00+08:00",
            "--cycles",
            "0",
        ],
    )

    app_main.main()

    names = [Path(p).name for p in calls]
    assert names == ["drink_water_first.mp4", "falldown_first.mp4"]
