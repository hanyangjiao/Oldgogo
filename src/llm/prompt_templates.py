from __future__ import annotations

from typing import List


def build_analysis_prompt(
    task_types: List[str],
    anomaly_types: List[str],
    window_start: str,
    window_end: str,
    frame_count: int,
    heart_rate_points: int,
) -> str:
    tasks_str = ", ".join(task_types) if task_types else "none"
    anomalies_str = ", ".join(anomaly_types) if anomaly_types else "none"

    return (
        "You are an expert in analyzing first-person videos of elderly individuals "
        "performing daily activities. Your task is to analyze the provided video window "
        "and determine if specific tasks or anomalies occurred.\n\n"
        "VIDEO CONTEXT:\n"
        f"- Window start: {window_start}\n"
        f"- Window end: {window_end}\n"
        f"- Frame count: {frame_count}\n"
        f"- Tasks to monitor: {tasks_str}\n\n"
        "HEART RATE CONTEXT:\n"
        f"- Points in window: {heart_rate_points}\n\n"
        "ANALYSIS REQUIREMENTS:\n"
        "For each task type, determine:\n"
        "1. Whether the task was performed (true/false)\n"
        "2. repeated_count as a cumulative total (increment at most once per window)\n"
        "3. A clear reason for your conclusion\n\n"
        "For each anomaly type, determine:\n"
        "1. Whether the anomaly occurred in THIS window (true/false)\n"
        "2. num_of_happens as a CUMULATIVE total across ALL windows:\n"
        "   - Look at dataset_snapshot.anomaly_list to count previous occurrences\n"
        "   - Count how many times this anomaly type appears in the list\n"
        "   - If the anomaly is detected in THIS window (match=true), add 1 to the count\n"
        "   - If NOT detected in THIS window (match=false), use the previous count\n"
        "   - CRITICAL: Even when match=false, you MUST maintain the cumulative count!\n"
        "3. A clear reason for your conclusion\n\n"
        "ANOMALY DETECTION GUIDELINES:\n"
        "VIDEO ANOMALIES and HEART RATE ANOMALIES are INDEPENDENT - analyze them separately!\n"
        "You can (and should) detect BOTH types in the same window if evidence exists.\n\n"
        "- FALLDOWN: Look for visual evidence of a person falling or lying on the ground.\n"
        "  Signs include: sudden vertical position change, person on floor/ground, \n"
        "  loss of balance, body collapsing, or person in horizontal position unexpectedly.\n"
        "  Carefully analyze the entire video for any falling motion or person down on the ground.\n"
        "- TACHYCARDIA: Heart rate consistently above 100 bpm (typically 110+ bpm).\n"
        "  Check if most/all heart rate readings in the window exceed the threshold.\n"
        "  This is independent of video content - analyze ONLY the heart rate data.\n"
        "- BRADYCARDIA: Heart rate consistently below 50 bpm (typically <50 bpm).\n"
        "  Check if most/all heart rate readings in the window are below the threshold.\n"
        "  This is independent of video content - analyze ONLY the heart rate data.\n\n"
        "IMPORTANT RULES:\n"
        "1. Only include tasks and anomalies explicitly requested\n"
        "2. Use timestamps relative to the window start when explaining evidence\n"
        "3. Video anomalies (falldown) and HR anomalies (tachycardia/bradycardia) are\n"
        "   analyzed SEPARATELY - you can detect BOTH in the same window\n"
        "4. For falldown detection, examine ALL frames carefully for visual evidence\n"
        "5. For HR anomalies: Analyze the entire heart rate series for consistent patterns\n"
        "6. Be thorough and accurate - don't skip anomalies because another was detected\n"
        "7. CUMULATIVE COUNT EXAMPLE:\n"
        "   If dataset_snapshot.anomaly_list shows 'falldown' appears 1 time:\n"
        "   - Current window has falldown: return {match: true, num_of_happens: 2}\n"
        "   - Current window NO falldown: return {match: false, num_of_happens: 1}\n"
        "   The count persists even when match=false!\n\n"
        f"Anomalies to monitor: {anomalies_str}\n"
        "Return ONLY valid JSON following the required schema."
    )


def build_daily_summary_prompt() -> str:
    return (
        "You are summarizing elder monitoring dataset. "
        "Return a concise human-readable summary with task completion and anomalies."
    )


def build_family_report_prompt() -> str:
    return (
        "You are writing a concise, empathetic update for family members based on a single "
        "analysis report of an elderly monitoring window. "
        "Summarize key activities, detected anomalies, and any follow-up suggestions. "
        "Do not include raw JSON. Keep it under 150 words."
    )
