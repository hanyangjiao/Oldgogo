#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python is required to send email notifications." >&2
  exit 1
fi

CONFIG_PATH="${CONFIG_PATH:-src/config/default.yaml}"
REPORT_PATH="${REPORT_PATH:-}"
REPORTS_ROOT="${REPORTS_ROOT:-reports}"

ARGS=(--config "$CONFIG_PATH" --reports-root "$REPORTS_ROOT")
if [ -n "$REPORT_PATH" ]; then
  ARGS+=(--report "$REPORT_PATH")
fi

"$PYTHON_BIN" helpers/send_anomaly_email.py "${ARGS[@]}"
