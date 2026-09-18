#!/usr/bin/env bash
# Browser smoke test for one component, or all of them.
#
#   scripts/smoke.sh GPU              start GPU's backend + frontend, run e2e/smoke.spec.ts, stop both
#   scripts/smoke.sh GPU --keep       leave both servers running afterwards (Ctrl-C / kill to stop)
#   scripts/smoke.sh GPU -- --grep tour   pass anything after `--` straight to `playwright test`
#   scripts/smoke.sh --all            every reference/built/partial component, one at a time, then a table
#
# SMOKE_BACKEND_PORT / SMOKE_FRONTEND_PORT override the registry ports for a
# single-component run when something unrelated already holds them.
# Playwright's output (traces of failed tests) goes to e2e/test-results/<Component>/,
# so smoke runs of different components can overlap; SMOKE_OUTPUT overrides it
# and SMOKE_TRACE=off turns traces off.
#
# Ports come from components.json. The manifest the spec reads is
# <Component>/frontend/smoke.json (schema: e2e/README.md). Screenshots land in
# e2e/artifacts/<Component>/, server logs in e2e/artifacts/<Component>/*.log.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INDEX="$REPO/components.json"

field() {  # field <name> <key>
  python3 - "$INDEX" "$1" "$2" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
m = [c for c in data["components"] if c["name"].lower() == sys.argv[2].lower()]
if not m:
    raise SystemExit("unknown component %r (scripts/dev.sh --list)" % sys.argv[2])
v = m[0][sys.argv[3]]
print("" if v is None else v)
PY
}

runnable() {
  python3 - "$INDEX" <<'PY'
import json, sys
for c in json.load(open(sys.argv[1]))["components"]:
    if c["status"] in ("reference", "built", "partial") and c["backendPort"]:
        print(c["name"])
PY
}

port_busy() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

kill_tree() {
  local pid="$1" child
  for child in $(pgrep -P "$pid" 2>/dev/null); do kill_tree "$child"; done
  kill "$pid" 2>/dev/null || true
}

wait_http() {  # wait_http <url> <pid> <seconds>
  local i
  for i in $(seq 1 "$3"); do
    curl -sf -o /dev/null "$1" && return 0
    kill -0 "$2" 2>/dev/null || return 1
    sleep 1
  done
  return 1
}

