"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is CloudIQ's."""

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
BOXES = {r.id: r for r in ANATOMY.regions}


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
    """The storyboard shape: 6-9 beats, beat one shows the whole platform at
    layer 0, beat two peels the first layer, the last closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_frames_the_analysis_core():
    """The dip beat lights the ML engine and the cybersecurity engine (the
    regions the detect step lights) and frames both, at the deepest layer."""
    step = STEPS[SIGNATURE_STEP_ID]
    assert {"analytics", "security"} <= set(step.region_ids)
    cam = step.camera
    for rid in step.region_ids:
        r = BOXES[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(ANATOMY).values())


def test_the_signature_step_pins_the_first_health_dip():
    """The narration and the trace say the same thing at the same moment: the
    pinned step is the detection, and it is the first step below 100."""
    trace = simulate()
    i = STEPS[SIGNATURE_STEP_ID].trace_cursor
    state = trace[i]
    assert state.label == "A risk crosses threshold"
    assert state.phase == "detect"
    assert state.health_score < 100
    assert all(s.health_score == 100 for s in trace[:i])
    assert set(state.active_regions) <= set(STEPS[SIGNATURE_STEP_ID].region_ids)


def test_scripted_health_numbers_match_the_trace():
    """The scripts quote the dip and the recovery; the trace must agree."""
    trace = simulate()
    dip = trace[STEPS[SIGNATURE_STEP_ID].trace_cursor].health_score
    final = trace[TOUR.steps[-1].trace_cursor].health_score
    assert f"to {dip}" in STEPS[SIGNATURE_STEP_ID].script
    assert str(final) in TOUR.steps[-1].script
    assert dip < final < 100


def test_the_longest_stage_gets_a_beat():
    """ML analyze is the trace's longest stage; the tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert trace[longest].phase == "analyze"
    assert longest in {s.trace_cursor for s in TOUR.steps}


def test_the_tour_follows_telemetry_one_way():
    """The camera travels left to right with the data: the gateway beat
    comes before any insight beat, and each non-bookend beat's lit regions
    never sit left of the previous one's."""
    trace = simulate()
    phases = [trace[s.trace_cursor].phase for s in TOUR.steps]
    assert phases.index("transmit") < phases.index("surface")
    lefts = [
        min(BOXES[r].x for r in s.region_ids) for s in TOUR.steps[1:] if s.region_ids
    ]
    assert all(a <= b for a, b in zip(lefts, lefts[1:])), lefts


def test_every_beat_lights_what_its_trace_step_lights():
    """Where the pinned trace step lights regions, the beat lights them too,
    so the tour never contradicts the pipeline page."""
    trace = simulate()
    for step in TOUR.steps:
        active = set(trace[step.trace_cursor].active_regions)
        assert active <= set(step.region_ids), step.id


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
    assert base["tour"]["steps"][0]["id"] == "the-estate"
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


def test_assertions_are_credited_to_the_tests_not_the_engine():
    """The engine emits a trace; test_engine.py is what asserts one-way flow
    and the partial recovery. A script that says the engine asserts it is
    claiming something the code does not do."""
    reg = registry()
    for step in TOUR.steps:
        for text in reg.get(step.script, {}).values():
            assert "engine asserts" not in text, step.id


def test_every_beat_frames_the_regions_it_lights():
    """Each camera box contains every region the beat lights, so nothing the
    narration points at is cropped (the two full-height columns force the
    whole map on their beats, which this still accepts)."""
    for step in TOUR.steps:
        cam = step.camera
        for rid in step.region_ids:
            r = BOXES[rid]
            assert cam.x - 1e-6 <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, (step.id, rid)
            assert cam.y - 1e-6 <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, (step.id, rid)
