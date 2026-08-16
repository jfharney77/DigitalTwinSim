"""spec_18 — lesson-tour invariants (same style as the repo's tour spec)."""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi.testclient import TestClient

from app.live_store import load_recording
from app.main import TOURS_DIR, app
from app.tour import build_tour

client = TestClient(app)


def test_tour_module_is_pure() -> None:
    src = (Path(__file__).parent.parent / "app" / "tour.py").read_text()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            for n in names:
                # spec_29: "leveling" is allowed because it imports nothing
                # but typing — registering variants keeps the module pure.
                assert n.split(".")[0] in {
                    "__future__", "typing", "", "models", "leveling",
                }, f"impure import {n}"


def test_every_step_resolves_and_cursor_is_valid() -> None:
    tour = build_tour()
    assert tour.steps, "empty tour"
    for step in tour.steps:
        path = TOURS_DIR / f"{step.lesson_id}.jsonl"
        assert path.exists(), f"missing golden recording {step.lesson_id}"
        trace = load_recording(path, step.lesson_id)
        assert 0 <= step.cursor < len(trace), f"{step.id}: cursor out of range"
        assert step.script.strip()
        assert step.provenance in ("hardware", "representative")


def test_cursor_frames_are_kernel_frames() -> None:
    # Each step narrates a kernel moment; pinning an idle sample would show
    # a dark die under a script describing activity.
    for step in build_tour().steps:
        trace = load_recording(TOURS_DIR / f"{step.lesson_id}.jsonl", step.lesson_id)
        assert trace[step.cursor].kind == "kernel", step.id


def test_tour_endpoints() -> None:
    r = client.get("/api/tour")
    assert r.status_code == 200
    tour = r.json()
    first = tour["steps"][0]["lessonId"]
    rec = client.get(f"/api/tour/recordings/{first}")
    assert rec.status_code == 200
    assert rec.json()["trace"]
    assert client.get("/api/tour/recordings/nope").status_code == 404
    assert client.get("/api/tour/recordings/..%2fescape").status_code == 404


def test_every_tour_script_is_registered_at_the_ends() -> None:
    # spec_29: the tour is the beginner path, so it gets no fallbacks — the
    # intro, every step script, and every experiment must be authored at
    # levels 1 AND 5 (regions may fall back; the tour may not).
    from app.leveling import registry

    reg = registry()
    tour = build_tour()
    blocks = [("intro", tour.intro)]
    blocks += [(f"{s.id}.script", s.script) for s in tour.steps]
    blocks += [
        (f"{s.id}.experiment", s.experiment)
        for s in tour.steps
        if s.experiment is not None
    ]
    assert len(blocks) == 1 + 8 + 6  # intro + scripts + experiments
    for name, text in blocks:
        assert text in reg, f"{name} is not registered"
        variants = reg[text]
        assert 1 in variants, f"{name} has no novice variant"
        assert 5 in variants, f"{name} has no expert variant"


def test_tour_endpoint_levels() -> None:
    # spec_29: resolution happens at the transport edge. Level 3 is
    # byte-identical to the unparameterized response; the ends differ for
    # every step script.
    base = client.get("/api/tour").json()
    assert client.get("/api/tour?level=3").json() == base
    novice = client.get("/api/tour?level=1").json()
    expert = client.get("/api/tour?level=5").json()
    assert novice["intro"] != base["intro"]
    for s3, s1, s5 in zip(base["steps"], novice["steps"], expert["steps"]):
        assert s1["script"] != s5["script"], s3["id"]
        assert s1["script"] != s3["script"], s3["id"]
        # names and structure are level-invariant
        assert s1["id"] == s3["id"] == s5["id"]
        assert s1["cursor"] == s3["cursor"]


def test_recordings_replay_in_ci() -> None:
    for p in sorted(TOURS_DIR.glob("*.jsonl")):
        trace = load_recording(p)
        assert trace, f"{p.name} replays empty"
        assert trace[0].kind == "device"  # geometry travels with the recording


def test_authored_links_resolve() -> None:
    # spec_30: a tour link must never 404 into a blank floorplan. The grammar
    # is exactly the frontend's: "#" (simulator), "#live"/"#live/tour",
    # "#anatomy[/<die>[/<region>]]", and "#anatomy/<a>/vs/<b>".
    from app.anatomy import ANATOMIES

    linked = [s for s in build_tour().steps if s.link is not None]
    assert linked, "spec_30 authored at least one tour link"
    for step in linked:
        link = step.link
        assert link is not None and link.startswith("#"), step.id
        body = link[1:]
        if body in ("", "live", "live/tour"):
            continue
        parts = body.split("/")
        assert parts[0] == "anatomy", f"{step.id}: unknown hash {link!r}"
        if len(parts) == 1:
            continue
        if len(parts) == 4 and parts[2] == "vs":
            assert parts[1] in ANATOMIES, f"{step.id}: unknown die {parts[1]!r}"
            assert parts[3] in ANATOMIES, f"{step.id}: unknown die {parts[3]!r}"
            continue
        die = ANATOMIES.get(parts[1])
        assert die is not None, f"{step.id}: unknown die {parts[1]!r}"
        if len(parts) == 3:
            assert any(r.id == parts[2] for r in die.regions), (
                f"{step.id}: unknown region {parts[2]!r} on {die.id}"
            )
        else:
            assert len(parts) == 2, f"{step.id}: bad hash grammar {link!r}"


def test_hardware_steps_carry_a_real_device_signature() -> None:
    # spec_31: a tour step claiming provenance="hardware" must open with a
    # device_info frame whose name is non-generic — not empty, not a
    # placeholder, and not one of the simulator's own profile labels. A
    # hardware claim must carry a real device's signature. Vacuously green
    # while every step is representative; load-bearing the day one flips.
    from app.live import DeviceInfoEvent
    from app.live_store import load_events
    from app.profiles import PROFILES
    from app.tour import device_name_is_generic

    # The predicate itself is exercised even while the loop is vacuous —
    # the test must be doing work today, not just on campaign day.
    assert device_name_is_generic(None)
    assert device_name_is_generic("")
    assert device_name_is_generic("   ")
    assert device_name_is_generic("Representative 24-SM die")
    assert device_name_is_generic("Generic-128")
    assert not device_name_is_generic("NVIDIA GeForce RTX 4060 Laptop GPU")

    for step in build_tour().steps:
        if step.provenance != "hardware":
            continue
        events = load_events(TOURS_DIR / f"{step.lesson_id}.jsonl")
        assert events, f"{step.id}: empty recording"
        first = events[0].event
        assert isinstance(first, DeviceInfoEvent), (
            f"{step.id}: hardware recording must open with device_info"
        )
        assert not device_name_is_generic(first.name), (
            f"{step.id}: hardware claim with generic device name {first.name!r}"
        )
        assert first.name not in PROFILES, (
            f"{step.id}: hardware claim carrying a simulator profile label "
            f"{first.name!r} instead of a driver-reported name"
        )


def test_the_payoff_links_are_authored() -> None:
    # spec_30 names the lesson-07 pair and the roofline step explicitly.
    links = {s.id: s.link for s in build_tour().steps}
    assert links["the-die-is-a-parameter"] == "#anatomy/gh100"
    assert links["blackwell-two-dies-one-gpu"] == "#anatomy/gb300/vs/gb200"
    assert links["the-roof"] == "#"  # the simulator's roofline read-out
