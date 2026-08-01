#!/usr/bin/env bash
# Serve the CustomerSetup pages over http://localhost:5170/.
#
# file:// works for reading, but the liveness pings and the shared
# localStorage reading level behave uniformly across browsers only when the
# pages are served over http. 5170 sits below the twins' 5173+ range and is
# reserved for this in ports.json.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PORT="${PORT:-5170}"

echo "CustomerSetup at http://localhost:${PORT}/ (Ctrl-C to stop)"
exec python3 -m http.server "$PORT" --directory "$ROOT" --bind 127.0.0.1
