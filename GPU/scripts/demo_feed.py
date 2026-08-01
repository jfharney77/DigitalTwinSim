#!/usr/bin/env python3
"""demo_feed (spec_20 #19) — the full Live CUDA UI demo with no GPU and no
CUDA toolkit: replays a golden lesson recording through the REAL ingest
endpoint at watchable speed, so the die lights, the timeline grows, and the
counters move exactly as they would under hardware.

Usage:  ./demo_feed.py [lesson_id] [delay_seconds]
        ./demo_feed.py                 # 02_vector_add, 0.8s between events
        ./demo_feed.py 06_bandwidth 0.4
        ./demo_feed.py --all [delay]   # every lesson in sequence (demo reel)
Env:    TWIN_URL (default http://localhost:8000)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

TOURS = Path(__file__).resolve().parent.parent / "backend" / "tours" / "lessons"


def post(url: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{url}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def feed(url: str, lesson: str, delay: float) -> None:
    path = TOURS / f"{lesson}.jsonl"
    if not path.exists():
        options = ", ".join(sorted(p.stem for p in TOURS.glob("*.jsonl")))
        sys.exit(f"unknown lesson {lesson!r}; options: {options}")
    post(url, "/api/live/session", {"name": f"demo-{lesson}"})
    events = [json.loads(l)["event"] for l in path.read_text().splitlines() if l.strip()]
    print(f"feeding {len(events)} events from {lesson} -> {url} (Ctrl-C stops)")
    for i, event in enumerate(events, 1):
        post(url, "/api/live/ingest", event)
        print(f"  {i}/{len(events)} {event['type']}")
        time.sleep(delay)


def main() -> None:
    url = os.environ.get("TWIN_URL", "http://localhost:8000")
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        delay = float(sys.argv[2]) if len(sys.argv) > 2 else 0.8
        for p in sorted(TOURS.glob("*.jsonl")):
            feed(url, p.stem, delay)
    else:
        lesson = sys.argv[1] if len(sys.argv) > 1 else "02_vector_add"
        delay = float(sys.argv[2]) if len(sys.argv) > 2 else 0.8
        feed(url, lesson, delay)
    print("done — the recording(s) are in the Live tab's session list.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped")
    except urllib.error.URLError:
        sys.exit("backend unreachable — start it with ./GPU/scripts/start_backend.sh")
