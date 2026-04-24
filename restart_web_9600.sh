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

echo -e "${YELLOW}=== Restarting OS Agent Web Service ===${NC}\n"

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

find_python() {
    if [[ -x "$SCRIPT_DIR/venv/bin/python" ]]; then
        echo "$SCRIPT_DIR/venv/bin/python"
    elif [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
        echo "$SCRIPT_DIR/.venv/bin/python"
    else
        command -v python3
    fi
}

kill_by_pidfile() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            echo -e "Stopping existing service (PID ${YELLOW}$pid${NC})..."
            kill "$pid" 2>/dev/null || true
            sleep 2
            kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi
}

kill_by_port() {
    if command -v ss >/dev/null 2>&1; then
        local pid
        pid=$(ss -ltnp 2>/dev/null | grep ":$PORT " | awk -F'pid=' '{print $2}' | awk -F',' '{print $1}' | head -1 || echo "")
        if [[ -z "$pid" ]]; then
           # fallback to older parse
           pid=$(ss -ltn 2>/dev/null | grep ":$PORT " | awk 'NR==1 {print $NF}' | grep -o '[0-9]*' | head -1 || echo "")
        fi
        if [[ -n "$pid" ]] && [[ "$pid" =~ ^[0-9]+$ ]]; then
            echo -e "Killing process on port $PORT (PID ${YELLOW}$pid${NC})..."
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
        fi
    fi
}

PYTHON_BIN="$(find_python)"

kill_by_pidfile
kill_by_port
sleep 1

if ss -ltn 2>/dev/null | grep -q ":$PORT "; then
    echo -e "${RED}ERROR: Port $PORT still in use after cleanup.${NC}"
    exit 1
fi

echo "Starting server on $HOST:$PORT..."
nohup "$PYTHON_BIN" -m src.main web --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"

sleep 3

if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo -e "${RED}ERROR: Failed to start. Check $LOG_FILE${NC}"
    tail -n 10 "$LOG_FILE"
    exit 1
fi

SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")"
echo -e "\n${GREEN}Service successfully restarted!${NC}"
echo "PID: $(cat "$PID_FILE")"
echo -e "URL: ${GREEN}http://${SERVER_IP}:$PORT${NC}"
