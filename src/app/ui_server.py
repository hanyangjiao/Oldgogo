#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
VIDEO_DIR = REPO_ROOT / "data" / "videos"
CONFIG_PATH = REPO_ROOT / "src" / "config" / "default.yaml"
SCHEMA_DIR = REPO_ROOT / "spec" / "schema"
NOTIFICATION_DIR = REPO_ROOT / "output" / "notifications"
REPORTS_DIR = REPO_ROOT / "reports"
LATEST_REPORT_PATH = REPORTS_DIR / "latest_analysis_report.json"

DATASET_STATE = None
LATEST_REPORT_STATE = None

sys.path.append(str(SRC_ROOT))
sys.path.append(str(REPO_ROOT))

from app.main import build_dataset, load_config  # noqa: E402
from domain.update_rules import apply_analysis_report  # noqa: E402
from helpers.generate_hr import generate_series  # noqa: E402
from llm.client_factory import get_llm_client  # noqa: E402
from validation.schema_validator import validate_analysis_report  # noqa: E402

HR_TYPES: Dict[str, Dict[str, Any]] = {
    "normal": {"label": "Normal (75 bpm)", "base_bpm": 75, "jitter": 5},
    "tachycardia": {"label": "Tachycardia (120 bpm)", "base_bpm": 120, "jitter": 8},
    "bradycardia": {"label": "Bradycardia (45 bpm)", "base_bpm": 45, "jitter": 3},
}


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
    return max(1, int(float(duration_str) + 0.5))


def _label_from_stem(stem: str) -> str:
    base = stem.replace("_h264", "")
    is_first = base.endswith("_first")
    if is_first:
        base = base[: -len("_first")]
    label = base.replace("_", " ").title()
    if is_first:
        label = f"{label} (First Angle)"
    return label


def list_video_options() -> List[Dict[str, Any]]:
    if not VIDEO_DIR.exists():
        return []
    candidates: Dict[str, Path] = {}
    for path in sorted(VIDEO_DIR.glob("*.mp4")):
        if "_first" not in path.stem:
            continue
        base = path.stem.replace("_h264", "")
        if base not in candidates or path.stem.endswith("_h264"):
            candidates[base] = path

    options = []
    for base, path in sorted(candidates.items()):
        options.append(
            {
                "id": base,
                "file": path.name,
                "label": _label_from_stem(path.stem),
                "path": f"data/videos/{path.name}",
            }
        )
    return options


def list_hr_types() -> List[Dict[str, Any]]:
    options = []
    for key, meta in HR_TYPES.items():
        options.append(
            {
                "id": key,
                "label": meta["label"],
                "base_bpm": meta["base_bpm"],
                "jitter": meta["jitter"],
            }
        )
    return options


def _resolve_in_dir(base: Path, filename: str) -> Path:
    candidate = (base / filename).resolve()
    if base not in candidate.parents and candidate != base:
        raise ValueError("Invalid path selection")
    if not candidate.exists():
        raise FileNotFoundError(f"File not found: {filename}")
    return candidate


def run_inference(video_id: str, hr_type_id: str) -> Dict[str, Any]:
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set in the environment.")

    videos = {option["id"]: option for option in list_video_options()}
    heart_rate_types = {option["id"]: option for option in list_hr_types()}

    if video_id not in videos:
        raise ValueError("Unknown video selection.")
    if hr_type_id not in heart_rate_types:
        raise ValueError("Unknown heart rate type.")

    video_option = videos[video_id]
    hr_option = heart_rate_types[hr_type_id]

    video_path = _resolve_in_dir(VIDEO_DIR, video_option["file"])
    video_duration = _video_duration_seconds(video_path)

    window_start = datetime.now().astimezone()
    series_duration = max(0, video_duration - 1)
    window_end = window_start + timedelta(seconds=series_duration)

    hr_series = generate_series(
        window_start.isoformat(),
        series_duration,
        1,
        hr_option["base_bpm"],
        hr_option["jitter"],
    )
    hr_series = [
        point
        for point in hr_series
        if datetime.fromisoformat(point["timestamp"]) <= window_end
    ]
    if not hr_series:
        raise ValueError("Failed to generate heart rate series.")

    frame_count = max(1, video_duration)

    config = load_config(CONFIG_PATH)
    global DATASET_STATE
    if DATASET_STATE is None:
        DATASET_STATE = build_dataset(config)
    dataset = DATASET_STATE
    task_types = [item["type"] for item in config.get("task_list", [])]
    anomaly_types = config.get("anomaly_type_list", [])

    client = get_llm_client("gemini")
    report = client.analyze_window(
        task_types=task_types,
        anomaly_types=anomaly_types,
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        frame_count=frame_count,
        heart_rate_points=len(hr_series),
        dataset_snapshot=dataset.to_dict(),
        heart_rate_series=hr_series,
        video_path=video_path,
    )

    validate_analysis_report(report, SCHEMA_DIR)

    notifications = apply_analysis_report(dataset, report)
    report["dataset_snapshot"] = dataset.to_dict()
    if "notifications" not in report or not isinstance(report.get("notifications"), dict):
        report["notifications"] = {}
    if notifications.voice_reminder or notifications.non_repeatable_violations:
        report["notifications"]["voice_reminder"] = True
    report["notifications"]["non_repeatable_violations"] = notifications.non_repeatable_violations

    human_report = client.summarize_report(report)

    _write_email_preview(report)
    _update_latest_report(report, {
        "video_id": video_option["id"],
        "video_label": video_option["label"],
        "video_file": video_option["file"],
        "hr_type_id": hr_option["id"],
        "hr_type_label": hr_option["label"],
        "hr_base_bpm": hr_option["base_bpm"],
        "hr_jitter": hr_option["jitter"],
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "frame_count": frame_count,
        "heart_rate_points": len(hr_series),
    }, human_report)

    return {
        "report": report,
        "human_report": human_report,
        "input": {
            "video_id": video_option["id"],
            "video_label": video_option["label"],
            "video_file": video_option["file"],
            "hr_type_id": hr_option["id"],
            "hr_type_label": hr_option["label"],
            "hr_base_bpm": hr_option["base_bpm"],
            "hr_jitter": hr_option["jitter"],
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "frame_count": frame_count,
            "heart_rate_points": len(hr_series),
        },
        "heart_rate_series": hr_series,
        "non_repeatable_violations": notifications.non_repeatable_violations,
    }


