# Test Plan

## Entry Points

- Dataset + updates: `src/domain/dataset.py`, `src/domain/update_rules.py`
- Schema validation: `src/validation/schema_validator.py`
- Inference loop/windowing: `src/app/main.py`, `src/scheduler/periodic_job.py`
- Report persistence: `src/reporting/save_report.py`
- Reset summary flow: `src/reporting/daily_summary.py`, `src/scheduler/reset_job.py`
- Notifications: `src/notification/email_notifier.py`, `src/notification/voice_notifier.py`

## Feature Coverage

- F1 Strict sync: `tests/integration/test_windowing_and_sync.py`
- F2 Windowed inference loop + single-call: `tests/integration/test_inference_loop_calls.py`
- F3 reset_time reset: `tests/integration/test_reset_time_summary_flow.py`
- F4 dataset schema validation: `tests/unit/test_schema_dataset.py`
- F5 analysis_report schema gate: `tests/integration/test_inference_loop_calls.py`
- F6 task update rules: `tests/unit/test_update_rules_tasks.py`
- F7 multi-anomaly matches: `tests/unit/test_update_rules_anomaly.py`
- F8 cooldown logic: `tests/unit/test_cooldown.py`
- F9 anomaly email template: `tests/integration/test_inference_loop_calls.py`
- F10 report persistence gate + timestamps: `tests/integration/test_report_persistence.py`
- F11 reset_time summary flow: `tests/integration/test_reset_time_summary_flow.py`

