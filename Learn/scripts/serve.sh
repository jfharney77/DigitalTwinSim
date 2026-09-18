#!/usr/bin/env bash
# Serve the Learn course over http://localhost:5172/Learn/.
#
# Serves the repo root, not Learn/, so the course's relative links to
# ../CustomerSetup/ (the shared stylesheet and script, and the capstone's
# setup pages) resolve side by side. 5172 is reserved for this in ports.json;
# 5170 is CustomerSetup's own server.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PORT="${PORT:-5172}"

echo "Learn at http://localhost:${PORT}/Learn/ (Ctrl-C to stop)"
exec python3 -m http.server "$PORT" --directory "$ROOT" --bind 127.0.0.1
