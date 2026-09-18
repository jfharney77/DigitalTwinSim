"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is Fort Zero's."""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

import app.tour
from app.anatomy import ANATOMY
from app.engine import BREACH_PHASES, PILLARS, simulate
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
    """Beat one shows the whole map at layer 0, beat two reveals the centre,
    the last shows the whole map again at layer 0."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    last = steps[-1]
    assert last.layer_reveal == 0
    assert (last.camera.w, last.camera.h) == (ANATOMY.width, ANATOMY.height)


def test_the_opening_beat_is_seven_co_equal_pillars():
    """The first beat lights all seven pillars and nothing that could read
    as a perimeter — there is no such region to light."""
    assert set(TOUR.steps[0].region_ids) == set(PILLARS)
    assert "policy" not in TOUR.steps[0].region_ids


def test_layers_have_no_inside():
    """The only layer above the pillars is the centre: the policy engine.
    No region is layered as an 'inside' behind a boundary."""
    layers = layer_map(ANATOMY)
    assert {rid for rid, n in layers.items() if n > 0} == {"policy"}


def test_the_signature_step_frames_the_intruder_and_the_decision():
    step = STEPS[SIGNATURE_STEP_ID]
    assert {"network", "visibility", "policy"} <= set(step.region_ids)
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.duration_ms == max(s.duration_ms for s in TOUR.steps)


def test_the_signature_step_pins_the_breach_trace_step():
    """The narration and the trace say the same thing at the same moment:
    an attacker inside, registered by the network pillar, reaching nothing."""
    state = simulate()[STEPS[SIGNATURE_STEP_ID].trace_cursor]
    assert state.phase == "breach"
    assert state.label == "An attacker compromises a host inside the network"
    assert state.phase in BREACH_PHASES
    assert "network" in state.active_regions
    assert state.resources_reachable == 0
    assert state.trust_score == 0
    assert state.implicit_trust_grants == 0
    assert set(STEPS[SIGNATURE_STEP_ID].region_ids) == set(state.active_regions)


def test_the_decision_beat_draws_on_all_seven_pillars():
    step = STEPS["all-seven-decide"]
    state = simulate()[step.trace_cursor]
    assert state.phase == "decide"
    assert set(step.region_ids) == set(PILLARS) | {"policy"}


def test_the_lease_beat_pins_a_grant_with_a_ttl():
    state = simulate()[STEPS["trust-is-a-lease"].trace_cursor]
    assert state.phase == "grant"
    assert state.trust_ttl_seconds == 300
    assert state.resources_reachable == 1


def test_the_location_beat_reaches_nothing():
    state = simulate()[STEPS["location-is-evidence"].trace_cursor]
    assert state.phase == "context"
    assert state.trust_score == 72
    assert state.resources_reachable == 0


def test_the_longest_stage_gets_a_beat():
    """Continuous monitoring is the trace's longest stage; the tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert trace[longest].phase == "monitor"
    assert STEPS["checking-never-stops"].trace_cursor == longest
    assert (trace[5].verifications, trace[longest].verifications) == (6, 31)
    assert trace[-1].verifications == 41


def test_lit_regions_match_the_trace_where_the_beat_pins_it():
    """Every beat after the opening lights exactly what its trace step lights,
    so the diagram never shows a pillar the engine did not consult."""
    trace = simulate()
    for step in TOUR.steps[1:]:
        assert set(step.region_ids) == set(trace[step.trace_cursor].active_regions), step.id


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
    assert base["tour"]["steps"][0]["id"] == "seven-pillars"
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


def test_every_camera_frames_every_lit_region():
    """A beat never lights a pillar the camera has left out of the shot."""
    boxes = {r.id: r for r in ANATOMY.regions}
    for step in TOUR.steps:
        cam = step.camera
        for rid in step.region_ids:
            r = boxes[rid]
            assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, (step.id, rid)
            assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, (step.id, rid)
