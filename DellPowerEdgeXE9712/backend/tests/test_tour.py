"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is the XE9712's."""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

import app.tour
from app.anatomy import ANATOMY
from app.engine import TRAYS, simulate
from app.leveling import LEVELS, registry
from app.main import app as api
from app.tour import SIGNATURE_STEP_ID, TOUR_RESPONSE, build_tour, layer_map
from twinkit.testing import assert_deterministic, assert_tour_invariants

PUBLIC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "public"
TOUR = TOUR_RESPONSE.tour
STEPS = {s.id: s for s in TOUR.steps}
BOXES = {r.id: r for r in ANATOMY.regions}


def _cursor_of(step_id: str):
    return simulate()[STEPS[step_id].trace_cursor]


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
    """The storyboard shape: 6-9 beats, beat one shows the whole rack at
    layer 0, beat two peels the first layer, the last closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_lights_every_gpu_and_the_fabric():
    """The atomic fuse lights all four drawn trays' GPUs and both switch
    blocks, frames every one of them, and sits at the deepest layer."""
    step = STEPS[SIGNATURE_STEP_ID]
    gpu_ids = {r.id for r in ANATOMY.regions if r.kind == "gpu"}
    switch_ids = {r.id for r in ANATOMY.regions if r.kind == "nvswitch"}
    assert gpu_ids | switch_ids <= set(step.region_ids)
    cam = step.camera
    for rid in step.region_ids:
        r = BOXES[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(ANATOMY).values())


def test_the_signature_step_pins_the_fuse():
    """The narration and the trace say the same thing at the same moment:
    the pinned step is the first with a domain, and it holds all 72 GPUs."""
    trace = simulate()
    i = STEPS[SIGNATURE_STEP_ID].trace_cursor
    state = trace[i]
    assert state.phase == "fused"
    assert state.label == "One NVLink domain — 72 GPUs become one accelerator"
    assert state.gpus_in_domain == 72
    assert trace[i - 1].gpus_in_domain == 0, "the fuse must be the 0 -> 72 step"


def test_every_beat_before_the_fuse_has_no_domain():
    """No beat before the signature claims a fused domain: the tour follows
    the atomic fuse, it does not anticipate it."""
    sig = STEPS[SIGNATURE_STEP_ID].trace_cursor
    for step in TOUR.steps:
        state = simulate()[step.trace_cursor]
        assert state.gpus_in_domain == (72 if step.trace_cursor >= sig else 0), step.id


def test_liquid_before_silicon_beat_pins_the_coolant_step():
    """Beat two is the coolant loop, pinned before any tray boots, and it
    lights the loop and nothing with a cold plate."""
    step = TOUR.steps[1]
    state = _cursor_of(step.id)
    assert state.phase == "coolant"
    assert set(step.region_ids) == {"cdu", "manifold"}
    later = [s.trace_cursor for s in TOUR.steps if "gpu-t1" in s.region_ids]
    assert later and min(later) > step.trace_cursor


def test_the_longest_stage_gets_a_beat():
    """NVLink fabric training is the trace's longest stage; the tour stops
    on it and lights the switch trays."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert trace[longest].phase == "fabric"
    beats = [s for s in TOUR.steps if s.trace_cursor == longest]
    assert beats
    assert {"nvswitch-a", "nvswitch-b"} <= set(beats[0].region_ids)


def test_the_switch_beat_shows_trays_either_side():
    """The mid-rack beat frames the switch trays with compute trays above
    and below them in view — that is the copper-reach argument."""
    step = STEPS["switch-trays-mid-rack"]
    cam = step.camera
    sw = BOXES["nvswitch-a"]
    above, below = BOXES["gpu-t2"], BOXES["gpu-t3"]
    assert above.y + above.h <= sw.y and sw.y + sw.h <= below.y
    for r in (sw, above, below):
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h, r.id


def test_trays_light_in_lockstep():
    """Whatever the tour lights on one tray it lights on all four — the
    trays are identical, as the engine's lockstep test insists."""
    for step in TOUR.steps:
        ids = set(step.region_ids)
        for rid in ids:
            base, _, suffix = rid.rpartition("-")
            if suffix in TRAYS:
                for t in TRAYS:
                    assert f"{base}-{t}" in ids, (step.id, rid)


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
    assert base["tour"]["steps"][0]["id"] == "rack-exterior"
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


def test_the_tour_never_lights_what_the_trace_has_dark():
    """A lit region reads as powered. Each beat lights only regions the
    pinned trace step has active, so the tour cannot show the GPUs awake
    at tray boot or the switch trays up before the fabric stage."""
    trace = simulate()
    for step in TOUR.steps:
        active = set(trace[step.trace_cursor].active_regions)
        assert set(step.region_ids) <= active, (
            step.id, sorted(set(step.region_ids) - active)
        )


def test_the_zoomed_beats_frame_what_they_light_or_say_so():
    """Close-ups frame at least one whole block of what they light; the
    fabric beat frames the left switch block whole (its script says the
    right-hand block mirrors it)."""
    for step in TOUR.steps:
        cam = step.camera
        whole = [
            rid for rid in step.region_ids
            if cam.x <= BOXES[rid].x
            and BOXES[rid].x + BOXES[rid].w <= cam.x + cam.w + 1e-6
            and cam.y <= BOXES[rid].y
            and BOXES[rid].y + BOXES[rid].h <= cam.y + cam.h + 1e-6
        ]
        assert not step.region_ids or whole, step.id
    cam, sw = STEPS["fabric-training"].camera, BOXES["nvswitch-a"]
    assert cam.x <= sw.x and sw.x + sw.w <= cam.x + cam.w
    assert cam.y <= sw.y and sw.y + sw.h <= cam.y + cam.h
    assert "mirrors the left" in STEPS["fabric-training"].script
