#!/usr/bin/env bash
# Run the existing smoke manifests against site/ served by a plain static
# server — no backend, no vite. Proves the hosted site works.
#
#   scripts/build_site.sh DellPowerStore PhysicsME5
#   scripts/smoke_static.sh                       every component in site/hosted.json
#   scripts/smoke_static.sh PhysicsME5 -- --grep scenario
#
# STATIC_PORT (default 6170 = CustomerSetup's 5170 + 1000) is the only port used.
# The physics apps download Pyodide from its CDN, so this check needs network.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE="${SITE_DIR:-$REPO/site}"
PORT="${STATIC_PORT:-6170}"
[ -f "$SITE/hosted.json" ] || { echo "no $SITE/hosted.json — run scripts/build_site.sh first"; exit 2; }

names=(); pw_args=()
while [ $# -gt 0 ]; do
  case "$1" in --) shift; pw_args=("$@"); break ;; *) names+=("$1"); shift ;; esac
done
if [ "${#names[@]}" -eq 0 ]; then
  mapfile -t names < <(python3 -c "import json,sys; print('\n'.join(json.load(open(sys.argv[1]))['built']))" "$SITE/hosted.json")
fi

if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then echo "port $PORT is in use (set STATIC_PORT)"; exit 2; fi
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$SITE" >/dev/null 2>&1 &
server=$!
trap 'kill $server 2>/dev/null' EXIT
for i in $(seq 1 20); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.5; done

fails=0; declare -a results
for name in "${names[@]}"; do
  echo "[$name] static smoke at http://127.0.0.1:$PORT/$name/"
  (cd "$REPO" && COMPONENT="$name" BASE_URL="http://127.0.0.1:$PORT" SMOKE_PATH="/$name/" \
    SMOKE_ARTIFACTS="$REPO/e2e/artifacts/static/$name" \
    SMOKE_OUTPUT="$REPO/e2e/test-results/static-$name" \
    npx playwright test -c e2e/playwright.config.ts "${pw_args[@]}")
  rc=$?; [ $rc -eq 0 ] && results+=("$name pass") || { results+=("$name FAIL"); fails=$((fails+1)); }
done

# Scenario-driven apps: the Pyodide engine must answer a body nobody prebaked
# exactly as the native engine does. ENGINE_BODY overrides the probe body.
for name in "${names[@]}"; do
  grep -q '"engine":true' "$SITE/$name/api-static/index.json" 2>/dev/null || continue
  probe="${ENGINE_BODY:-{\"durationMin\":977}}"
  expect="$(mktemp)"
  python3 "$REPO/scripts/static/native_answer.py" "$name" /api/simulate "$probe" >"$expect" 2>/dev/null
  (cd "$REPO" && SITE_URL="http://127.0.0.1:$PORT" COMPONENT="$name" BODY="$probe" EXPECT_JSON="$expect" \
    node e2e/static_engine.check.mjs) && results+=("$name engine pass") || { results+=("$name engine FAIL"); fails=$((fails+1)); }
  rm -f "$expect"
done

# The static pages: every localhost link must have been resolved or disabled.
(cd "$REPO" && SITE_URL="http://127.0.0.1:$PORT" node e2e/static_pages.check.mjs) \
  && results+=("pages pass") || { results+=("pages FAIL"); fails=$((fails+1)); }

# The course, clicked through: every module page, every lab stop, the Labs
# track and the capstone's coupled chain, hosted and with no backend.
(cd "$REPO" && SITE_URL="http://127.0.0.1:$PORT" node e2e/learn_clickthrough.check.mjs) \
  && results+=("learn pass") || { results+=("learn FAIL"); fails=$((fails+1)); }

echo; printf '%s\n' "${results[@]}"
[ "$fails" -eq 0 ]
