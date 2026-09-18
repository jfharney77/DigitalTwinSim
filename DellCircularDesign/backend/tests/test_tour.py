"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is the circular
design twin's own: the signature beat pins the step where the mass ledger
opens, and the tour tells the loop, leak included."""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

import app.tour
from app.anatomy import ANATOMY
from app.engine import COHORT_MASS_KG, simulate
from app.leveling import LEVELS, registry
from app.main import app as api
from app.tour import SIGNATURE_STEP_ID, TOUR_RESPONSE, build_tour, layer_map
from twinkit.testing import assert_deterministic, assert_tour_invariants

PUBLIC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "public"
TOUR = TOUR_RESPONSE.tour
STEPS = {s.id: s for s in TOUR.steps}


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
    """The storyboard shape: 6-9 beats, beat one shows the whole loop at
    layer 0, the last closes it back up.

    On a loop the "outside" is the forward line, so it may not be peeled
    away while the tour is still narrating it: a peel ghosts every unlit
    region on a shallower layer, and ghosting packaging and deployment
    during the manufacture beat would hide the very line being described.
    The first peel comes on the first beat that pins a trace step past
    deployment (the service loop), and every beat from there peels."""
    trace = simulate()
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    forward = {"materials", "manufacture", "ship", "deploy"}
    for s in steps[:-1]:
        on_forward_line = trace[s.trace_cursor].phase in forward
        assert (s.layer_reveal == 0) == on_forward_line, (
            f"{s.id}: layer_reveal {s.layer_reveal} on phase "
            f"{trace[s.trace_cursor].phase}"
        )
    last = steps[-1]
    assert last.layer_reveal == 0
    assert (last.camera.w, last.camera.h) == (ANATOMY.width, ANATOMY.height)


def test_the_signature_step_lights_recovery_and_all_three_exits():
    """The disassembly beat lights recovery and every destination the
    ledger counts, the leak included, and frames all of them."""
    step = STEPS[SIGNATURE_STEP_ID]
    assert {"recovery", "refurbish", "reclaim", "loss"} <= set(step.region_ids)
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(ANATOMY).values())


def test_the_signature_step_pins_the_step_where_the_ledger_opens():
    """The narration and the trace say the same thing at the same moment:
    the recover step, the first on which reused + reclaimed + lost == mass,
    and the numbers the script speaks are the ones the trace carries."""
    trace = simulate()
    i = STEPS[SIGNATURE_STEP_ID].trace_cursor
    state = trace[i]
    assert state.label == "Take-back at year seven — the mass accounting opens"
    assert state.phase == "recover"
    assert state.reused_kg + state.reclaimed_kg + state.lost_kg == COHORT_MASS_KG
    assert all(s.reused_kg == s.reclaimed_kg == s.lost_kg == 0 for s in trace[:i])
    script = STEPS[SIGNATURE_STEP_ID].script
    for kg in (state.reused_kg, state.reclaimed_kg, state.lost_kg, state.mass_kg):
        assert f"{kg:,}" in script, kg


def test_the_longest_stage_gets_a_beat():
    """Manufacture is the trace's longest stage; the tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert longest in {s.trace_cursor for s in TOUR.steps}


def test_the_leak_is_narrated_and_lit():
    """A tour that skipped the loss region would be the brochure the twin
    refuses to be: some beat lights it, on a trace step where it is lit."""
    trace = simulate()
    beats = [s for s in TOUR.steps if "loss" in s.region_ids]
    assert beats
    assert any("loss" in trace[s.trace_cursor].active_regions for s in beats)


def test_the_tour_ends_where_it_began():
    """The last beat pins the reborn step and lights the materials pool the
    first beat started on: the loop closes in the tour as in the trace."""
    trace = simulate()
    first, last = TOUR.steps[0], TOUR.steps[-1]
    assert last.trace_cursor == len(trace) - 1
    assert trace[last.trace_cursor].phase == "reborn"
    assert "materials" in first.region_ids and "materials" in last.region_ids


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
    assert base["tour"]["steps"][0]["id"] == "the-product-whole"
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


def test_every_beat_frames_what_it_lights():
    """A lit region the camera cuts off is narration pointing off-screen."""
    boxes = {r.id: r for r in ANATOMY.regions}
    for step in TOUR.steps:
        cam = step.camera
        for rid in step.region_ids:
            r = boxes[rid]
            assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, (step.id, rid)
            assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, (step.id, rid)


def test_the_streams_beat_keeps_both_returns_on_stage():
    """The two returns end at deployment and at the materials pool. Both
    ends must be lit, or the layer peel ghosts them and their edges with
    them, and the beat about two roads home shows neither road."""
    step = STEPS["material-streams"]
    assert {"refurbish", "deployment", "reclaim", "materials"} <= set(step.region_ids)
