#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$ROOT/logs"

# Start backend in the background, logging to logs/backend.log
"$SCRIPT_DIR/start_backend.sh" >"$ROOT/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo "Backend starting (PID $BACKEND_PID) — logs: logs/backend.log"

# PID file for stop_all.sh: backend on line 1, frontend on line 2.
# Frontend runs in the foreground here, so line 2 is left blank and stop_all.sh
# falls back to killing whatever holds port 5219.
printf '%s\n\n' "$BACKEND_PID" >"$ROOT/logs/pids"

cleanup() {
  echo "Stopping backend (PID $BACKEND_PID)..."
  kill "$BACKEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# Frontend in the foreground; Ctrl-C triggers cleanup of the backend.
"$SCRIPT_DIR/start_frontend.sh"
