#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND="$ROOT/frontend"

cd "$FRONTEND"

PORT="${PORT:-5207}"

# Say who has the port before Vite fails on it. Several twins share this
# machine, so the usual cause is a neighbour that walked onto 5207 when its own
# port was busy. Never kill it — say what is there and how to work around it.
if curl -s -m 2 "http://localhost:$PORT/" -o /tmp/pf-port-check.$$ 2>/dev/null; then
  TITLE="$(sed -n 's/.*<title>\(.*\)<\/title>.*/\1/p' /tmp/pf-port-check.$$ | head -1)"
  rm -f /tmp/pf-port-check.$$
  echo "Port $PORT is already answering${TITLE:+ as: $TITLE}."
  echo "If that is not this app, stop it, or run this one elsewhere:"
  echo "  PORT=5307 ./scripts/start_frontend.sh"
  echo "The backend address is unaffected; override it with API_TARGET if needed."
  exit 1
fi
rm -f /tmp/pf-port-check.$$

if [ ! -d "node_modules" ]; then
  npm install
fi

export PORT
exec npm run dev
