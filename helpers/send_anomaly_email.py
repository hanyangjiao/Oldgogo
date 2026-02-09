from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from notification.email_notifier import send_email_notification


def _load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _find_latest_report(reports_root: Path) -> Optional[Path]:
    if not reports_root.exists():
        return None
    candidates = list(reports_root.rglob("*_analysis_report.json"))
    if not candidates:
        latest_path = reports_root / "latest_analysis_report.json"
        return latest_path if latest_path.exists() else None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _load_report(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_anomalies(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    anomalies = report.get("anomalies", [])
    if not isinstance(anomalies, list):
        return []
    return [a for a in anomalies if isinstance(a, dict) and a.get("match")]


def _render_body(report: Dict[str, Any], matches: List[Dict[str, Any]]) -> str:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Send email when anomaly occurs")
    parser.add_argument(
        "--config",
        type=str,
        default="src/config/default.yaml",
        help="Path to config yaml with emergency_contact",
    )
    parser.add_argument(
        "--report",
        type=str,
        default="",
        help="Path to analysis report JSON (default: latest in reports/)",
    )
    parser.add_argument(
        "--reports-root",
        type=str,
        default="reports",
        help="Reports root (used when --report is not provided)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    report_path = Path(args.report) if args.report else None
    if report_path is None:
        report_path = _find_latest_report(Path(args.reports_root))
    if report_path is None or not report_path.exists():
        raise FileNotFoundError("No analysis report found to process.")

    config = _load_yaml(config_path)
    report = _load_report(report_path)
    matches = _extract_anomalies(report)
    if not matches:
        print("[INFO] No anomalies detected. No email sent.")
        return 0

    subject = "Anomaly Alert"
    body = _render_body(report, matches)
    send_email_notification(config.get("emergency_contact", []), subject, body)
    print(f"[INFO] Anomaly email sent for report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
