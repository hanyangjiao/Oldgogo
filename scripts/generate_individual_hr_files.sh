#!/usr/bin/env bash
# Generate individual heart rate JSON files for each "_first" suffix video

set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck source=/dev/null
  . "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck source=/dev/null
  . "$HOME/anaconda3/etc/profile.d/conda.sh"
fi
conda activate dds

# Start time matching run_online.sh
START_TIME="2026-01-16T09:00:00+08:00"
VIDEO_DIR="data/videos"
OUTPUT_DIR="data/heart_rate"

echo "[INFO] Generating individual HR files for each '_first' video..."
echo ""

# Get only videos with "_first" suffix
videos=($(ls -1 "$VIDEO_DIR"/*_first.mp4 2>/dev/null | sort || true))

if [ ${#videos[@]} -eq 0 ]; then
  echo "[ERROR] No videos with '_first' suffix found in $VIDEO_DIR"
  exit 1
fi

echo "[INFO] Found ${#videos[@]} videos with '_first' suffix:"
for video in "${videos[@]}"; do
  echo "  - $(basename "$video")"
done
echo ""

# Track current start time
current_start="$START_TIME"

mkdir -p "$OUTPUT_DIR"

for i in "${!videos[@]}"; do
  video="${videos[$i]}"
  video_name=$(basename "$video" .mp4)

  # Calculate duration
  duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
  duration_sec=$(printf "%.0f" "$duration")

  # Assign HR scenarios based on video name
  if [[ "$video_name" == *"drink_water"* ]]; then
    scenario="normal (75 bpm)"
    base_bpm=75
    jitter=5
  elif [[ "$video_name" == *"falldown"* ]]; then
    # Falldown should have bradycardia + visual falldown detection
    scenario="bradycardia (<50 bpm) + falldown"
    base_bpm=45
    jitter=3
  elif [[ "$video_name" == *"take_medicine"* ]]; then
    scenario="tachycardia (120 bpm)"
    base_bpm=120
    jitter=8
  else
    # Default to normal
    scenario="normal (75 bpm)"
    base_bpm=75
    jitter=5
  fi

  echo "[INFO] Generating HR for $video_name"
  echo "  Duration: ${duration_sec}s"
  echo "  Start time: $current_start"
  echo "  Scenario: $scenario"

  # Generate HR file with exact duration
  duration_minutes=$(( (duration_sec + 59) / 60 ))
  if [ $duration_minutes -lt 1 ]; then
    duration_minutes=1
  fi

  python helpers/generate_hr.py \
    --start "$current_start" \
    --minutes $duration_minutes \
    --interval-sec 1 \
    --base-bpm $base_bpm \
    --jitter $jitter \
    --out "$OUTPUT_DIR/${video_name}_hr_full.json"

  # Trim to exact duration
  python3 << EOF
import json
from datetime import datetime, timedelta
from pathlib import Path

with open("$OUTPUT_DIR/${video_name}_hr_full.json", 'r') as f:
    data = json.load(f)

start_dt = datetime.fromisoformat("$current_start")
end_dt = start_dt + timedelta(seconds=$duration_sec)

# Filter points within the video duration (exclusive end)
trimmed = [p for p in data if start_dt <= datetime.fromisoformat(p['timestamp']) < end_dt]

with open("$OUTPUT_DIR/${video_name}.json", 'w') as f:
    json.dump(trimmed, f, ensure_ascii=False, indent=2)

print(f"  Saved {len(trimmed)} points to $OUTPUT_DIR/${video_name}.json")
EOF

  rm "$OUTPUT_DIR/${video_name}_hr_full.json"

  # Calculate next start time
  current_start=$(python3 -c "
from datetime import datetime, timedelta
dt = datetime.fromisoformat('$current_start')
next_dt = dt + timedelta(seconds=$duration_sec)
print(next_dt.isoformat())
")

  echo ""
done

echo "[SUCCESS] Individual HR files generated!"
echo ""
echo "Generated files in $OUTPUT_DIR/:"
for video in "${videos[@]}"; do
  video_name=$(basename "$video" .mp4)
  echo "  ✓ ${video_name}.json"
done
echo ""

# Combine all individual files into one
echo "[INFO] Combining all HR files into all_first_videos.json..."
python3 << 'EOF'
import json
from pathlib import Path
from datetime import datetime

output_dir = Path("data/heart_rate")
combined = []

# Get all individual HR files for _first videos
hr_files = sorted(output_dir.glob("*_first.json"))

for hr_file in hr_files:
    with open(hr_file, 'r') as f:
        data = json.load(f)
        combined.extend(data)

# Sort by timestamp to ensure chronological order
combined.sort(key=lambda x: datetime.fromisoformat(x['timestamp']))

# Save combined file
output_file = output_dir / "all_first_videos.json"
with open(output_file, 'w') as f:
    json.dump(combined, f, ensure_ascii=False, indent=2)

print(f"  ✓ Combined {len(combined)} HR points into all_first_videos.json")
EOF

echo ""
echo "[SUCCESS] all_first_videos.json created!"
echo "  → This file is used by run_online.sh"
