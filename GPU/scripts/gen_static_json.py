#!/usr/bin/env python3
"""Regenerate GPU/frontend/static.json — the static-hosting config
(docs/STATIC_HOSTING.md) that scripts/build_static.py reads.

    cd GPU/backend && .venv/bin/python ../scripts/gen_static_json.py

It lists what the builder cannot guess:
  * skip        the live routes (SSE, session store) — local-only by nature;
  * params      lesson ids (from backend/tours/lessons) and fleet profile names,
                so every tour recording is snapshotted on every die;
  * postBodies  the simulator's first-paint request for every profile, so the
                hosted page opens without waiting for the in-browser engine.
                The workload mirrors App.tsx's defaults; a drifted body is
                never an error — it just falls through to the engine.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent / "backend"
sys.path[:0] = [str(BACKEND), str(HERE.parent.parent)]

from app.profiles import PROFILES  # noqa: E402

DEFAULT_WORKLOAD = {  # App.tsx's initial state, in the shape api.ts sends
    "kind": "matmul", "N": 4, "M": 0, "K": 0, "dtype": "fp32", "seed": 0,
    "tileSize": 2, "doubleBuffer": False, "steps": 1, "blockSize": 0,
    "execution": "cuda", "gpus": 1,
}

lessons = sorted(p.stem for p in (BACKEND / "tours" / "lessons").glob("*.jsonl"))
bodies = [
    {"profile": p.model_dump(mode="json", by_alias=True), "workload": DEFAULT_WORKLOAD}
    for p in PROFILES.values()
]
cfg = {
    "skip": ["/api/live"],
    "params": {"lesson": lessons, "asProfile": list(PROFILES)},
    "postBodies": {"/api/simulate": bodies},
}
out = HERE.parent / "frontend" / "static.json"
out.write_text(json.dumps(cfg, indent=1) + "\n")
print(f"{out}: {len(lessons)} lessons, {len(PROFILES)} profiles, {len(bodies)} prebaked bodies")
