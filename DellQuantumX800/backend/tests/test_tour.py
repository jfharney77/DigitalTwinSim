"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is the
Quantum-X800's."""

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
TRACE = simulate()


def test_tour_invariants():
    assert_tour_invariants(
        TOUR_RESPONSE,
        ANATOMY,
        TRACE,
        SIGNATURE_STEP_ID,
        module=app.tour,
        public_dir=PUBLIC,
    )


def test_tour_is_deterministic():
    assert_deterministic(lambda: build_tour(ANATOMY))


def test_six_to_nine_beats_exterior_first():
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_exterior_beat_shows_the_manager_beside_the_spines():
    """Beat one lights the subnet manager with the spine tier it sits beside."""
    lit = set(TOUR.steps[0].region_ids)
    assert "manager" in lit and {"spine-s1", "spine-s2"} <= lit


def test_the_signature_step_pins_the_credits_trace_step():
    """The narration and the trace say the same thing at the same moment:
    credits are armed before any traffic, and nothing was sent without one."""
    idx = STEPS[SIGNATURE_STEP_ID].trace_cursor
    state = TRACE[idx]
    assert state.phase == "credits"
    assert state.label == "Receivers grant buffer credits — losslessness switches on"
    assert state.fabric_tbps == 0
    assert all(s.fabric_tbps == 0 for s in TRACE[:idx])
    assert all(s.packets_sent_without_credit == 0 for s in TRACE)


def test_the_signature_step_frames_every_link_it_lights():
    step = STEPS[SIGNATURE_STEP_ID]
    lit = set(step.region_ids)
    assert {"spine-s1", "spine-s2", "leaf-l1", "leaf-l4", "endpoint-e1", "endpoint-e4"} <= lit
    assert lit <= set(TRACE[step.trace_cursor].active_regions)
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(ANATOMY).values())


def test_the_longest_stage_gets_a_beat():
    """Central route computation is the trace's longest stage; the tour stops on it."""
    longest = max(range(len(TRACE)), key=lambda i: TRACE[i].cycle_cost)
    assert TRACE[longest].phase == "routes"
    assert longest in {s.trace_cursor for s in TOUR.steps}


def test_the_manager_is_lit_only_while_it_programs_the_fabric():
    """The tour never lights the manager on a beat whose trace step leaves it
    dark — beat one excepted, where the fabric is dark and the manager is
    being introduced."""
    for step in TOUR.steps[1:]:
        if "manager" in step.region_ids:
            assert TRACE[step.trace_cursor].phase in {"discover", "routes"}, step.id
    aside = STEPS["manager-steps-aside"]
    assert "manager" not in aside.region_ids
    assert "manager" not in TRACE[aside.trace_cursor].active_regions


def test_the_sharp_beat_pins_the_crossing_counters():
    sharp = TRACE[STEPS["sharp-counters-cross"].trace_cursor]
    before = TRACE[STEPS["the-all-reduce"].trace_cursor]
    assert sharp.phase == "sharp" and before.phase == "collective"
    assert sharp.fabric_tbps < before.fabric_tbps
    assert sharp.allreduce_gbps > before.allreduce_gbps


def test_the_burst_beat_pins_the_only_stall():
    burst = TRACE[STEPS["incast-senders-wait"].trace_cursor]
    assert burst.phase == "burst"
    assert burst.stall_micros_per_sec > 0 and burst.peak_link_percent >= 95
    assert burst.packets_sent_without_credit == 0


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
    assert base["tour"]["steps"][0]["id"] == "fat-tree-from-above"
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


def _inside(cam, r) -> bool:
    eps = 1e-6
    return (
        cam.x - eps <= r.x
        and r.x + r.w <= cam.x + cam.w + eps
        and cam.y - eps <= r.y
        and r.y + r.h <= cam.y + cam.h + eps
    )


def test_every_beat_frames_every_region_it_lights():
    """A beat that talks about a region must show all of it, not a sliver."""
    boxes = {r.id: r for r in ANATOMY.regions}
    for step in TOUR.steps:
        for rid in step.region_ids:
            assert _inside(step.camera, boxes[rid]), (step.id, rid, step.camera)


def test_the_aside_beat_frames_the_dark_manager():
    """The beat says "look at the small box, it has gone dark", so the
    camera must actually hold the manager in shot."""
    aside = STEPS["manager-steps-aside"]
    manager = next(r for r in ANATOMY.regions if r.id == "manager")
    assert _inside(aside.camera, manager)
    assert aside.camera.w < ANATOMY.width  # a close-up, not the whole map
