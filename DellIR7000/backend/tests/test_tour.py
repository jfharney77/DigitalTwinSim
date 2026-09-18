"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is the IR7000's."""

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
BAYS = {r.id for r in ANATOMY.regions if r.kind == "coldplate"}


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


def test_the_signature_step_frames_the_whole_heat_path():
    """The heat-balance beat lights the input (power shelf, bays) and both
    exits (the liquid loop and the rear door), and frames all of it."""
    step = STEPS[SIGNATURE_STEP_ID]
    lit = set(step.region_ids)
    assert {"power-shelf", "door", "cdu", "manifold-supply", "manifold-return"} <= lit
    assert BAYS <= lit
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(ANATOMY).values())


def test_the_signature_step_pins_the_first_loaded_step():
    """The narration and the trace say the same thing at the same moment:
    the first step with IT load, where liquid + air == load is first
    non-trivial — and the numbers the script quotes are the trace's."""
    trace = simulate()
    i = STEPS[SIGNATURE_STEP_ID].trace_cursor
    state = trace[i]
    assert state.label == "IT load arrives — heat appears on the cold plates"
    assert state.it_load_watts > 0
    assert all(s.it_load_watts == 0 for s in trace[:i])
    assert state.liquid_watts + state.air_watts == state.it_load_watts
    script = STEPS[SIGNATURE_STEP_ID].script
    for kw in (state.it_load_watts, state.liquid_watts, state.air_watts):
        assert f"{kw // 1000} kW" in script


def test_the_longest_stage_gets_a_beat():
    """Leak/flow verification is the trace's longest stage; the tour stops on
    it, on the cold-plate beat."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert trace[longest].phase == "verify"
    assert STEPS["cold-plates"].trace_cursor == longest


def test_flow_is_shown_before_heat():
    """The tour tells the commissioning order the engine asserts: every beat
    before the signature pins a step with zero IT load."""
    trace = simulate()
    for step in TOUR.steps:
        if step.id == SIGNATURE_STEP_ID:
            break
        assert trace[step.trace_cursor].it_load_watts == 0, step.id


def test_bays_light_together():
    """The four bays always heat in lockstep in the engine; the tour never
    lights a subset of them."""
    for step in TOUR.steps:
        lit = set(step.region_ids) & BAYS
        assert lit in (set(), BAYS), step.id


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
    assert base["tour"]["steps"][0]["id"] == "rack-as-plumbing"
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


def test_every_beat_frames_every_region_it_lights():
    """A lit region the camera cuts off is a beat talking about something the
    viewer cannot see. Every beat, not only the signature, frames all of its
    lit regions in full."""
    boxes = {r.id: r for r in ANATOMY.regions}
    for step in TOUR.steps:
        cam = step.camera
        for rid in step.region_ids:
            r = boxes[rid]
            assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, (step.id, rid)
            assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, (step.id, rid)


def test_every_beat_lights_what_its_trace_step_has_active():
    """The beats pinned on the commissioning steps light at least what the
    trace itself has working there, so the map and the trace agree. The
    signature and the two load beats light the heat path instead, which is
    a superset by construction."""
    trace = simulate()
    for step in TOUR.steps[1:-1]:
        active = set(trace[step.trace_cursor].active_regions)
        lit = set(step.region_ids)
        if step.id in {"cdu-internals", "supply-and-return", "rear-door", "facility-water"}:
            # Close-ups: they light the part being described, which must be
            # something the trace step has working.
            assert lit & active, step.id
        else:
            assert active <= lit, (step.id, active - lit)


def test_quoted_figures_come_from_the_pinned_step():
    """Every kW and L/min figure in a standard script is a number the pinned
    trace step carries (or the 480 kW roadmap, which the anatomy states)."""
    import re

    trace = simulate()
    for step in TOUR.steps:
        s = trace[step.trace_cursor]
        allowed = {
            s.it_load_watts // 1000,
            s.liquid_watts // 1000,
            s.air_watts // 1000,
            480,
        }
        for n in re.findall(r"(\d+) kW", step.script):
            assert int(n) in allowed, (step.id, n)
        for n in re.findall(r"(\d+) litres per minute", step.script):
            assert int(n) == s.flow_lpm, (step.id, n)
