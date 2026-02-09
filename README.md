# Oldgogo

Oldgogo is an elder monitoring system that runs windowed video + vitals analysis, maintains a cumulative task/anomaly dataset during a UI session, and generates human-readable summaries, alerts, and reports.

## Key Features

- UI for running inference on queued video/HR pairs
- Cumulative dataset updates within a single Start session
- Non-repeatable task detection with voice alert
- Anomaly detection with voice alert + optional beep fallback
- Email notifications via SMTP with local fallback copy
- Latest email preview displayed in the UI
- Latest cumulative report persisted to `reports/latest_analysis_report.json`

## Project Layout

```
spec/                     # system spec + JSON schemas
src/
  app/                    # app entrypoints + UI server
  config/                 # default config
  domain/                 # dataset + update rules
  ingestion/              # local ingestion + strict sync
  llm/                    # Gemini/GPT clients + prompts
  notification/           # email + voice + cooldown
  reporting/              # report persistence
  scheduler/              # periodic + reset jobs
  validation/             # JSON Schema validation
scripts/
  run_ui.sh
  run_local.sh
  run_online.sh
```

## Requirements

- Python 3.10+
- Conda (recommended)
- ffprobe available on PATH (used to read video duration)

## Setup

```bash
conda create -n dds python=3.10 -y
conda activate dds
pip install -r requirements.txt
```

## API Keys

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
nano .env
```

Or set as environment variable:

```bash
export GEMINI_API_KEY="your_gemini_key"
```

**Important:** Never commit `.env` to git! It's already in `.gitignore`.

## Run the UI

```bash
./scripts/run_ui.sh
```

UI will be served at:

```
http://localhost:8000/src/app/ui/
```

## UI Behavior (Important)

- Each Start resets the server-side dataset state.
- Within a single Start, each queued pair updates the same dataset.
- If a non-repeatable task repeats, the UI plays a voice warning and continues.
- Any anomaly triggers voice alert (fallback to beep if speech synthesis is unavailable).
- The latest email preview is always written to `output/notifications/`.
- The latest cumulative report is stored at `reports/latest_analysis_report.json`.

## Local / Online Modes (CLI)

Local mode:

```bash
python src/app/main.py --mode local \
  --video data/videos/drink_water.mp4 \
  --video-start "2026-01-16T09:00:00+08:00" \
  --hr data/hr/hr_normal.json \
  --cycles 1 \
  --llm gemini
```

Online mode (process a directory of videos):

```bash
python src/app/main.py --mode online \
  --video-dir data/videos \
  --video-start "2026-01-16T09:00:00+08:00" \
  --hr data/hr/hr_normal.json \
  --cycles 2 \
  --llm gemini
```

## SMTP Email Setup (Optional)

Configure SMTP via environment variables:

```bash
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your@gmail.com"
export SMTP_PASS="your_app_password"
export SMTP_FROM="your@gmail.com"
```

Recipients are defined in `src/config/default.yaml` under `emergency_contact`.

## Outputs

- Latest cumulative report: `reports/latest_analysis_report.json`
- Historical reports: `reports/YYYY-MM-DD/HHMMSS_analysis_report.json`
- Email previews (always): `output/notifications/email_*.txt`

## Troubleshooting

- If the UI exits immediately, check `/tmp/elder_ui_server.log`.
- Ensure your Python binary is from the correct conda environment.
- If audio does not play, interact with the page once (browser autoplay policies).

## License

For demonstration and internal testing purposes only.