smoke_one() {  # smoke_one <name> [--keep] [-- <playwright args>]; returns the spec's exit code
  local name dir bport fport keep="" out backend_pid="" frontend_pid="" rc
  local -a pw_args=()
  local want="$1"; shift
  while [ $# -gt 0 ]; do
    case "$1" in
      --keep) keep="--keep"; shift ;;
      --) shift; pw_args=("$@"); break ;;
      *) echo "unknown argument: $1 (extra playwright args go after --)"; return 2 ;;
    esac
  done
  set -- "$want"
  name="$(field "$1" name)" || return 2
  dir="$REPO/$(field "$name" directory)"
  bport="${SMOKE_BACKEND_PORT:-$(field "$name" backendPort)}"
  fport="${SMOKE_FRONTEND_PORT:-$(field "$name" frontendPort)}"
  out="$REPO/e2e/artifacts/$name"

  if [ ! -f "$dir/frontend/smoke.json" ]; then
    echo "[$name] no frontend/smoke.json — nothing to run (schema: e2e/README.md)"
    return 3
  fi
  for p in "$bport" "$fport"; do
    if port_busy "$p"; then
      echo "[$name] port $p is already in use — stop whatever holds it (scripts/dev.sh, another twin) and retry"
      return 2
    fi
  done
  mkdir -p "$out"

  cleanup_one() {
    [ -n "$frontend_pid" ] && kill_tree "$frontend_pid"
    [ -n "$backend_pid" ] && kill_tree "$backend_pid"
    # Reap them, and give the ports a moment to close, so the next component
    # in --all (PowerMax and E3200 share ports) does not see them busy.
    wait $frontend_pid $backend_pid 2>/dev/null
    local i
    for i in $(seq 1 20); do
      port_busy "$bport" || port_busy "$fport" || break
      sleep 0.5
    done
    frontend_pid=""; backend_pid=""
  }
  trap 'cleanup_one; exit 130' INT TERM

  # Backend: the start_backend.sh recipe, minus --reload (it forks a watcher)
  # and with this component's port instead of the script's hard-coded 8000.
  (
    cd "$dir/backend" || exit 1
    # `python -m` rather than .venv/bin/uvicorn: a venv that was moved (GPU's
    # was created at the old backend/ path) keeps stale shebangs in its scripts.
    if ! .venv/bin/python -c "import uvicorn, fastapi" 2>/dev/null; then
      [ -x .venv/bin/python ] || python3 -m venv .venv || exit 1
      .venv/bin/python -m pip install -q -r requirements.txt || exit 1
    fi
    "$REPO/scripts/link_twinkit.sh" "$dir/backend/.venv" >/dev/null
    export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
    exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$bport"
  ) >"$out/backend.log" 2>&1 &
  backend_pid=$!

  # Frontend: root npm workspaces own node_modules; vite gets the port on the
  # command line (strict, so a collision fails loudly) and the proxy target.
  (
    cd "$dir/frontend" || exit 1
    export API_TARGET="http://127.0.0.1:$bport"
    exec npx vite --port "$fport" --strictPort --host 127.0.0.1
  ) >"$out/frontend.log" 2>&1 &
  frontend_pid=$!

  if ! wait_http "http://127.0.0.1:$bport/api/health" "$backend_pid" 120; then
    echo "[$name] backend did not come up on :$bport — see $out/backend.log"
    tail -20 "$out/backend.log"; cleanup_one; trap - INT TERM; return 2
  fi
  if ! wait_http "http://127.0.0.1:$fport/" "$frontend_pid" 60; then
    echo "[$name] frontend did not come up on :$fport — see $out/frontend.log"
    tail -20 "$out/frontend.log"; cleanup_one; trap - INT TERM; return 2
  fi

  echo "[$name] backend :$bport  frontend :$fport  — running smoke spec"
  (cd "$REPO" && COMPONENT="$name" BASE_URL="http://127.0.0.1:$fport" \
    SMOKE_OUTPUT="${SMOKE_OUTPUT:-$REPO/e2e/test-results/$name}" \
    npx playwright test -c e2e/playwright.config.ts "${pw_args[@]}")
  rc=$?

  if [ "$keep" = "--keep" ]; then
    echo "[$name] --keep: servers left running (backend pid $backend_pid, frontend pid $frontend_pid). Ctrl-C to stop."
    trap 'cleanup_one; exit 0' INT TERM
    wait "$frontend_pid"
  fi
  cleanup_one
  trap - INT TERM
  return $rc
}

case "${1:-}" in
  ""|-h|--help)
    sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
  --all)
    declare -a names results
    fails=0
    for n in $(runnable); do
      smoke_one "$n"; rc=$?
      case $rc in
        0) r="pass" ;;
        3) r="no manifest" ;;
        2) r="FAIL (startup)"; fails=$((fails + 1)) ;;
        *) r="FAIL"; fails=$((fails + 1)) ;;
      esac
      names+=("$n"); results+=("$r")
    done
    echo
    printf '%-28s %s\n' "Component" "Smoke"
    for i in "${!names[@]}"; do printf '%-28s %s\n' "${names[$i]}" "${results[$i]}"; done
    echo
    echo "$fails failing. Screenshots and server logs: e2e/artifacts/<Component>/"
    [ "$fails" -eq 0 ]; exit $? ;;
  *)
    smoke_one "$@"; rc=$?
    [ $rc -eq 3 ] && rc=1
    exit $rc ;;
esac