def _extract_anomalies(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    anomalies = report.get("anomalies", [])
    if not isinstance(anomalies, list):
        return []
    return [a for a in anomalies if isinstance(a, dict) and a.get("match")]


def _render_email_body(report: Dict[str, Any], matches: List[Dict[str, Any]]) -> str:
    lines = ["Anomaly detected in the latest analysis report.", ""]
    window = report.get("window") or {}
    if window.get("start_time") and window.get("end_time"):
        lines.append(f"Window: {window['start_time']} → {window['end_time']}")
        lines.append("")
    lines.append("Detected anomalies:")
    for item in matches:
        reason = item.get("reason", "").strip()
        if reason:
            lines.append(f"- {item.get('type', 'unknown')}: {reason}")
        else:
            lines.append(f"- {item.get('type', 'unknown')}")
    return "\n".join(lines)


def _write_email_preview(report: Dict[str, Any]) -> None:
    matches = _extract_anomalies(report)
    if not matches:
        return
    body = _render_email_body(report, matches)
    NOTIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = NOTIFICATION_DIR / f"email_{timestamp}.txt"
    content = f"Subject: Anomaly Alert\n\n{body}"
    path.write_text(content, encoding="utf-8")


def _update_latest_report(report: Dict[str, Any], input_data: Dict[str, Any], human_report: str) -> None:
    global LATEST_REPORT_STATE
    now = datetime.utcnow().isoformat() + "Z"
    if LATEST_REPORT_STATE is None:
        LATEST_REPORT_STATE = {
            "schema_version": report.get("schema_version", "1.0"),
            "started_at": now,
            "last_updated": now,
            "items": [],
        }
    LATEST_REPORT_STATE["last_updated"] = now
    LATEST_REPORT_STATE["latest_report"] = report
    LATEST_REPORT_STATE["latest_input"] = input_data
    LATEST_REPORT_STATE["latest_human_report"] = human_report
    LATEST_REPORT_STATE["dataset_snapshot"] = report.get("dataset_snapshot", {})
    LATEST_REPORT_STATE["items"].append(
        {
            "timestamp": report.get("timestamp"),
            "input": input_data,
            "report": report,
            "human_report": human_report,
        }
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_REPORT_PATH.write_text(
        json.dumps(LATEST_REPORT_STATE, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class UIRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_response(302)
            self.send_header("Location", "/src/app/ui/")
            self.end_headers()
            return

        if parsed.path == "/api/options":
            payload = {
                "videos": list_video_options(),
                "hr_types": list_hr_types(),
            }
            self._send_json(200, payload)
            return
        if parsed.path == "/api/latest-email":
            latest = None
            if NOTIFICATION_DIR.exists():
                candidates = sorted(
                    NOTIFICATION_DIR.glob("email_*.txt"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                latest = candidates[0] if candidates else None
            if latest and latest.exists():
                body = latest.read_text(encoding="utf-8")
                self._send_json(200, {"ok": True, "body": body})
            else:
                self._send_json(200, {"ok": False, "body": ""})
            return
        if parsed.path == "/api/latest-report":
            if LATEST_REPORT_PATH.exists():
                body = LATEST_REPORT_PATH.read_text(encoding="utf-8")
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    data = {}
                self._send_json(200, {"ok": True, "data": data})
            else:
                self._send_json(200, {"ok": False, "data": {}})
            return

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/reset":
            global DATASET_STATE
            DATASET_STATE = None
            global LATEST_REPORT_STATE
            LATEST_REPORT_STATE = None
            if LATEST_REPORT_PATH.exists():
                LATEST_REPORT_PATH.unlink()
            self._send_json(200, {"ok": True})
            return
        if parsed.path != "/api/infer":
            self._send_json(404, {"ok": False, "error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b""
            payload = json.loads(raw.decode("utf-8")) if raw else {}
            video_id = payload.get("video_id")
            hr_type_id = payload.get("hr_type")
            if not video_id or not hr_type_id:
                raise ValueError("video_id and hr_type are required")

            result = run_inference(video_id, hr_type_id)
            response = {"ok": True, **result}
            self._send_json(200, response)
        except Exception as exc:  # noqa: BLE001
            error_payload = {
                "ok": False,
                "error": str(exc),
                "trace": traceback.format_exc().splitlines()[-5:],
            }
            self._send_json(500, error_payload)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    parser = argparse.ArgumentParser(description="Elder Monitor UI server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), UIRequestHandler)
    print(f"[UI] Serving on http://{args.host}:{args.port}/src/app/ui/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
