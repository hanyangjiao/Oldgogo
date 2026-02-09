import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path("src")))

from llm.client_factory import get_llm_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate family-facing report from analysis report JSON")
    parser.add_argument(
        "--report",
        type=str,
        default="reports/latest_analysis_report.json",
        help="Path to analysis report JSON",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="output/notifications/family_report.txt",
        help="Output text path",
    )
    parser.add_argument(
        "--llm",
        choices=["gemini", "gpt"],
        default="gemini",
        help="LLM provider",
    )
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")

    with open(report_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    client = get_llm_client(args.llm)
    text = client.summarize_report(report)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(text.strip() + "\n")

    print(f"[INFO] Family report saved: {out_path}")


if __name__ == "__main__":
    main()
