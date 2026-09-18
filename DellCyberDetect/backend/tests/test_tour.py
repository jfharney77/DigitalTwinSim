"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is Cyber
Detect's: the signature beat pins the blind step, and nothing in the tour
reveals corruption before content analysis has run."""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

import app.tour
from app.anatomy import ANATOMY, CLEAN_SNAPSHOTS, TOTAL_SNAPSHOTS
from app.engine import simulate
from app.leveling import LEVELS, registry
from app.main import app as api
from app.tour import SIGNATURE_STEP_ID, TOUR_RESPONSE, build_tour, layer_map
from twinkit.testing import assert_deterministic, assert_tour_invariants

PUBLIC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "public"
TOUR = TOUR_RESPONSE.tour
STEPS = {s.id: s for s in TOUR.steps}
SNAPS = {f"snap-{i}" for i in range(1, TOTAL_SNAPSHOTS + 1)}


def test_tour_invariants():
    assert_tour_invariants(
        TOUR_RESPONSE,
        ANATOMY,
        simulate(),
        SIGNATURE_STEP_ID,
        module=app.tour,
        public_dir=PUBLIC,
    )


def test_tour_is_deterministic():
    assert_deterministic(lambda: build_tour(ANATOMY))


def test_six_to_nine_beats_exterior_first():
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_pins_the_blind_step():
    """The narration and the trace say the same thing at the same moment:
    corruption present, alerts at zero, nothing yet read."""
    state = simulate()[STEPS[SIGNATURE_STEP_ID].trace_cursor]
    assert state.phase == "blind"
    assert state.label == "Metadata and behaviour detection see nothing"
    assert state.snapshots_corrupted == 4
    assert state.metadata_alerts == 0
    assert state.content_confidence_percent == 0


def test_the_signature_step_shows_the_whole_timeline():
    """The viewer must see every snapshot at once to be unable to tell them
    apart — so all seven are lit and all seven are in frame."""
    step = STEPS[SIGNATURE_STEP_ID]
    assert SNAPS <= set(step.region_ids)
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid


def test_no_beat_reveals_corruption_before_the_bytes_are_read():
    """TimelineView draws corruption only once confidence is nonzero. Every
    beat up to and including the inspection pins a state where that is
    still false, so the tour never marks the copies early."""
    trace = simulate()
    inspect_idx = next(i for i, s in enumerate(trace) if s.phase == "inspect")
    early = [s for s in TOUR.steps if s.trace_cursor <= inspect_idx]
    assert len(early) >= 3
    for s in early:
        assert trace[s.trace_cursor].content_confidence_percent == 0, s.id


def test_confidence_beat_is_the_first_scored_state():
    trace = simulate()
    first = next(i for i, s in enumerate(trace) if s.content_confidence_percent > 0)
    assert STEPS["confidence-climbs"].trace_cursor == first


def test_the_verdict_beat_lights_the_named_copy():
    trace = simulate()
    step = STEPS["verdict-is-a-date"]
    state = trace[step.trace_cursor]
    assert state.phase == "verdict"
    assert state.last_clean_snapshot == CLEAN_SNAPSHOTS
    assert f"snap-{state.last_clean_snapshot}" in step.region_ids
    assert "verdict" in step.region_ids
    lit_snaps = set(step.region_ids) & SNAPS
    assert lit_snaps == {f"snap-{state.last_clean_snapshot}"}


def test_the_recovery_beat_restores_from_the_named_copy():
    trace = simulate()
    step = STEPS["recover-named-copy"]
    state = trace[step.trace_cursor]
    assert state.phase == "recover"
    assert {"recovery", "verdict", f"snap-{state.last_clean_snapshot}"} <= set(
        step.region_ids
    )
    # Never the newest copy.
    assert f"snap-{TOTAL_SNAPSHOTS}" not in step.region_ids


def test_the_longest_stage_gets_a_beat():
    """Content inspection is the trace's longest stage; the tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert trace[longest].phase == "inspect"
    assert longest in {s.trace_cursor for s in TOUR.steps}


def test_layers_put_the_machinery_deepest():
    layers = layer_map(ANATOMY)
    assert layers["array"] == 0
    assert all(layers[s] == 1 for s in SNAPS)
    assert layers["inspect"] == layers["classifier"] == layers["models"] == 2


def test_every_script_is_authored_at_one_three_and_five():
    reg = registry()
    for step in TOUR.steps:
        variants = reg.get(step.script)
        assert variants is not None, f"{step.id}: script is not wrapped in L()"
        assert {1, 3, 5} <= set(variants), f"{step.id}: levels {sorted(variants)}"
        assert len(variants[1]) > len(variants[5]), step.id


def test_endpoint_serves_the_tour_at_every_level():
    client = TestClient(api)
    base = client.get("/api/tour").json()
    assert base["tour"]["steps"][0]["id"] == "snapshot-timeline"
    assert set(base["layers"]) == {r.id for r in ANATOMY.regions}
    assert base["mapWidth"] == ANATOMY.width
    scripts = {}
    for level in LEVELS:
        body = client.get(f"/api/tour?level={level}").json()
        assert [s["id"] for s in body["tour"]["steps"]] == list(STEPS)
        scripts[level] = [s["script"] for s in body["tour"]["steps"]]
        assert all(text.strip() for text in scripts[level])
    assert scripts[3] == [s.script for s in TOUR.steps]
    assert scripts[1] != scripts[5]


def _in_frame(cam, r) -> bool:
    return (
        cam.x <= r.x + 1e-6
        and r.x + r.w <= cam.x + cam.w + 1e-6
        and cam.y <= r.y + 1e-6
        and r.y + r.h <= cam.y + cam.h + 1e-6
    )


def test_every_lit_region_is_in_frame():
    """The camera frames what the beat talks about. The production volume is
    a full-width banner, so a zoom may crop it; anything else lit must be
    wholly on screen."""
    boxes = {r.id: r for r in ANATOMY.regions}
    for step in TOUR.steps:
        for rid in step.region_ids:
            if rid == "array":
                continue
            assert _in_frame(step.camera, boxes[rid]), f"{step.id}: {rid} off camera"


def test_the_confidence_beat_shows_the_copies_it_condemns():
    """The narration says the four ruined copies turn red now, so they must be
    in frame — not just the classifier."""
    step = STEPS["confidence-climbs"]
    state = simulate()[step.trace_cursor]
    boxes = {r.id: r for r in ANATOMY.regions}
    condemned = [f"snap-{i}" for i in range(CLEAN_SNAPSHOTS + 1, TOTAL_SNAPSHOTS + 1)]
    assert len(condemned) == state.snapshots_corrupted
    for rid in condemned:
        assert _in_frame(step.camera, boxes[rid]), rid


def test_no_beat_calls_a_condemned_copy_clean():
    """The verdict condemns every snapshot after CLEAN_SNAPSHOTS. A beat
    before encryption may light only the copies the verdict will vindicate,
    so the tour never presents a later-condemned copy as good."""
    trace = simulate()
    first_encrypt = next(i for i, s in enumerate(trace) if s.phase == "encrypt")
    clean = {f"snap-{i}" for i in range(1, CLEAN_SNAPSHOTS + 1)}
    for step in TOUR.steps:
        if step.trace_cursor < first_encrypt:
            assert set(step.region_ids) & SNAPS <= clean, step.id
