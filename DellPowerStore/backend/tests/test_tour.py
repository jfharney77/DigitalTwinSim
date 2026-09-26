"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is PowerStore's."""

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
    """The storyboard shape: 6-9 beats, beat one shows the whole product at
    layer 0, beat two peels the first layer, the last closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_frames_the_shared_cache_and_both_nodes():
    """The mirror is a pair of NVRAM drives in the shared bay that both nodes
    reach (Dell H18157, and what the node-loss trace depends on). So the beat
    lights the NVRAM and both nodes, and never the interconnect or the DIMMs:
    lighting those would draw a node-to-node mirror the failure trace denies."""
    step = STEPS[SIGNATURE_STEP_ID]
    assert {"nvram", "board-a", "board-b"} <= set(step.region_ids)
    assert not {"interconnect", "dimm-a", "dimm-b"} & set(step.region_ids)
    assert "interconnect" not in simulate()[step.trace_cursor].active_regions
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    # The link layer is peeled one beat later, where the link is the subject.
    assert step.layer_reveal < max(layer_map(ANATOMY).values())
    assert STEPS["nodes-converge"].layer_reveal == max(layer_map(ANATOMY).values())


def test_the_happy_path_and_the_failure_trace_describe_one_write_path():
    """Students predicted 'write-through' on the failure stop because the tour
    once said the second copy crossed the interconnect. No level of the beat,
    or of the trace step it pins, may say that again."""
    reg = registry()
    step = STEPS[SIGNATURE_STEP_ID]
    texts = list(reg[step.script].values())
    texts += list(reg[simulate()[step.trace_cursor].description].values())
    for text in texts:
        low = text.lower()
        assert "shared" in low, text
        for wrong in ("cross-node", "node to node,", "to its partner", "to the other half"):
            assert wrong not in low, (wrong, text)


def test_the_signature_step_pins_the_nvram_trace_step():
    """The narration and the trace say the same thing at the same moment."""
    state = simulate()[STEPS[SIGNATURE_STEP_ID].trace_cursor]
    assert state.label == "NVRAM write cache initializes"
    assert "nvram" in state.active_regions


def test_the_longest_stage_gets_a_beat():
    """PowerStoreOS load is the trace's longest stage; the tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert longest in {s.trace_cursor for s in TOUR.steps}


def test_a_to_b_symmetry_in_what_the_tour_lights():
    """Every lit -a region lights its -b twin — the tour never tells half
    the dual-node story."""
    for step in TOUR.steps:
        ids = set(step.region_ids)
        for rid in ids:
            if rid.endswith("-a"):
                assert rid[:-2] + "-b" in ids, (step.id, rid)
            if rid.endswith("-b"):
                assert rid[:-2] + "-a" in ids, (step.id, rid)


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
