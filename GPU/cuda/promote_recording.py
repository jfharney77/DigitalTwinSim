#!/usr/bin/env python3
"""spec_31 Phase 1 step 3 — promote a captured session to a golden recording.

Downloads a named session's JSONL from the backend and installs it over the
representative golden recording at ``backend/tours/lessons/<lesson>.jsonl``
— after checking the promotion rules, and never silently:

- the recording must open with a ``device_info`` frame whose name is
  non-generic (a real driver-reported name, not empty, not a placeholder,
  not one of the simulator's profile labels) — a hardware claim must carry
  a real device's signature;
- its kernel frames must cover the lesson (≥1 launch of the lesson's
  kernel);
- its SM count must match the golden recording it replaces — which is what
  keeps the two lesson-07 steps representative forever on a 24-SM die
  (spec_31 Phase 2): a 4060 capture can never impersonate an H100 or B300.

Dry-run by default; ``--write`` performs the overwrite. The flip of the tour
step's ``provenance`` to "hardware" (and any cursor re-pin) is a deliberate
human edit in ``backend/app/tour.py`` — this tool reminds, it never edits.
No hand-editing of JSONL: if a capture is bad, capture again.

Usage:
    python3 promote_recording.py <session_id> <lesson_id> [--write]
    python3 promote_recording.py --file capture.jsonl <lesson_id> [--write]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_URL = os.environ.get("TWIN_URL", "http://localhost:8000")
TOURS_DIR = Path(__file__).resolve().parent.parent / "backend" / "tours" / "lessons"

# Mirrors app/tour.py::device_name_is_generic; the profile-label half is
# resolved live from /api/profiles (with a static fallback when offline).
GENERIC_MARKERS = ("representative", "generic")
FALLBACK_PROFILE_LABELS = {
    "Generic-128", "Generic-512", "RTX-4060-Laptop", "H100-SXM",
    "B300-Blackwell-Ultra", "RTX-5090", "MI300X",
}

# The kernel each lesson's probe flushes (03 sweeps sizes → prefix match).
LESSON_KERNELS: dict[str, tuple[str, bool]] = {
    "01_hello_thread": ("hello_thread", False),
    "02_vector_add": ("vector_add", False),
    "03_block_size": ("vector_add_bs", True),
    "04_matmul_naive": ("matmul_naive", False),
    "05_matmul_tiled": ("matmul_tiled", False),
    "06_bandwidth": ("stream_copy", False),
    "07_bigger_dies": ("vector_add", False),
    "07_bigger_dies_blackwell": ("vector_add", False),
}


def _fail(msg: str) -> None:
    print(f"promote: REFUSED — {msg}")
    sys.exit(1)


def _parse(jsonl: str) -> list[dict]:
    events = []
    for i, line in enumerate(jsonl.splitlines()):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as e:
            _fail(f"line {i + 1} is not JSON ({e}) — capture again, "
                  "never hand-edit a recording")
    return events


def _profile_labels(url: str) -> set[str]:
    try:
        with urllib.request.urlopen(url + "/api/profiles", timeout=5) as r:
            profiles = json.loads(r.read().decode())
        return {p.get("name", "") for p in profiles}
    except (urllib.error.URLError, OSError, ValueError):
        return set(FALLBACK_PROFILE_LABELS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("session_id", nargs="?", default=None,
                    help="session to download from the backend")
    ap.add_argument("lesson_id", choices=sorted(LESSON_KERNELS),
                    help="golden recording to replace")
    ap.add_argument("--file", default=None,
                    help="promote a local JSONL instead of downloading")
    ap.add_argument("--url", default=DEFAULT_URL,
                    help=f"backend base URL (default {DEFAULT_URL})")
    ap.add_argument("--write", action="store_true",
                    help="actually overwrite the golden (default: dry run)")
    args = ap.parse_args()

    # -- fetch ---------------------------------------------------------------
    if args.file:
        raw = Path(args.file).read_text()
        source = args.file
    elif args.session_id:
        path = f"/api/live/sessions/{args.session_id}/download"
        try:
            with urllib.request.urlopen(args.url + path, timeout=10) as r:
                raw = r.read().decode()
        except urllib.error.HTTPError as e:
            _fail(f"backend returned {e.code} for session "
                  f"{args.session_id!r} — check `GET /api/live/sessions`")
            return 1
        except (urllib.error.URLError, OSError):
            print(f"promote: backend unreachable at {args.url} — start it "
                  "(GPU/scripts/start_all.sh) or use --file with a "
                  "downloaded JSONL")
            return 2
        source = f"session {args.session_id!r}"
    else:
        ap.error("give a session_id or --file")
        return 2

    events = _parse(raw)
    if not events:
        _fail("recording is empty")

    # -- rule: opens with a non-generic device_info --------------------------
    first = events[0].get("event", {})
    if first.get("type") != "device_info":
        _fail("recording does not open with a device_info frame — the probe "
              "emits one per run; twin-sampler alone cannot (cuda/README.md)")
    name = (first.get("name") or "").strip()
    lowered = name.lower()
    if not name or any(m in lowered for m in GENERIC_MARKERS):
        _fail(f"device name {name!r} is generic — a hardware recording must "
              "carry the driver-reported name (spec_31 promotion rules)")
    if name in _profile_labels(args.url):
        _fail(f"device name {name!r} is a simulator profile label, not a "
              "driver-reported name")

    # -- rule: kernel frames cover the lesson --------------------------------
    kernel, prefix = LESSON_KERNELS[args.lesson_id]
    launches = [
        e for e in events
        if e.get("event", {}).get("type") == "kernel_launch"
        and (
            e["event"].get("kernel", "").startswith(kernel)
            if prefix else e["event"].get("kernel") == kernel
        )
    ]
    if not launches:
        _fail(f"no kernel_launch of {kernel!r}{'*' if prefix else ''} in the "
              f"recording — it does not cover lesson {args.lesson_id}")

    # -- rule: SM count matches the golden it replaces (Phase 2) -------------
    golden = TOURS_DIR / f"{args.lesson_id}.jsonl"
    if not golden.exists():
        _fail(f"no golden recording at {golden} — nothing to promote over")
    golden_first = json.loads(golden.read_text().splitlines()[0])["event"]
    want_sms, got_sms = golden_first.get("smCount"), first.get("smCount")
    if want_sms != got_sms:
        _fail(
            f"SM count {got_sms} ≠ the golden's {want_sms} — this step "
            "narrates a different die. spec_31 Phase 2: a recording claiming "
            f"{want_sms} SMs cannot come from a {got_sms}-SM device; the "
            "07_bigger_dies steps stay representative forever on this machine."
        )

    # -- report + write ------------------------------------------------------
    n_events = len(events)
    print(f"promote: {source} → {golden}")
    print(f"  device   {name!r} ({got_sms} SMs)")
    print(f"  covers   {len(launches)} launch(es) of "
          f"{kernel!r}{'*' if prefix else ''}")
    print(f"  events   {n_events} (golden currently has "
          f"{sum(1 for line in golden.read_text().splitlines() if line.strip())})")

    if not args.write:
        print("promote: dry run — all promotion rules pass; rerun with "
              "--write to install")
        return 0

    golden.write_text(raw if raw.endswith("\n") else raw + "\n")
    print("promote: golden replaced. Now finish the promotion by hand:")
    print("  1. backend/app/tour.py — flip this step's provenance to "
          "\"hardware\"")
    print("  2. re-pin the step's cursor if the frame count changed "
          "(cursor frames must be kernel frames)")
    print("  3. edit the script ONLY where it states machine-specific "
          "numbers; the teaching prose survives untouched")
    print("  4. cd ../backend && python -m pytest -q  (test_tour.py gates "
          "every promotion)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
