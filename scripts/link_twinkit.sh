#!/usr/bin/env bash
# Make the repo-root `twinkit` package importable from a component's venv.
#
# Every component backend has its own .venv, and `twinkit/` lives at the repo
# root rather than on PyPI. A one-line .pth file in the venv's site-packages
# is the least invasive way to join the two: no install step, no network, no
# build backend, and removing it is `rm`.
#
#   scripts/link_twinkit.sh                 # every component venv
#   scripts/link_twinkit.sh GPU/backend/.venv   # just that one
#
# Idempotent. Silently skips venvs that do not exist yet — start_backend.sh
# calls this after creating one.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

link_one() {
  local venv="$1"
  [ -d "$venv" ] || return 0
  local site
  site="$(find "$venv" -maxdepth 4 -type d -name site-packages -print -quit)"
  [ -n "$site" ] || return 0
  printf '%s\n' "$REPO" > "$site/twinkit.pth"
  echo "linked twinkit -> $venv"
}

if [ "$#" -gt 0 ]; then
  for v in "$@"; do link_one "$v"; done
else
  for v in "$REPO"/*/backend/.venv; do link_one "$v"; done
fi
