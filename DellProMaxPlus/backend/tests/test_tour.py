"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is the Pro Max
Plus's: the weights cross once, the card holds them, the host goes idle."""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

import app.tour
from app.anatomy import ANATOMY
from app.engine import GENERATION_PHASES, HOST_KINDS, simulate
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
    """The storyboard shape: 6-9 beats, beat one shows the whole laptop at
    layer 0, beat two peels it into rooms, the last closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_three_rooms_beat_lights_host_link_and_card():
    """Beat two is the peel: host side, PCIe strip and card side at once."""
    kinds = {KIND[r] for r in TOUR.steps[1].region_ids}
    assert {"host", "memory", "storage", "link", "npu", "aimemory"} <= kinds


def test_the_signature_step_lights_the_path_and_frames_it():
    """The weights' whole route — SSD, host CPU and memory, PCIe strip, AI
    memory — is lit (the script says "through the host"), and the camera
    holds all of it."""
    step = STEPS[SIGNATURE_STEP_ID]
    assert {"ssd", "cpu", "dram", "pcie", "aimem"} <= set(step.region_ids)
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(ANATOMY).values())


def test_the_signature_step_pins_the_only_step_the_link_carries_traffic():
    """The narration and the trace say the same thing at the same moment:
    the pinned step is the load, and it is the one step with link traffic."""
    trace = simulate()
    cursor = STEPS[SIGNATURE_STEP_ID].trace_cursor
    state = trace[cursor]
    assert state.label == "61 GB of weights cross PCIe — the only time they will"
    assert state.phase == "load"
    assert "pcie" in state.active_regions
    busy = [i for i, s in enumerate(trace) if s.link_gbps > 0]
    assert busy == [cursor]


def test_no_later_beat_pins_link_traffic():
    """Every beat after the signature pins a step where the link reads zero —
    the tour never implies a second crossing."""
    trace = simulate()
    sig = STEPS[SIGNATURE_STEP_ID].trace_cursor
    for step in TOUR.steps:
        if step.trace_cursor > sig:
            assert trace[step.trace_cursor].link_gbps == 0, step.id


def test_the_longest_stage_gets_a_beat():
    """Model load is the trace's longest stage; the tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert longest in {s.trace_cursor for s in TOUR.steps}
    assert longest == STEPS[SIGNATURE_STEP_ID].trace_cursor


def test_generating_beats_never_light_the_host():
    """While tokens flow the host is idle in the engine, so the tour never
    lights a host-side region on a generating beat."""
    trace = simulate()
    for step in TOUR.steps:
        if trace[step.trace_cursor].phase in GENERATION_PHASES:
            lit = {KIND[r] for r in step.region_ids}
            assert not (lit & HOST_KINDS), step.id


def test_lit_regions_are_ones_the_trace_step_uses_after_the_peel():
    """From the peel on, every lit region is active at the pinned trace step
    — the tour lights only what the engine says is working."""
    trace = simulate()
    for step in TOUR.steps[2:]:
        active = set(trace[step.trace_cursor].active_regions)
        assert set(step.region_ids) <= active, step.id


def test_the_last_beat_is_the_network_pull():
    last = TOUR.steps[-1]
    state = simulate()[last.trace_cursor]
    assert state.phase == "offline"
    assert last.trace_cursor == len(simulate()) - 1


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
    assert base["tour"]["steps"][0]["id"] == "laptop-exterior"
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


def test_no_step_shows_the_schematic_as_the_real_product():
    """The player puts a step photo behind "Show the real product"; the only
    local image is this project's schematic, so no step may attach it."""
    assert all(s.photo_id is None for s in TOUR.steps)
