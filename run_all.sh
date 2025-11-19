#!/usr/bin/env bash
set -euo pipefail

# 통합 실행 스크립트:
# 1) Docker 스택 (InfluxDB, Grafana, control-ui) 기동
# 2) hardware_api(실제 트래커 + 센서) 기동
# 3) 데이터 프로듀서(InlfuxDB 적재) 기동
# 옵션:
#   - stop: 모든 Docker 컨테이너와 백그라운드 파이썬 프로세스 종료

ROOT_DIR="$(cd -- "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/rpi-dashboard-local/docker-compose.yml"
LOG_DIR="$ROOT_DIR/logs"
HARDWARE_API_PORT="${HARDWARE_API_PORT:-5000}"
CONTROL_UI_PORT="${CONTROL_UI_PORT:-8080}"
MCP_SERVER_PORT="${MCP_SERVER_PORT:-5001}"
ENABLE_PRODUCER="${ENABLE_PRODUCER:-1}"
HARDWARE_API_URL="${HARDWARE_API_URL:-http://host.docker.internal:${HARDWARE_API_PORT}}"
# 최신 brew python(3.14)보다 호환성 높은 시스템 python을 기본값으로 사용
PY_BIN="${PYTHON:-/usr/bin/python3}"
PIP_BIN="${PIP:-/usr/bin/pip3}"
PIP_FLAGS="${PIP_FLAGS:---break-system-packages}"
CC_BIN="${CC:-gcc}"

mkdir -p "$LOG_DIR"

info() { echo "[run_all] $*" >&2; }
err() { echo "[run_all] $*" >&2; }

ensure_compose() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose -f "$COMPOSE_FILE")
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose -f "$COMPOSE_FILE")
  else
    err "docker compose/ docker-compose 가 필요합니다."
    exit 1
  fi
}

start_compose() {
  [[ -f "$COMPOSE_FILE" ]] || { err "Compose 파일 없음: $COMPOSE_FILE"; exit 1; }
  ensure_compose
  cleanup_containers
  CONTROL_UI_PORT=$(pick_control_ui_port "$CONTROL_UI_PORT")
  export CONTROL_UI_PORT
  export HARDWARE_API_URL
  info "Docker 스택 기동 (build 포함)…"
  "${COMPOSE_CMD[@]}" up -d --build
}

cleanup_containers() {
  # compose에서 사용하는 컨테이너 이름을 미리 정리해 충돌 방지
  local names=(control-ui grafana influxdb)
  for n in "${names[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${n}\$"; then
      info "기존 컨테이너 $n 중지/삭제..."
      docker rm -f "$n" >/dev/null 2>&1 || true
    fi
  done
}

port_in_use() {
  local port="$1"
  lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | awk '{print $9}' | grep -q ":${port}$"
}

pick_control_ui_port() {
  local candidate="$1"
  local fallback_start=18080

  if ! port_in_use "$candidate"; then
    echo "$candidate"
    return
  fi

  info "포트 ${candidate} 사용 중 → 대체 포트 탐색"
  for ((p=fallback_start; p<fallback_start+20; p++)); do
    if ! port_in_use "$p"; then
      info "control-ui 호스트 포트를 ${p}(으)로 설정합니다."
      echo "$p"
      return
    fi
  done

  err "사용 가능한 호스트 포트를 찾지 못했습니다. 포트 점유를 해제한 뒤 다시 시도하세요."
  exit 1
}

start_background() {
  local name="$1" cmd="$2" pidfile="$3" logfile="$4"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" >/dev/null 2>&1; then
    info "$name 이미 실행 중 (pid $(cat "$pidfile"))."
    return
  fi
  info "$name 시작 → 로그: $logfile"
  nohup bash -lc "$cmd" >"$logfile" 2>&1 &
  echo $! >"$pidfile"
}

