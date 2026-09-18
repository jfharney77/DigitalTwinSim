"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is PowerScale's."""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

import app.tour
from app.anatomy import ANATOMY
from app.engine import ALL_NODES, INITIAL_NODES, simulate
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
    """The storyboard shape: 6-9 beats, beat one shows the whole cluster at
    layer 0, beat two peels the first layer, the last closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_lays_one_file_system_across_every_node():
    """The onefs-stripe beat lights the namespace with every node the trace
    has online and their drives, frames all of it, and pins the stripe step."""
    step = STEPS[SIGNATURE_STEP_ID]
    lit = set(step.region_ids)
    assert "namespace" in lit
    assert set(INITIAL_NODES) <= lit
    cam = step.camera
    for rid in step.region_ids:
        r = BOXES[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(ANATOMY).values())


def test_the_signature_step_pins_the_stripe_trace_step():
    """The narration and the trace say the same thing at the same moment."""
    state = simulate()[STEPS[SIGNATURE_STEP_ID].trace_cursor]
    assert state.phase == "stripe"
    assert state.label == "One file system striped across every node"
    assert "namespace" in state.active_regions


def test_the_namespace_beat_shows_the_only_shape_spanning_every_node():
    step = STEPS["namespace-band"]
    assert step.region_ids == ["namespace"]
    ns = BOXES["namespace"]
    for node in ALL_NODES:
        n = BOXES[node]
        assert ns.x <= n.x and n.x + n.w <= ns.x + ns.w


def test_the_add_node_beat_pins_growth_without_migration():
    """Capacity jumps, namespaces stays 1, migrations stay 0 — at the beat."""
    trace = simulate()
    i = STEPS["add-a-node"].trace_cursor
    state = trace[i]
    assert state.phase == "addnode"
    assert state.capacity_tb > trace[i - 1].capacity_tb
    assert state.namespaces == 1
    assert state.migrations_required == 0


def test_the_longest_stage_gets_a_beat():
    """The live rebalance is the trace's longest stage; the tour stops on it,
    with every protocol still lit (service continues)."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    beats = [s for s in TOUR.steps if s.trace_cursor == longest]
    assert beats
    assert trace[longest].rebalancing
    assert {"proto-nfs", "proto-smb", "proto-s3", "proto-hdfs"} <= set(beats[0].region_ids)


def test_lit_nodes_match_the_trace_and_are_never_partitioned():
    """Whenever a beat lights nodes, it lights exactly the nodes the pinned
    trace step has online — never a strict subset (striping spans the
    cluster), never a node that has not joined."""
    trace = simulate()
    for step in TOUR.steps:
        lit = {r for r in step.region_ids if r.startswith("node-")}
        if not lit:
            continue
        assert lit in (set(INITIAL_NODES), set(ALL_NODES)), step.id
        online = {
            r for r in trace[step.trace_cursor].active_regions
            if r.startswith("node-")
        }
        assert lit == online, step.id


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
    assert base["tour"]["steps"][0]["id"] == "cluster-exterior"
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
    """A lit region the camera cuts off is narration pointing at nothing:
    every beat's camera must contain every region it lights."""
    for step in TOUR.steps:
        cam = step.camera
        for rid in step.region_ids:
            r = BOXES[rid]
            assert cam.x - 1e-6 <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, (step.id, rid)
            assert cam.y - 1e-6 <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, (step.id, rid)


def test_scripts_carry_no_internal_labels():
    """Narration is read by people: no 'Signature:' style scaffolding and no
    step numbering, at any level."""
    import re

    reg = registry()
    for step in TOUR.steps:
        for text in reg[step.script].values():
            assert "Signature" not in text, step.id
            assert not re.match(r"\s*(step\s*)?\d+[.:)]", text, re.I), step.id
