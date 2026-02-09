#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  . "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
  . "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
  . "/opt/anaconda3/etc/profile.d/conda.sh"
fi

conda activate dds

# Load environment variables from .env if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Check if GEMINI_API_KEY is set
if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "ERROR: GEMINI_API_KEY is not set"
  echo "Please create a .env file with: GEMINI_API_KEY=your_key_here"
  echo "Or export it: export GEMINI_API_KEY='your_key_here'"
  exit 1
fi

python src/app/main.py \
  --mode local \
  --video data/videos/falldown.mp4 \
  --video-start "2026-01-16T09:00:00+08:00" \
  --hr data/hr/hr_bradycardia.json \
  --cycles 1 \
  --llm gemini
