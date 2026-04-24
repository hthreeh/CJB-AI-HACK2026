#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

HOST="0.0.0.0"
PORT="9600"
LOG_FILE="$SCRIPT_DIR/web_9600.log"
PID_FILE="$SCRIPT_DIR/web_9600.pid"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}=== Starting OS Agent Web Service ===${NC}\n"

# Ensure Python environment exists
if [[ ! -d "$SCRIPT_DIR/venv" ]] && [[ ! -d "$SCRIPT_DIR/.venv" ]]; then
  echo -e "${YELLOW}Virtual environment not found. Creating one...${NC}"
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv "$SCRIPT_DIR/venv"
    "$SCRIPT_DIR/venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
  else
    echo -e "${RED}ERROR: python3 is not installed.${NC}"
    exit 1
  fi
fi

if [[ -x "$SCRIPT_DIR/venv/bin/python" ]]; then
  PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
elif [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi

if [[ -f "$PID_FILE" ]]; then
  EXISTING_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
    echo -e "${GREEN}Web service is already running on PID $EXISTING_PID${NC}"
    SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")"
    echo -e "URL: ${GREEN}http://${SERVER_IP}:$PORT${NC}"
    exit 0
  fi
fi

if command -v ss >/dev/null 2>&1 && ss -ltn | grep -q ":$PORT "; then
  echo -e "${RED}Port $PORT is already in use. Please free it before starting the web service.${NC}"
  exit 1
fi

echo "Starting server on $HOST:$PORT..."
nohup "$PYTHON_BIN" -m src.main web --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 &
WEB_PID=$!
echo "$WEB_PID" >"$PID_FILE"

# Wait for server to start
sleep 3

if ! kill -0 "$WEB_PID" 2>/dev/null; then
  echo -e "${RED}Failed to start web service. Check $LOG_FILE for details.${NC}"
  tail -n 10 "$LOG_FILE"
  exit 1
fi

SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')"
echo -e "${GREEN}Web service successfully started!${NC}"
echo "PID: $WEB_PID"
echo "Log: $LOG_FILE"
echo -e "URL: ${GREEN}http://${SERVER_IP}:$PORT${NC}"
