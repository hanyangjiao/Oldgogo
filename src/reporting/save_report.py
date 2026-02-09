from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from validation.schema_validator import validate_analysis_report


def save_analysis_report(
    report: Dict[str, Any],
    reports_root: Path,
    schema_dir: Path,
    overwrite: bool = False,
) -> Path:
    validate_analysis_report(report, schema_dir)
    if overwrite:
        reports_root.mkdir(parents=True, exist_ok=True)
        path = reports_root / "latest_analysis_report.json"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        return path

    timestamp = datetime.now().strftime("%Y-%m-%d/%H%M%S")
    target_dir = reports_root / timestamp.split("/")[0]
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{timestamp.split('/')[1]}_analysis_report.json"
    path = target_dir / filename

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return path
