#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND="$ROOT/backend"

cd "$BACKEND"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

if [ -f ".venv/Scripts/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/Scripts/activate"
else
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

if [ -f "requirements.txt" ]; then
  pip install -q -r requirements.txt
fi

exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8045
