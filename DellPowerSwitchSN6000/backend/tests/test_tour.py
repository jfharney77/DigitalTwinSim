"""The narrated tour, checked against this twin's own map and trace. The
shared rules live in ``twinkit.testing.assert_tour_invariants``; what stays
here is the SN6000's: the signature beat must stand on the congestion step,
where the fabric is genuinely stressed and still drops nothing."""

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
KIND = {r.id: r.kind for r in ANATOMY.regions}


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
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_pins_the_congestion_step():
    """The narration and the trace say the same thing at the same moment:
    the busiest link at >=95% and zero packets dropped."""
    state = simulate()[STEPS[SIGNATURE_STEP_ID].trace_cursor]
    assert state.phase == "congestion"
    assert state.label.startswith("Congestion")
    assert state.hot_link is not None
    assert state.peak_link_percent >= 95
    assert state.dropped_packets == 0


def test_the_signature_step_frames_the_whole_path_and_the_reflexes():
    """Lossless is a property of the whole two-hop path plus the congestion
    control acting on it; the beat lights all of it and frames all of it."""
    step = STEPS[SIGNATURE_STEP_ID]
    lit = set(step.region_ids)
    assert "telemetry" in lit
    for kind in ("spine", "leaf", "endpoint"):
        assert {rid for rid, k in KIND.items() if k == kind} <= lit, kind
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in lit:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(ANATOMY).values())
    assert step.duration_ms == max(s.duration_ms for s in TOUR.steps)


def test_the_reroute_follows_the_signature():
    """The storyboard's payoff: the beat after the stress is the reroute,
    and the trace it pins cools the hot link without losing throughput."""
    ids = [s.id for s in TOUR.steps]
    after = TOUR.steps[ids.index(SIGNATURE_STEP_ID) + 1]
    trace = simulate()
    before, now = trace[STEPS[SIGNATURE_STEP_ID].trace_cursor], trace[after.trace_cursor]
    assert now.phase == "reroute"
    assert now.peak_link_percent < before.peak_link_percent
    assert now.fabric_tbps >= before.fabric_tbps


def test_the_longest_stage_gets_a_beat():
    """Link training is the trace's longest stage; the tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert trace[longest].phase == "linktrain"
    assert longest in {s.trace_cursor for s in TOUR.steps}


def test_tiers_light_in_lockstep():
    """The tour never lights half a tier: a beat that lights one spine (or
    leaf, or rack) lights all of them, as the engine does."""
    for step in TOUR.steps:
        lit = set(step.region_ids)
        for kind in ("spine", "leaf", "endpoint"):
            tier = {rid for rid, k in KIND.items() if k == kind}
            assert not (lit & tier) or tier <= lit, (step.id, kind)


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
    assert base["tour"]["steps"][0]["id"] == "mesh-from-above"
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


def test_the_two_rack_close_up_cuts_no_block_in_half():
    """The all-reduce beat frames racks 1 and 2 and says so; leaf 3 and rack 3
    must fall wholly outside the frame, not half inside it. The renderer adds
    a 2.5-unit margin on each side of the camera box."""
    cam = STEPS["all-reduce"].camera
    left, right = cam.x - 2.5, cam.x + cam.w + 2.5
    for r in ANATOMY.regions:
        if r.kind not in ("leaf", "endpoint"):
            continue
        inside = left <= r.x and r.x + r.w <= right
        outside = r.x >= right or r.x + r.w <= left
        assert inside or outside, r.id
    shown = {r.id for r in ANATOMY.regions
             if r.kind == "endpoint" and left <= r.x and r.x + r.w <= right}
    assert shown == {"endpoint-e1", "endpoint-e2"}
