#!/usr/bin/env python3
"""spec_31 Phase 4 — the rerunnable form of the hardware campaign.

Asserts that a curriculum run actually reached the backend: each probed
lesson 01–07 produced at least one kernel frame in the session, and lesson
00 delivered a ``device_info`` event. Invoked by ``make verify-hardware``
(which lints, builds, opens a named session via ``--preflight``, runs the
whole curriculum, then calls this checker) — but it can be pointed at any
kept session with ``--session``.

Stdlib only, on purpose: campaign day must not start with pip.

Exit codes: 0 all lessons PASS · 1 one or more lessons FAIL ·
2 backend unreachable (actionable message printed, nothing "failed").
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URL = os.environ.get("TWIN_URL", "http://localhost:8000")
SESSION_NAME = "verify-hardware"

# What each lesson leaves behind in a session. Kernel names are the ones the
# lessons pass to probe.flush(); 03 sweeps block sizes so it matches by
# prefix. Lessons 02 and 07 share the name "vector_add" — in a run-all
# session the pair is proven by requiring two runs of it.
KERNEL_CHECKS: list[tuple[str, str, bool, int]] = [
    # (lesson, kernel name or prefix, prefix-match?, min runs)
    ("01_hello_thread", "hello_thread", False, 1),
    ("02_vector_add", "vector_add", False, 1),
    ("03_block_size", "vector_add_bs", True, 1),
    ("04_matmul_naive", "matmul_naive", False, 1),
    ("05_matmul_tiled", "matmul_tiled", False, 1),
    ("06_bandwidth", "stream_copy", False, 1),
    ("07_bigger_dies", "vector_add", False, 2),  # shares 02's kernel name
]

# Mirrors app/tour.py::device_name_is_generic (markers) + the profile-label
# half, resolved live from /api/profiles when the backend is up.
GENERIC_MARKERS = ("representative", "generic")


def _get(url: str, path: str) -> object:
    with urllib.request.urlopen(url + path, timeout=5) as r:
        return json.loads(r.read().decode())


def _post(url: str, path: str, body: dict) -> object:
    req = urllib.request.Request(
        url + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())


def _delete(url: str, path: str) -> None:
    req = urllib.request.Request(url + path, method="DELETE")
    with urllib.request.urlopen(req, timeout=5):
        pass


def _backend_or_exit(url: str) -> None:
    try:
        _get(url, "/api/health")
    except (urllib.error.URLError, OSError, ValueError):
        print(f"verify-hardware: backend unreachable at {url}")
        print("  The probe degrades to stderr when offline — a run without the")
        print("  backend produces no session and nothing to verify.")
        print("  Fix: start it (GPU/scripts/start_all.sh, or")
        print("  `cd GPU/backend && . .venv/bin/activate && uvicorn app.main:app`),")
        print("  or point TWIN_URL / --url at where it actually listens.")
        sys.exit(2)


def preflight(url: str) -> None:
    """Backend up? Then open the named campaign session so run-all lands in a
    kept, named recording — never the anonymous adhoc session."""
    _backend_or_exit(url)
    info = _post(url, "/api/live/session", {"name": SESSION_NAME})
    print(f"verify-hardware: backend OK at {url}; recording into session "
          f"{info.get('id', '?')!r}")


def _pick_session(url: str, session_id: str | None) -> str:
    if session_id:
        return session_id
    sessions = _get(url, "/api/live/sessions?limit=10")
    if not isinstance(sessions, list) or not sessions:
        print("verify-hardware: no sessions found — did run-all execute with")
        print("  the backend up? (`make verify-hardware` runs the whole ladder;")
        print("  events printed to stderr mean the backend was unreachable.)")
        sys.exit(2)
    active = [s for s in sessions if s.get("active")]
    chosen = active[0] if active else sessions[0]  # newest first
    return str(chosen["id"])


def verify(url: str, session_id: str | None) -> int:
    _backend_or_exit(url)
    sid = _pick_session(url, session_id)
    summary = _get(url, f"/api/live/sessions/{sid}/summary")
    assert isinstance(summary, dict)
    device_name = summary.get("deviceName")
    stats = {s["kernel"]: s.get("runs", 0) for s in summary.get("kernelStats", [])}

    print(f"verify-hardware: session {sid!r} — {summary.get('frames', 0)} frames, "
          f"{summary.get('kernelLaunches', 0)} kernel launches, "
          f"device {device_name!r}")

    failures = 0

    # Lesson 00 emits device_info only: the session's device frame is its proof.
    if device_name:
        print("  PASS 00_device_query      device_info received "
              f"({device_name!r})")
    else:
        failures += 1
        print("  FAIL 00_device_query      no device_info in session — the "
              "probe emits it; twin-sampler alone cannot (see cuda/README.md)")

    for lesson, kernel, prefix, min_runs in KERNEL_CHECKS:
        if prefix:
            runs = sum(n for k, n in stats.items() if k.startswith(kernel))
            label = f"kernel {kernel}*"
        else:
            runs = stats.get(kernel, 0)
            label = f"kernel {kernel!r}"
        if runs >= min_runs:
            note = " (shared name: covers 02+07)" if min_runs > 1 else ""
            print(f"  PASS {lesson:<20} {label} ×{runs}{note}")
        else:
            failures += 1
            need = f"needs ≥{min_runs} run(s), saw {runs}"
            print(f"  FAIL {lesson:<20} {label} — {need}")

    # Advisory, not a gate: a campaign session should carry the driver's name.
    if device_name:
        lowered = device_name.strip().lower()
        profile_names: set[str] = set()
        try:
            profiles = _get(url, "/api/profiles")
            if isinstance(profiles, list):
                profile_names = {p.get("name", "") for p in profiles}
        except (urllib.error.URLError, OSError, ValueError):
            pass
        if (
            not lowered
            or any(m in lowered for m in GENERIC_MARKERS)
            or device_name in profile_names
        ):
            print(f"  WARN device name {device_name!r} looks generic — a "
                  "hardware capture must carry the driver-reported name "
                  "(spec_31 promotion rules)")

    # Advisory: lesson 06 should have refreshed the roofline calibration.
    try:
        meas = _get(url, "/api/measurements")
        if isinstance(meas, dict) and "stream_gbps" in meas:
            v = meas["stream_gbps"].get("value")
            print(f"  note stream_gbps calibration present ({v} GB/s, "
                  f"measured {meas['stream_gbps'].get('measuredAt')})")
        else:
            print("  note no stream_gbps calibration yet — lesson 06 posts it "
                  "(spec_15; Phase 3 of the campaign)")
    except (urllib.error.URLError, OSError, ValueError):
        pass

    # Close our named session so the recording is kept, not still recording.
    try:
        sessions = _get(url, "/api/live/sessions?limit=10")
        is_active = isinstance(sessions, list) and any(
            s.get("id") == sid and s.get("active") for s in sessions
        )
        if is_active:
            _delete(url, "/api/live/session")
            print(f"  session {sid!r} closed and kept")
    except (urllib.error.URLError, OSError, ValueError):
        pass

    if failures:
        print(f"verify-hardware: FAIL — {failures} check(s) failed")
        return 1
    print("verify-hardware: PASS — every probed lesson reached the backend")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default=DEFAULT_URL,
                    help=f"backend base URL (default {DEFAULT_URL})")
    ap.add_argument("--session", default=None,
                    help="session id to verify (default: active, else newest)")
    ap.add_argument("--preflight", action="store_true",
                    help="check the backend and open the campaign session, "
                         "then exit — run before `make run-all`")
    args = ap.parse_args()
    if args.preflight:
        preflight(args.url)
        return 0
    return verify(args.url, args.session)


if __name__ == "__main__":
    sys.exit(main())
