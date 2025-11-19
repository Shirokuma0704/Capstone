#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "$0")" && pwd)"
RPI_STACK_DIR="$SCRIPT_DIR/../rpi-dashboard-local"
COMPOSE_FILE="$RPI_STACK_DIR/docker-compose.yml"
CONTROL_UI_DIR="$RPI_STACK_DIR/control_ui"
IMAGE_NAME="stgc-control-ui:latest"
CONTAINER_NAME="stgc-control-ui"

usage() {
  cat >&2 <<'EOF'
Usage: ./run_docker.sh [up|down|logs|ui]
  up    Build and start the full stack via docker-compose (control_ui, influxdb, grafana). Default.
  down  Stop and remove the compose stack.
  logs  Tail logs from the compose stack.
  ui    Build and run only the control_ui image standalone (same as previous behavior).
EOF
  exit 1
}

command -v docker >/dev/null 2>&1 || { echo "docker is not installed or not in PATH." >&2; exit 1; }

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose -f "$COMPOSE_FILE")
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose -f "$COMPOSE_FILE")
else
  echo "docker compose is required but not found." >&2
  exit 1
fi

[[ -f "$COMPOSE_FILE" ]] || { echo "Compose file not found at $COMPOSE_FILE" >&2; exit 1; }
[[ -d "$CONTROL_UI_DIR" ]] || { echo "Docker context not found at $CONTROL_UI_DIR" >&2; exit 1; }

ACTION="${1:-up}"

case "$ACTION" in
  up)
    echo "[run_docker.sh] Bringing up full stack from $COMPOSE_FILE (with build)..."
    "${COMPOSE_CMD[@]}" up -d --build
    echo "[run_docker.sh] Stack is running. Use './run_docker.sh logs' to tail logs."
    ;;
  down)
    echo "[run_docker.sh] Stopping compose stack..."
    "${COMPOSE_CMD[@]}" down
    ;;
  logs)
    echo "[run_docker.sh] Tailing logs for compose stack (Ctrl+C to exit)..."
    "${COMPOSE_CMD[@]}" logs -f
    ;;
  ui)
    echo "[run_docker.sh] Building image $IMAGE_NAME from $CONTROL_UI_DIR..."
    docker build -t "$IMAGE_NAME" "$CONTROL_UI_DIR"

    echo "[run_docker.sh] Removing any existing container named $CONTAINER_NAME..."
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

    echo "[run_docker.sh] Starting container $CONTAINER_NAME on port 8080..."
    docker run -d --name "$CONTAINER_NAME" -p 8080:8080 --restart unless-stopped "$IMAGE_NAME"
    echo "[run_docker.sh] Container is running. Tail logs with: docker logs -f $CONTAINER_NAME"
    ;;
  *)
    usage
    ;;
esac
