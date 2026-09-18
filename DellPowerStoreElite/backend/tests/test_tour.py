"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is the Elite's."""

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


def _step_for(label: str) -> int:
    return next(i for i, s in enumerate(simulate()) if s.label == label)


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
    """The storyboard shape: 6-9 beats, beat one shows both appliances at
    layer 0, beat two peels the first layer, the last closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0
    assert (steps[-1].camera.w, steps[-1].camera.h) == (ANATOMY.width, ANATOMY.height)


def test_the_signature_step_pins_the_join():
    """The narration and the trace say the same thing at the same moment:
    the one join step, two generations, downtime still zero."""
    step = STEPS[SIGNATURE_STEP_ID]
    trace = simulate()
    state = trace[step.trace_cursor]
    assert state.label == "The Elite joins the existing cluster"
    assert state.phase == "join"
    assert state.generations_in_cluster == 2
    assert trace[step.trace_cursor - 1].generations_in_cluster == 1
    assert state.downtime_seconds == 0


def test_the_signature_step_lights_both_generations_and_frames_them():
    """The join is about two generations at once: the prior array still
    serving and the Elite arriving — lit together, all inside the frame."""
    step = STEPS[SIGNATURE_STEP_ID]
    ids = set(step.region_ids)
    assert {"prior-bay", "prior-io-a", "prior-io-b"} <= ids
    assert {"elite-bay", "elite-mgmt-a", "elite-mgmt-b"} <= ids
    active = set(simulate()[step.trace_cursor].active_regions)
    assert ids <= active, "the beat lights something the trace step does not"
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.duration_ms == max(s.duration_ms for s in TOUR.steps)


def test_the_beats_pin_the_steps_they_narrate():
    """Each storyboard beat stops on the trace step making the same claim."""
    assert STEPS["elite-wakes"].trace_cursor == _step_for("Elite nodes boot PowerStoreOS")
    assert STEPS["rdma-mesh"].trace_cursor == _step_for(
        "200 Gb RDMA mesh links the generations"
    )
    assert STEPS["cutover"].trace_cursor == _step_for(
        "Cutover — the Elite serves, performance triples"
    )
    assert STEPS["second-job"].trace_cursor == _step_for(
        "The prior generation takes a second job"
    )
    assert STEPS["mixed-generation-end"].trace_cursor == len(simulate()) - 1


def test_the_mesh_is_not_lit_before_the_mesh_beat():
    """The tour never shows the mesh carrying anything before the engine
    brings it up."""
    order = [s.id for s in TOUR.steps]
    first = order.index("rdma-mesh")
    for step in TOUR.steps[:first]:
        assert "cluster-mesh" not in step.region_ids, step.id
    assert "cluster-mesh" in STEPS["live-rebalance"].region_ids


def test_the_longest_stage_gets_a_beat():
    """The live rebalance is the trace's unique longest stage; the tour
    stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert trace[longest].phase == "rebalance"
    assert STEPS["live-rebalance"].trace_cursor == longest


def test_every_pinned_step_has_zero_downtime():
    trace = simulate()
    for step in TOUR.steps:
        assert trace[step.trace_cursor].downtime_seconds == 0, step.id


def test_the_last_beat_still_lights_the_prior_generation():
    """Mixed-generation is the end state: the closing beat shows both."""
    ids = STEPS["mixed-generation-end"].region_ids
    assert any(r.startswith("prior-") for r in ids)
    assert any(r.startswith("elite-") for r in ids)


def test_a_to_b_symmetry_in_what_the_tour_lights():
    """Every lit -a region lights its -b twin — the dual-node habit
    inherited from the PowerStore twin."""
    for step in TOUR.steps:
        ids = set(step.region_ids)
        for rid in ids:
            if rid.endswith("-a"):
                assert rid[:-2] + "-b" in ids, (step.id, rid)
            if rid.endswith("-b"):
                assert rid[:-2] + "-a" in ids, (step.id, rid)


def test_the_mesh_is_the_deepest_layer():
    layers = layer_map(ANATOMY)
    assert layers["cluster-mesh"] == max(layers.values())


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
    assert base["tour"]["steps"][0]["id"] == "two-generations"
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
    """A lit region the camera crops is a claim the viewer cannot see. The
    shared invariants only check the signature beat; this checks them all."""
    boxes = {r.id: r for r in ANATOMY.regions}
    for step in TOUR.steps:
        cam = step.camera
        for rid in step.region_ids:
            r = boxes[rid]
            assert cam.x - 1e-6 <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, (step.id, rid)
            assert cam.y - 1e-6 <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, (step.id, rid)


def test_every_beat_lights_only_what_its_trace_step_lights():
    """The tour may light a subset of the pinned step's active regions,
    never something the engine has dark at that moment."""
    trace = simulate()
    for step in TOUR.steps:
        active = set(trace[step.trace_cursor].active_regions)
        assert set(step.region_ids) <= active, (step.id, set(step.region_ids) - active)


def test_the_narrated_numbers_match_the_trace():
    """The figures the standard scripts quote are the pinned steps' own."""
    trace = simulate()
    base = trace[0].iops_thousands
    assert "250K" in STEPS["two-generations"].script and base == 250
    rebalance = trace[STEPS["live-rebalance"].trace_cursor]
    assert f"{rebalance.iops_thousands}K" in STEPS["live-rebalance"].script
    cut = trace[STEPS["cutover"].trace_cursor]
    assert f"{cut.iops_thousands}K" in STEPS["cutover"].script
    assert round(cut.iops_thousands / base) == 3
    before = trace[STEPS[SIGNATURE_STEP_ID].trace_cursor - 1]
    after = trace[STEPS[SIGNATURE_STEP_ID].trace_cursor]
    sig = STEPS[SIGNATURE_STEP_ID].script
    assert f"{before.effective_tb / 1000:.1f} PB" in sig
    assert f"{after.effective_tb // 1000} PB" in sig
    assert max(s.iops_thousands for s in trace[: STEPS["cutover"].trace_cursor]) == base
