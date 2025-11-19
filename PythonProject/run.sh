#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
  echo "Usage: $0 [--mock] [--track] [--help]" >&2
  echo "  --mock    Run logger with mock sensors (no hardware required)." >&2
  echo "  --track   Run solar tracker (GPS -> servo motors)." >&2
  exit 1
}

MOCK_MODE=0
TRACK_MODE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mock)
      MOCK_MODE=1
      shift
      ;;
    --track)
      TRACK_MODE=1
      shift
      ;;
    --help|-h)
      usage
      ;;
    *)
      usage
      ;;
  esac
done

# Load environment variables from .env if present
if [[ -f .env ]]; then
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
fi

PIP_BIN=${PIP:-pip3}
PY_BIN=${PYTHON:-python3}

echo "[run.sh] Installing Python requirements..."
"$PIP_BIN" install -r requirements.txt

if [[ $TRACK_MODE -eq 1 ]]; then
  echo "[run.sh] Starting solar tracker (GPS -> servo motors)."
  exec "$PY_BIN" -m src.solar_tracker
else
  if [[ $MOCK_MODE -eq 1 ]]; then
    export USE_SENSOR_MOCK=1
    echo "[run.sh] Starting logger in MOCK mode (USE_SENSOR_MOCK=1)."
  else
    echo "[run.sh] Starting logger with REAL hardware (photodiode excluded)."
  fi
  exec "$PY_BIN" -m src.data_logger
fi
