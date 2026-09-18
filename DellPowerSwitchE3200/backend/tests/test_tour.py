"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is the E3200's."""

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
    """The storyboard shape: 6-9 beats, beat one shows the whole switch at
    layer 0, beat two peels the lid, the last closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_peel_shows_the_asic_and_its_manager():
    """Beat two is the storyboard's peel: the ASIC and the CPU, both under
    the lid."""
    peel = TOUR.steps[1]
    assert {"asic", "cpu"} <= set(peel.region_ids)
    layers = layer_map(ANATOMY)
    assert layers["asic"] == layers["cpu"] == peel.layer_reveal


def test_the_signature_step_frames_the_poe_subsystem_and_the_front_ports():
    """PoE is delivered by the PSE and leaves through the access ports; the
    signature beat lights both and frames both."""
    step = STEPS[SIGNATURE_STEP_ID]
    assert {"poe-system", "access-ports"} <= set(step.region_ids)
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(ANATOMY).values())


def test_the_signature_step_pins_the_power_peak():
    """The narration and the trace say the same thing at the same moment:
    the pinned step is the PoE step, and it is the trace's power peak."""
    trace = simulate()
    state = trace[STEPS[SIGNATURE_STEP_ID].trace_cursor]
    assert state.label == "PoE delivered to devices"
    assert "poe-system" in state.active_regions
    assert state.power_watts == max(s.power_watts for s in trace)


def test_the_longest_stage_gets_a_beat():
    """The network-OS boot is the trace's longest stage; the tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert "network os" in trace[longest].label.lower()
    assert longest in {s.trace_cursor for s in TOUR.steps}


def test_beats_pin_the_storyboard_stages():
    """ONIE, the NOS boot, the ASIC tables, PoE and line rate each have the
    beat the storyboard gives them."""
    trace = simulate()
    labels = {s.id: trace[s.trace_cursor].label for s in TOUR.steps}
    assert labels["onie"] == "ONIE bootloader"
    assert labels["nos-choice"] == "Network OS boots (OS10 / SONiC)"
    assert labels["asic-tables"] == "Forwarding tables programmed"
    assert labels["line-rate"] == "Line-rate forwarding"


def test_no_traffic_is_narrated_before_the_ports_come_up():
    """Every beat before the ports phase pins a step with zero data rate."""
    trace = simulate()
    for step in TOUR.steps:
        state = trace[step.trace_cursor]
        if state.phase in ("off", "standby", "poweron", "onie", "nos"):
            assert state.data_rate_gbps == 0, step.id


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
    assert base["tour"]["steps"][0]["id"] == "front-panel"
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


def test_every_camera_frames_what_its_beat_talks_about():
    """No beat narrates a region the camera has cropped: every lit region
    sits wholly inside that beat's frame."""
    boxes = {r.id: r for r in ANATOMY.regions}
    for step in TOUR.steps:
        cam = step.camera
        for rid in step.region_ids:
            r = boxes[rid]
            assert cam.x - 1e-6 <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, (step.id, rid)
            assert cam.y - 1e-6 <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, (step.id, rid)


def test_the_poe_beat_claims_only_what_the_trace_shows():
    """The narrated 'about 250 a moment ago, about 900 now' is the trace's
    own pair of numbers, and the PoE draw really is most of the peak."""
    trace = simulate()
    i = STEPS[SIGNATURE_STEP_ID].trace_cursor
    assert (trace[i - 1].power_watts, trace[i].power_watts) == (250, 900)
    assert trace[i].power_watts - trace[i - 1].power_watts > trace[i].power_watts / 2
