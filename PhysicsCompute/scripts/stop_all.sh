#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$ROOT/logs/pids"

stopped=0

kill_pid() {
  local pid="$1" label="$2"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    echo "Stopped $label (PID $pid)."
    stopped=1
  fi
}

kill_port() {
  local port="$1" label="$2"
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    for pid in $pids; do
      kill "$pid" 2>/dev/null || true
      echo "Stopped $label on port $port (PID $pid)."
      stopped=1
    done
  fi
}

# Preferred path: PID file written by start_all.sh
if [ -f "$PID_FILE" ]; then
  backend_pid="$(sed -n '1p' "$PID_FILE" 2>/dev/null || true)"
  frontend_pid="$(sed -n '2p' "$PID_FILE" 2>/dev/null || true)"
  kill_pid "$backend_pid" "backend"
  kill_pid "$frontend_pid" "frontend"
  rm -f "$PID_FILE"
fi

# Fallback / belt-and-suspenders: kill by well-known dev ports.
kill_port 8032 "FastAPI/uvicorn"
kill_port 5205 "Vite dev server"

if [ "$stopped" -eq 0 ]; then
  echo "No running processes found."
fi
