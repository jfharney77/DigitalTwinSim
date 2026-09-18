"""The narrated tour, checked against this twin's own map and trace. The
shared rules live in ``twinkit.testing.assert_tour_invariants``; what stays
here is the XE9680's."""

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
GPUS = {r.id for r in ANATOMY.regions if r.kind == "gpu"}
NICS = {r.id for r in ANATOMY.regions if r.kind == "network"}


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
    """Beat one shows the whole chassis at layer 0, beat two peels the lid,
    the last closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_frames_all_eight_gpus_and_the_switch():
    step = STEPS[SIGNATURE_STEP_ID]
    assert GPUS | {"nvswitch"} <= set(step.region_ids)
    assert not NICS & set(step.region_ids), "the fabric is not part of the fuse"
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(ANATOMY).values())


def test_the_signature_step_pins_the_fuse():
    """The narration and the trace say the same thing at the same moment:
    the domain snaps to eight here and was zero one step before."""
    trace = simulate()
    i = STEPS[SIGNATURE_STEP_ID].trace_cursor
    state = trace[i]
    assert state.phase == "fuse"
    assert state.label == "NVSwitch fuses eight GPUs into one domain"
    assert state.gpus_in_domain == 8 and trace[i - 1].gpus_in_domain == 0
    assert all(s.gpus_in_domain == 8 for s in trace[i:])


def test_the_nic_beat_follows_the_fuse_and_lights_every_nic():
    trace = simulate()
    nic_step = STEPS["one-nic-per-gpu"]
    assert nic_step.trace_cursor > STEPS[SIGNATURE_STEP_ID].trace_cursor
    assert trace[nic_step.trace_cursor].phase == "fabric"
    assert trace[nic_step.trace_cursor].nics_up == 8
    assert NICS <= set(nic_step.region_ids)


def test_the_host_beat_comes_before_the_gpu_beat():
    trace = simulate()
    assert trace[STEPS["host-boots-first"].trace_cursor].phase == "post"
    assert trace[STEPS["gpu-init"].trace_cursor].phase == "gpuinit"
    assert STEPS["host-boots-first"].trace_cursor < STEPS["gpu-init"].trace_cursor


def test_the_longest_stage_gets_a_beat():
    """GPU init (HBM training x8) is the trace's longest stage; the tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert longest == STEPS["gpu-init"].trace_cursor


def test_gpus_are_lit_as_a_set():
    """The GPUs light in lockstep in the trace, so the tour never lights a
    partial field."""
    for step in TOUR.steps:
        lit = GPUS & set(step.region_ids)
        assert not lit or lit == GPUS, step.id


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
    assert base["tour"]["steps"][0]["id"] == "six-u-from-above"
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


def _overlap(cam, r) -> float:
    w = min(cam.x + cam.w, r.x + r.w) - max(cam.x, r.x)
    h = min(cam.y + cam.h, r.y + r.h) - max(cam.y, r.y)
    return max(w, 0) * max(h, 0)


def test_every_lit_region_is_on_camera():
    """A beat never spotlights something the camera cannot see: at least a
    fifth of every lit region sits inside the frame. (The map is too wide for
    full-height regions to fit a real zoom, so a beat may show the labelled
    top of a lower row rather than the whole of it.)"""
    boxes = {r.id: r for r in ANATOMY.regions}
    for step in TOUR.steps:
        for rid in step.region_ids:
            r = boxes[rid]
            assert _overlap(step.camera, r) >= (r.w * r.h) / 5 - 1e-6, (step.id, rid)


def test_the_host_beat_frames_the_host_alone():
    step = STEPS["host-boots-first"]
    host = next(r for r in ANATOMY.regions if r.id == "host-cpus")
    cam = step.camera
    assert step.region_ids == ["host-cpus"]
    assert cam.x <= host.x and host.x + host.w <= cam.x + cam.w
    assert cam.y <= host.y and host.y + host.h <= cam.y + cam.h
    assert cam.w < ANATOMY.width, "a real zoom, not the whole map"


def test_generation_specific_figures_are_qualified():
    """900 GB/s is the H100/H200 NVLink figure; the XE9680 also ships B200
    boards, so the narration never states it unqualified."""
    for level in (1, 2, 3, 4, 5):
        client = TestClient(api)
        body = client.get(f"/api/tour?level={level}").json()
        for s in body["tour"]["steps"]:
            if "900 GB/s" in s["script"]:
                assert "H100" in s["script"], (level, s["id"])


def test_colossus_is_not_credited_to_this_box_alone():
    """Colossus was reported as Dell *and* Supermicro 8-GPU servers in
    liquid-cooled racks; any beat that names it says so."""
    client = TestClient(api)
    for level in (1, 3, 5):
        body = client.get(f"/api/tour?level={level}").json()
        for s in body["tour"]["steps"]:
            if "Colossus" in s["script"]:
                assert "Supermicro" in s["script"], (level, s["id"])
