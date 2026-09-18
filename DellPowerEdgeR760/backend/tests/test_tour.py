"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is the R760's."""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

import app.tour
from app.anatomy import ANATOMY
from app.engine import simulate
from app.leveling import LEVELS, registry
from app.main import app as api
from app.tour import SIGNATURE_STEP_ID, TOUR_RESPONSE, build_tour, layer_map
from twinkit.testing import assert_deterministic, assert_tour_invariants

PUBLIC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "public"
TOUR = TOUR_RESPONSE.tour
STEPS = {s.id: s for s in TOUR.steps}
DIMMS = {"dimm-a1", "dimm-a2", "dimm-b1", "dimm-b2"}


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
    """The storyboard shape: 6-9 beats; beat one shows the whole server at
    layer 0; the drive bay (a front, lid-on part) is beat two; the lid comes
    off by beat three; the last beat closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].id == "drive-bay" and "backplane" in steps[1].region_ids
    assert steps[2].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_frames_every_dimm_and_both_cpus():
    """Memory training happens on both sockets at once: the beat lights all
    four DIMM banks and both CPUs, frames all of them, and has the shroud off."""
    step = STEPS[SIGNATURE_STEP_ID]
    assert DIMMS | {"cpu1", "cpu2"} <= set(step.region_ids)
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(ANATOMY).values())


def test_the_signature_step_pins_the_memory_training_trace_step():
    """The narration and the trace say the same thing at the same moment —
    and that moment is the trace's unique longest stage."""
    trace = simulate()
    i = STEPS[SIGNATURE_STEP_ID].trace_cursor
    state = trace[i]
    assert state.label == "DDR5 memory training"
    assert DIMMS <= set(state.active_regions)
    max_cost = max(s.cycle_cost for s in trace)
    assert state.cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_every_beat_keeps_what_it_lights_in_frame():
    """A beat that narrates a region must show it: at least 80% of each lit
    region's area inside the camera box. (The first draft framed four of the
    six fans it talked about, and half the drive bay.)"""
    boxes = {r.id: r for r in ANATOMY.regions}
    for step in TOUR.steps:
        cam = step.camera
        for rid in step.region_ids:
            r = boxes[rid]
            ix = max(0.0, min(r.x + r.w, cam.x + cam.w) - max(r.x, cam.x))
            iy = max(0.0, min(r.y + r.h, cam.y + cam.h) - max(r.y, cam.y))
            assert ix * iy >= 0.8 * r.w * r.h, (step.id, rid)


def test_the_signature_beat_is_the_longest_beat():
    step = STEPS[SIGNATURE_STEP_ID]
    assert step.duration_ms == max(s.duration_ms for s in TOUR.steps)


def test_each_beat_pins_a_trace_step_that_lights_what_it_narrates():
    """Beats that narrate a subsystem pin a trace step where that subsystem
    is actually at work."""
    trace = simulate()
    expect = {
        "drive-bay": "backplane",
        "fan-wall": "fan-0",
        "perc-and-boss": "perc",
        "idrac-corner": "idrac",
    }
    for sid, rid in expect.items():
        assert rid in trace[STEPS[sid].trace_cursor].active_regions, sid
    assert trace[STEPS["fan-wall"].trace_cursor].fan_percent == 100
    assert trace[STEPS["reassemble"].trace_cursor].phase == "os"


def test_idrac_is_awake_before_the_host_in_every_beat_after_the_first():
    """The drive-bay beat claims the host is still off while the backplane is
    read: the pinned step must be in the management-controller phase."""
    trace = simulate()
    assert trace[STEPS["drive-bay"].trace_cursor].phase == "bmc"
    idrac_boot = next(i for i, s in enumerate(trace) if "idrac" in s.active_regions)
    assert idrac_boot <= STEPS["drive-bay"].trace_cursor


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
    assert base["tour"]["steps"][0]["id"] == "front-bezel"
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
