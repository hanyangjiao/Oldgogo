#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"
UI_PATH="src/app/ui/index.html"
URL="http://localhost:${PORT}/src/app/ui/"

if [ ! -f "$UI_PATH" ]; then
  echo "UI not found at $UI_PATH" >&2
  exit 1
fi

# Prefer the active conda env's Python if available.
if [ -n "${CONDA_PREFIX:-}" ] && [ -x "${CONDA_PREFIX}/bin/python" ]; then
  PYTHON_BIN="${CONDA_PREFIX}/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python is required to serve the UI." >&2
  exit 1
fi

echo "Starting UI server on $URL"
echo "Press Ctrl+C to stop."
if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "[WARN] GEMINI_API_KEY is not set. Inference will fail until it is provided."
fi

"$PYTHON_BIN" src/app/ui_server.py --host "$HOST" --port "$PORT" >/tmp/elder_ui_server.log 2>&1 &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open "$URL" >/dev/null 2>&1 || true
fi

wait "$SERVER_PID"
