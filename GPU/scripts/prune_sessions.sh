#!/usr/bin/env bash
# Prune ad-hoc live recordings (spec_19 #20): sessions auto-started by an
# unattended probe pile up as "...-adhoc.jsonl". Named recordings are kept.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backend/sessions"
[ -d "$DIR" ] || { echo "no sessions directory yet"; exit 0; }
count=$(find "$DIR" -name '*-adhoc.jsonl' | wc -l)
find "$DIR" -name '*-adhoc.jsonl' -delete
echo "pruned $count ad-hoc recording(s); named recordings kept."
