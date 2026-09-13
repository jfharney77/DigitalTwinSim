#!/usr/bin/env bash
# Start any component, without reading its README first.
#
#   scripts/dev.sh --list             every component, its ports and its status
#   scripts/dev.sh --list storage     just that hardware family
#   scripts/dev.sh DellPowerMax       backend in the background, frontend in front
#   scripts/dev.sh DellPowerMax --backend-only
#
# Ports, status and the trace endpoint come from components.json, which is
# generated from disk — so this cannot drift from what is actually there.
# Ctrl-C stops both.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INDEX="$REPO/components.json"

py() { python3 -c "$1" "${@:2}"; }

usage() {
  sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

list() {
  py '
import json, sys
family = (sys.argv[2] if len(sys.argv) > 2 else "") or None
data = json.load(open(sys.argv[1]))
rows = [c for c in data["components"] if family in (None, c["family"])]
if not rows:
    families = sorted({c["family"] for c in data["components"]})
    raise SystemExit("no components in family %r. Families: %s" % (family, ", ".join(families)))
width = max(len(c["name"]) for c in rows)
order = {s: i for i, s in enumerate(data["statuses"])}
for c in sorted(rows, key=lambda c: (order[c["status"]], c["family"], c["name"])):
    ports = "%s/%s" % (c["backendPort"] or "-", c["frontendPort"] or "-")
    print("%-*s  %-10s %-11s %-9s %s" % (
        width, c["name"], c["status"], c["family"], ports, c["description"]))
' "$INDEX" "${1:-}"
}

lookup() {  # lookup <name> <field>
  py '
import json, sys
data = json.load(open(sys.argv[1]))
match = [c for c in data["components"] if c["name"].lower() == sys.argv[2].lower()]
if not match:
    names = [c["name"] for c in data["components"]]
    near = [n for n in names if sys.argv[2].lower() in n.lower()]
    raise SystemExit("unknown component %r%s\nTry: scripts/dev.sh --list" % (
        sys.argv[2], ("\nDid you mean: " + ", ".join(near)) if near else ""))
print(match[0][sys.argv[3]] if match[0][sys.argv[3]] is not None else "")
' "$INDEX" "$1" "$2"
}

case "${1:-}" in
  ""|-h|--help) usage; exit 0 ;;
  --list|-l)    list "${2:-}"; exit 0 ;;
esac

NAME="$(lookup "$1" name)"
DIR="$REPO/$(lookup "$1" directory)"
STATUS="$(lookup "$1" status)"
BACKEND_PORT="$(lookup "$1" backendPort)"
FRONTEND_PORT="$(lookup "$1" frontendPort)"
TRACE="$(lookup "$1" traceEndpoint)"

if [ ! -d "$DIR/backend" ]; then
  echo "$NAME is a $STATUS — it has a spec and reserved ports, but no backend yet."
  echo "Spec: $(lookup "$1" spec)"
  exit 1
fi

echo "$NAME  ($STATUS)"
echo "  backend   http://localhost:$BACKEND_PORT${TRACE:+$TRACE}"
echo "  frontend  http://localhost:$FRONTEND_PORT"
echo

backend_pid=""
frontend_pid=""
# npm and uvicorn --reload both fork, so stop the whole tree, children first.
kill_tree() {
  local pid="$1" child
  for child in $(pgrep -P "$pid" 2>/dev/null); do kill_tree "$child"; done
  kill "$pid" 2>/dev/null || true
}
cleanup() {
  trap - EXIT INT TERM
  [ -n "$frontend_pid" ] && kill_tree "$frontend_pid"
  [ -n "$backend_pid" ] && kill_tree "$backend_pid"
}
trap cleanup EXIT INT TERM

"$DIR/scripts/start_backend.sh" &
backend_pid=$!

if [ "${2:-}" = "--backend-only" ]; then
  wait "$backend_pid"
  exit 0
fi

# Give uvicorn a moment to claim the port before vite proxies at it. Polling
# beats sleeping: a cold start installs dependencies first.
for _ in $(seq 1 120); do
  if curl -sf "http://localhost:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
    echo "backend up on :$BACKEND_PORT"
    break
  fi
  kill -0 "$backend_pid" 2>/dev/null || { echo "backend exited"; exit 1; }
  sleep 1
done

# Not exec: the EXIT trap has to survive so stopping this script (Ctrl-C, or a
# plain kill) takes the background backend down with the frontend.
"$DIR/scripts/start_frontend.sh" &
frontend_pid=$!
wait "$frontend_pid"
