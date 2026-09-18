"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is VxRail's."""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

import app.tour
from app.anatomy import ANATOMY
from app.engine import NODES, simulate
from app.leveling import LEVELS, registry
from app.main import app as api
from app.tour import SIGNATURE_STEP_ID, TOUR_RESPONSE, build_tour
from twinkit.testing import assert_deterministic, assert_tour_invariants

PUBLIC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "public"
TOUR = TOUR_RESPONSE.tour
STEPS = {s.id: s for s in TOUR.steps}
LOCKSTEP_PHASES = ("power", "esxi", "discovery")


def _node(rid: str) -> str | None:
    suffix = rid.rsplit("-", 1)[-1]
    return suffix if suffix in NODES else None


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
    """Beat one shows the whole rack at layer 0, beat two opens a node, the
    last closes the cluster back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_pins_the_primary_election():
    """The narration and the trace say the same thing at the same moment:
    the pinned step is the election, and it lights exactly one node."""
    state = simulate()[STEPS[SIGNATURE_STEP_ID].trace_cursor]
    assert state.phase == "primary"
    assert state.label == "Primary-node election — VxRail Manager powers up"
    assert {_node(r) for r in state.active_regions} == {"n1"}


def test_the_signature_step_lights_one_node_and_frames_it():
    """Exactly one node breaks lockstep: the beat lights only node 1's
    regions, and its camera frames all of them."""
    step = STEPS[SIGNATURE_STEP_ID]
    assert step.region_ids
    assert {_node(r) for r in step.region_ids} == {"n1"}
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    # The longest beat: the one idea gets the most time.
    assert step.duration_ms == max(s.duration_ms for s in TOUR.steps)


def test_lockstep_beats_light_every_node():
    """Where the pinned trace step is a lockstep phase, whatever the beat
    lights on one node it lights on all four — the tour never tells a
    lockstep phase as if one node did it alone."""
    trace = simulate()
    checked = 0
    for step in TOUR.steps:
        if trace[step.trace_cursor].phase not in LOCKSTEP_PHASES:
            continue
        checked += 1
        ids = set(step.region_ids)
        for rid in ids:
            if _node(rid):
                base = rid.rsplit("-", 1)[0]
                for n in NODES:
                    assert f"{base}-{n}" in ids, (step.id, rid, n)
    assert checked >= 2


def test_lit_regions_are_doing_work_in_the_pinned_trace_step():
    """Once the trace is moving, a beat lights only regions the engine says
    are active at the step it pins (the first two beats are anatomy looks at
    the dark rack, pinned to step 0)."""
    trace = simulate()
    for step in TOUR.steps:
        if step.trace_cursor == 0:
            continue
        active = set(trace[step.trace_cursor].active_regions)
        assert set(step.region_ids) <= active, step.id


def test_the_longest_stage_gets_a_beat():
    """The VxRail Manager cluster build is the trace's longest stage."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert trace[longest].phase == "cluster"
    assert longest in {s.trace_cursor for s in TOUR.steps}


def test_vsan_beat_lights_every_nodes_nvme():
    trace = simulate()
    vsan = [s for s in TOUR.steps if trace[s.trace_cursor].phase == "vsan"]
    assert len(vsan) == 1
    assert {f"storage-{n}" for n in NODES} <= set(vsan[0].region_ids)


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
    assert base["tour"]["steps"][0]["id"] == "rack-elevation"
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


def test_every_lit_region_is_in_shot():
    """A beat never lights (and narrates) a region its camera crops away:
    every lit region's box lies wholly inside the beat's camera."""
    boxes = {r.id: r for r in ANATOMY.regions}
    eps = 1e-6
    for step in TOUR.steps:
        cam = step.camera
        for rid in step.region_ids:
            r = boxes[rid]
            assert cam.x - eps <= r.x and r.x + r.w <= cam.x + cam.w + eps, (step.id, rid)
            assert cam.y - eps <= r.y and r.y + r.h <= cam.y + cam.h + eps, (step.id, rid)


def test_the_node_interior_beat_lights_one_whole_node():
    """The beat that opens a node lights every region of node 1 and nothing
    of any other node: one complete server, not a sampler."""
    step = STEPS["node-interior"]
    ids = set(step.region_ids)
    node_one = {r.id for r in ANATOMY.regions if _node(r.id) == "n1"}
    assert ids == node_one
