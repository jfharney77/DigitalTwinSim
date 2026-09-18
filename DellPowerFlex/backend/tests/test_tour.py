"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is PowerFlex's."""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

import app.tour
from app.anatomy import ANATOMY
from app.engine import FAILED_NODE, simulate
from app.leveling import LEVELS, registry
from app.main import app as api
from app.tour import SIGNATURE_STEP_ID, TOUR_RESPONSE, build_tour, layer_map
from twinkit.testing import assert_deterministic, assert_tour_invariants

PUBLIC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "public"
TOUR = TOUR_RESPONSE.tour
STEPS = {s.id: s for s in TOUR.steps}
BOXES = {r.id: r for r in ANATOMY.regions}


def _frames(step, rid: str) -> bool:
    cam, r = step.camera, BOXES[rid]
    return (
        cam.x <= r.x + 1e-6
        and r.x + r.w <= cam.x + cam.w + 1e-6
        and cam.y <= r.y + 1e-6
        and r.y + r.h <= cam.y + cam.h + 1e-6
    )


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
    """The storyboard shape: 6-9 beats, beat one shows the whole pool at
    layer 0, beat two peels the first layer, the last closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_frames_the_empty_controller_band():
    """The camera pans the space where a controller row would sit: the
    fabric, the nodes below it, the gap between them — and the small
    metadata manager, which is the only coordination the pool has."""
    step = STEPS[SIGNATURE_STEP_ID]
    assert {"fabric", "mdm"} <= set(step.region_ids)
    assert {r.id for r in ANATOMY.regions if r.kind == "node"} <= set(step.region_ids)
    for rid in step.region_ids:
        assert _frames(step, rid), rid
    # The framed gap between fabric and nodes holds nothing: no controller.
    fabric = BOXES["fabric"]
    top_of_nodes = min(r.y for r in ANATOMY.regions if r.kind == "node")
    assert not [
        r.id
        for r in ANATOMY.regions
        if r.y >= fabric.y + fabric.h and r.y + r.h <= top_of_nodes
    ]
    assert "controller" not in {r.kind for r in ANATOMY.regions}
    assert step.layer_reveal == max(layer_map(ANATOMY).values())


def test_the_signature_step_pins_the_manager_election():
    """The narration and the trace say the same thing at the same moment:
    the pool elects a manager, not a controller."""
    state = simulate()[STEPS[SIGNATURE_STEP_ID].trace_cursor]
    assert state.label == "Nodes join — a metadata manager is elected"
    assert "mdm" in state.active_regions
    assert state.iops_thousands == 0


def test_the_longest_stage_gets_a_beat():
    """Building the pool is the trace's longest stage; the tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert trace[longest].phase == "pool"
    assert longest == STEPS["chunk-scatter"].trace_cursor


def test_the_beats_pin_the_steps_they_narrate():
    trace = simulate()
    phase = {sid: trace[s.trace_cursor].phase for sid, s in STEPS.items()}
    assert phase["coordinator-dark"] == "io"
    assert phase["a-node-dies"] == "failure"
    assert phase["every-survivor-rebuilds"] == "rebuild"
    rebuild = trace[STEPS["every-survivor-rebuilds"].trace_cursor]
    assert rebuild.rebuild_participants == rebuild.nodes_online == 5


def test_the_coordinator_beat_leaves_the_manager_dark():
    step = STEPS["coordinator-dark"]
    assert "mdm" not in step.region_ids
    assert "mdm" not in simulate()[step.trace_cursor].active_regions


def test_no_node_is_privileged_in_what_the_tour_lights():
    """Mirrors the engine's rule: the lit node set is empty, all six, or
    all five survivors — and the failed node never comes back."""
    allowed = [set(), {f"node-{i}" for i in range(1, 7)},
               {f"node-{i}" for i in range(1, 6)}]
    trace = simulate()
    first_failure = next(i for i, s in enumerate(trace) if s.phase == "failure")
    for step in TOUR.steps:
        lit = {r for r in step.region_ids if r.startswith("node-")}
        assert lit in allowed, (step.id, lit)
        if step.trace_cursor >= first_failure:
            assert FAILED_NODE not in step.region_ids, step.id


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
    assert base["tour"]["steps"][0]["id"] == "six-servers"
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
    """A lit region off-camera is narration about something the reader
    cannot see."""
    for step in TOUR.steps:
        for rid in step.region_ids:
            assert _frames(step, rid), (step.id, rid)


def test_the_numbers_in_the_scripts_are_the_traces_numbers():
    """The scripts quote ~1.8M IOPS steady, ~90% at the failure and above
    70% during the rebuild; those are the pinned trace steps' own values."""
    trace = simulate()
    steady = trace[STEPS["coordinator-dark"].trace_cursor]
    failure = trace[STEPS["a-node-dies"].trace_cursor]
    rebuild = trace[STEPS["every-survivor-rebuilds"].trace_cursor]
    assert steady.iops_thousands == 1800
    assert "1.8 million" in STEPS["coordinator-dark"].script
    assert round(failure.iops_thousands / steady.iops_thousands, 2) == 0.90
    assert "90 percent" in STEPS["a-node-dies"].script
    assert rebuild.iops_thousands / steady.iops_thousands > 0.70
    assert "70 percent" in STEPS["every-survivor-rebuilds"].script
    assert failure.protected_percent < 100
