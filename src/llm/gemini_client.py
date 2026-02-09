from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from llm.prompt_templates import (
    build_analysis_prompt,
    build_daily_summary_prompt,
    build_family_report_prompt,
)


@dataclass
class GeminiClient:
    api_key: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for real API calls.")

        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ImportError(
                "google-generativeai is required for Gemini calls. "
                "Install with: pip install -r requirements.txt"
            ) from exc

        genai.configure(api_key=self.api_key)
        self.genai = genai
        model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        self.model = genai.GenerativeModel(model_name)

    def analyze_window(
        self,
        task_types: List[str],
        anomaly_types: List[str],
        window_start: str,
        window_end: str,
        frame_count: int,
        heart_rate_points: int,
        dataset_snapshot: Dict[str, Any],
        heart_rate_series: Optional[List[Dict[str, Any]]] = None,
        video_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        return self._call_real_api(
            task_types,
            anomaly_types,
            window_start,
            window_end,
            frame_count,
            heart_rate_points,
            dataset_snapshot,
            heart_rate_series or [],
            video_path,
        )

    def summarize_daily(self, dataset_snapshot: Dict[str, Any]) -> str:
        return self._call_real_summary_api(dataset_snapshot)

    def summarize_report(self, analysis_report: Dict[str, Any]) -> str:
        return self._call_real_report_api(analysis_report)

    def _call_real_api(
        self,
        task_types: List[str],
        anomaly_types: List[str],
        window_start: str,
        window_end: str,
        frame_count: int,
        heart_rate_points: int,
        dataset_snapshot: Dict[str, Any],
        heart_rate_series: List[Dict[str, Any]],
        video_path: Optional[Path],
    ) -> Dict[str, Any]:
        prompt = build_analysis_prompt(
            task_types,
            anomaly_types,
            window_start,
            window_end,
            frame_count,
            heart_rate_points,
        )
        schema_dir = Path("spec/schema")
        analysis_schema = (schema_dir / "analysis_report.schema.json").read_text(encoding="utf-8")
        dataset_schema = (schema_dir / "dataset.schema.json").read_text(encoding="utf-8")

        payload = {
            "window": {"start_time": window_start, "end_time": window_end},
            "inputs": {"frame_count": frame_count, "heart_rate_points": heart_rate_points},
            "dataset_snapshot": dataset_snapshot,
            "heart_rate_series": heart_rate_series,
        }

        full_prompt = (
            f"{prompt}\n\n"
            "You must return ONLY a JSON object that matches the following schema.\n"
            f"analysis_report.schema.json:\n{analysis_schema}\n\n"
            f"dataset.schema.json:\n{dataset_schema}\n\n"
            "Here is the window input payload:\n"
            f"{json.dumps(payload, ensure_ascii=False)}\n"
            "Return JSON only, no markdown."
        )

        if video_path:
            video_file = self.genai.upload_file(video_path)
            max_wait_time = 300
            waited = 0
            while video_file.state.name != "ACTIVE" and waited < max_wait_time:
                time.sleep(5)
                waited += 5
                video_file = self.genai.get_file(video_file.name)
            if video_file.state.name != "ACTIVE":
                raise RuntimeError(
                    f"Video file failed to become ACTIVE after {max_wait_time}s. "
                    f"Current state: {video_file.state.name}"
                )
            response = self.model.generate_content([video_file, full_prompt])
        else:
            response = self.model.generate_content(full_prompt)
        response_text = response.text.strip()
        if response_text.startswith("```"):
            response_text = response_text.strip("`")
        response_text = response_text.strip()
        if not response_text.startswith("{"):
            start_idx = response_text.find("{")
            if start_idx != -1:
                response_text = response_text[start_idx:]
        if not response_text.endswith("}"):
            end_idx = response_text.rfind("}")
            if end_idx != -1:
                response_text = response_text[: end_idx + 1]

        return json.loads(response_text)

    def _call_real_summary_api(self, dataset_snapshot: Dict[str, Any]) -> str:
        prompt = build_daily_summary_prompt()
        full_prompt = (
            f"{prompt}\n\n"
            "Dataset snapshot:\n"
            f"{json.dumps(dataset_snapshot, ensure_ascii=False)}\n"
            "Return a concise human-readable summary."
        )
        response = self.model.generate_content(full_prompt)
        return response.text.strip()

    def _call_real_report_api(self, analysis_report: Dict[str, Any]) -> str:
        prompt = build_family_report_prompt()
        full_prompt = (
            f"{prompt}\n\n"
            "Analysis report:\n"
            f"{json.dumps(analysis_report, ensure_ascii=False)}\n"
            "Return the family update text only."
        )
        response = self.model.generate_content(full_prompt)
        return response.text.strip()
