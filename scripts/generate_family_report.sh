#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck source=/dev/null
  . "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck source=/dev/null
  . "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck source=/dev/null
  . "/opt/anaconda3/etc/profile.d/conda.sh"
fi

conda activate elder_monitor

python helpers/generate_family_report.py \
  --report reports/latest_analysis_report.json \
  --out output/notifications/family_report.txt \
  --llm gemini
