"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is NativeEdge's."""

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
ENDPOINTS = {r.id for r in ANATOMY.regions if r.kind == "endpoint"}


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
    """The storyboard shape: 6-9 beats, beat one shows the whole estate at
    layer 0, beat two peels the first layer, the last closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert first.trace_cursor == 0
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_pins_the_one_human_action():
    """The narration and the trace say the same thing at the same moment: the
    zero-touch beat pins the first step where operator_actions is 1, and every
    later step of the trace keeps it at exactly 1."""
    trace = simulate()
    cursor = STEPS[SIGNATURE_STEP_ID].trace_cursor
    state = trace[cursor]
    assert state.phase == "power"
    assert state.label == "Power and a network cable — the only human action"
    assert state.operator_actions == 1
    assert all(s.operator_actions == 0 for s in trace[:cursor])
    assert all(s.operator_actions == 1 for s in trace[cursor:])


def test_the_signature_step_frames_the_estate_it_lights():
    """The zero-touch beat lights every endpoint and the WAN they dial out
    over, and its camera frames all of them."""
    step = STEPS[SIGNATURE_STEP_ID]
    assert ENDPOINTS | {"network"} <= set(step.region_ids)
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid


def test_attestation_the_longest_stage_gets_a_beat():
    """Attestation is the trace's unique longest stage; the tour stops on it
    and lights the secure-onboarding gate there."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert trace[longest].phase == "attest"
    beat = next(s for s in TOUR.steps if s.trace_cursor == longest)
    assert "identity" in beat.region_ids


def test_no_beat_claims_trust_before_the_trace_has_it():
    """The Orchestrator and the control plane stay dark until the pinned
    trace step has established trust — the tour never runs ahead of the
    engine's own ordering."""
    trace = simulate()
    control = {"orchestrator", "blueprint", "catalog", "policy", "observability"}
    for step in TOUR.steps:
        if not trace[step.trace_cursor].trust_established:
            assert not control & set(step.region_ids), step.id


def test_endpoints_light_as_a_set():
    """The estate scales in lockstep in the engine, so the tour never lights
    part of it."""
    for step in TOUR.steps:
        lit = ENDPOINTS & set(step.region_ids)
        assert lit in (set(), ENDPOINTS), step.id


def test_the_last_beat_lights_the_whole_platform():
    final = TOUR.steps[-1]
    assert simulate()[final.trace_cursor].phase == "managed"
    assert set(final.region_ids) == {r.id for r in ANATOMY.regions}


def test_layers_run_estate_to_control():
    layers = layer_map(ANATOMY)
    assert all(layers[e] == 0 for e in ENDPOINTS)
    assert layers["network"] == 0
    assert layers["identity"] == layers["orchestrator"] == 1
    assert max(layers.values()) == 2


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
    assert base["tour"]["steps"][0]["id"] == "sealed-crate"
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


# PlatformView pads every camera box by this margin (anatomy units) on each
# side before it becomes the SVG viewBox, so this is what the viewer sees.
VIEW_MARGIN = 2.5


def test_no_lit_region_is_sliced_by_the_frame():
    """A lit block is either wholly across the visible width or wholly off it:
    a close-up that cuts a lit edge site down the middle hides the name of the
    thing the narration is talking about. (Tall blocks may run off the top or
    bottom; their labels sit at the top-left of the block.)"""
    boxes = {r.id: r for r in ANATOMY.regions}
    for step in TOUR.steps:
        left = step.camera.x - VIEW_MARGIN
        right = step.camera.x + step.camera.w + VIEW_MARGIN
        for rid in step.region_ids:
            r = boxes[rid]
            inside = left - 1e-6 <= r.x and r.x + r.w <= right + 1e-6
            outside = r.x + r.w <= left + 1e-6 or r.x >= right - 1e-6
            assert inside or outside, f"{step.id}: {rid} is cut by the frame"


def test_the_attestation_close_up_frames_the_gate():
    """The attestation beat is a close-up, and the secure-onboarding block it
    is about sits wholly inside it."""
    step = STEPS["attestation"]
    cam = step.camera
    assert cam.w < ANATOMY.width / 2
    gate = next(r for r in ANATOMY.regions if r.id == "identity")
    assert cam.x <= gate.x and gate.x + gate.w <= cam.x + cam.w
    assert cam.y <= gate.y and gate.y + gate.h <= cam.y + cam.h
