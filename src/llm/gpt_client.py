from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm.prompt_templates import (
    build_analysis_prompt,
    build_daily_summary_prompt,
    build_family_report_prompt,
)


@dataclass
class GPTClient:
    api_key: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for GPT API calls.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai is required for GPT calls. Install with: pip install -r requirements.txt"
            ) from exc

        self.client = OpenAI(api_key=self.api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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
            "heart_rate_series": heart_rate_series or [],
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

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.2,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.strip("`")
        content = content.strip()
        if not content.startswith("{"):
            start_idx = content.find("{")
            if start_idx != -1:
                content = content[start_idx:]
        if not content.endswith("}"):
            end_idx = content.rfind("}")
            if end_idx != -1:
                content = content[: end_idx + 1]

        return json.loads(content)

    def summarize_daily(self, dataset_snapshot: Dict[str, Any]) -> str:
        prompt = build_daily_summary_prompt()
        full_prompt = (
            f"{prompt}\n\n"
            "Dataset snapshot:\n"
            f"{json.dumps(dataset_snapshot, ensure_ascii=False)}\n"
            "Return a concise human-readable summary."
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    def summarize_report(self, analysis_report: Dict[str, Any]) -> str:
        prompt = build_family_report_prompt()
        full_prompt = (
            f"{prompt}\n\n"
            "Analysis report:\n"
            f"{json.dumps(analysis_report, ensure_ascii=False)}\n"
            "Return the family update text only."
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