start_hardware_api() {
  local pidfile="$LOG_DIR/hardware_api.pid"
  local logfile="$LOG_DIR/hardware_api.log"
  local cmd="cd \"$ROOT_DIR\" && CC=$CC_BIN $PIP_BIN install $PIP_FLAGS -r requirements.txt && cd \"$ROOT_DIR/src\" && HARDWARE_API_PORT=$HARDWARE_API_PORT $PY_BIN hardware_api.py"
  start_background "hardware_api" "$cmd" "$pidfile" "$logfile"
}

start_mcp_server() {
  local pidfile="$LOG_DIR/mcp_server.pid"
  local logfile="$LOG_DIR/mcp_server.log"
  local cmd="cd \"$ROOT_DIR/PythonProject\" && CC=$CC_BIN $PIP_BIN install $PIP_FLAGS -r requirements.txt && MCP_SERVER_PORT=$MCP_SERVER_PORT $PY_BIN -m src.mcp_server"
  start_background "mcp_server" "$cmd" "$pidfile" "$logfile"
}

start_data_producer() {
  if [[ "$ENABLE_PRODUCER" != "1" ]]; then
    info "데이터 프로듀서 건너뜀 (ENABLE_PRODUCER=$ENABLE_PRODUCER)"
    return
  fi
  local pidfile="$LOG_DIR/data_producer.pid"
  local logfile="$LOG_DIR/data_producer.log"
  local cmd="cd \"$ROOT_DIR/rpi-dashboard-local/data_producer\" && CC=$CC_BIN $PIP_BIN install $PIP_FLAGS -r requirements.txt && HARDWARE_API_URL=\"http://127.0.0.1:${HARDWARE_API_PORT}\" $PY_BIN write_data.py"
  start_background "data_producer" "$cmd" "$pidfile" "$logfile"
}

stop_background() {
  local name="$1" pidfile="$2"
  if [[ -f "$pidfile" ]]; then
    local pid
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" >/dev/null 2>&1; then
      info "$name 중지 중 (pid $pid)..."
      kill "$pid" >/dev/null 2>&1 || true
      sleep 1
      if kill -0 "$pid" >/dev/null 2>&1; then
        info "$name 강제 종료..."
        kill -9 "$pid" >/dev/null 2>&1 || true
      fi
    fi
    rm -f "$pidfile"
  fi
}

stop_hardware_api() {
  stop_background "hardware_api" "$LOG_DIR/hardware_api.pid"
}

stop_data_producer() {
  stop_background "data_producer" "$LOG_DIR/data_producer.pid"
}

stop_mcp_server() {
  stop_background "mcp_server" "$LOG_DIR/mcp_server.pid"
}

stop_compose() {
  if [[ -f "$COMPOSE_FILE" ]]; then
    ensure_compose
    info "Docker 스택 중지..."
    "${COMPOSE_CMD[@]}" down >/dev/null 2>&1 || true
  fi
  cleanup_containers
}

main() {
  info "설정: PY_BIN=$PY_BIN, PIP_BIN=$PIP_BIN, CC_BIN=$CC_BIN, HARDWARE_API_URL=$HARDWARE_API_URL, CONTROL_UI_PORT=$CONTROL_UI_PORT, MCP_SERVER_PORT=$MCP_SERVER_PORT"

  if [[ "${1:-}" == "stop" ]]; then
    stop_mcp_server
    stop_data_producer
    stop_hardware_api
    stop_compose
    info "모든 서비스 종료 완료."
    exit 0
  fi

  # 새로 시작하기 전에 기존 프로세스 정리
  stop_mcp_server
  stop_data_producer
  stop_hardware_api
  start_compose
  start_hardware_api
  start_data_producer
  start_mcp_server

  info "모든 서비스 기동 완료."
  info " - hardware_api: http://127.0.0.1:${HARDWARE_API_PORT}"
  info " - mcp_server: http://127.0.0.1:${MCP_SERVER_PORT}"
  info " - control_ui (docker): http://127.0.0.1:${CONTROL_UI_PORT}"
  info " - Grafana (docker): http://127.0.0.1:3000"
  info "로그 디렉터리: $LOG_DIR"
}

main "$@"
