"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is iDRAC's."""

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
    """The storyboard shape: 6-9 beats, beat one shows the whole map at
    layer 0 with nothing powered, beat two peels to the warm corner, the last
    closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert simulate()[first.trace_cursor].power_watts == 0, "beat one is before AC"
    assert steps[1].layer_reveal >= 1
    assert steps[1].region_ids == ["pwr"], "the one warm corner is standby power"
    assert steps[-1].layer_reveal == 0


def test_the_host_stays_off_on_every_beat():
    """The tour narrates test_host_never_powers_on: every pinned trace step is
    BMC-domain draw only, and the host is never lit because it is not on the
    map at all."""
    trace = simulate()
    for step in TOUR.steps:
        assert trace[step.trace_cursor].power_watts <= 20, step.id


def test_the_root_of_trust_precedes_everything_it_protects():
    """The chain-of-trust beat pins the RoT verification step, and comes
    before the beats for the kernel's buses and the Lifecycle Controller."""
    trace = simulate()
    rot = STEPS["root-of-trust"]
    assert trace[rot.trace_cursor].label == "Root of Trust verifies firmware"
    assert "rot" in rot.region_ids and "rot" in trace[rot.trace_cursor].active_regions
    order = [s.id for s in TOUR.steps]
    assert order.index("root-of-trust") < order.index("sideband-buses")
    assert order.index("root-of-trust") < order.index("lifecycle-controller")


def test_the_longest_stage_gets_a_beat():
    """Lifecycle Controller init is the trace's unique longest stage; the
    tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert STEPS["lifecycle-controller"].trace_cursor == longest
    assert trace[longest].label == "Lifecycle Controller initializes"


def test_the_signature_step_pins_the_steady_state_watch():
    """The narration and the trace say the same thing at the same moment:
    ready, watching, host still off."""
    step = STEPS[SIGNATURE_STEP_ID]
    state = simulate()[step.trace_cursor]
    assert state.label == "Out-of-band watch (steady state)"
    assert state.phase == "ready"
    assert state.progress_percent == 100
    assert set(step.region_ids) <= set(state.active_regions)
    # Both sides of the map carry the idea: the buses into the host and the
    # port to the world, joined through the SoC.
    assert {"soc", "monitor", "nic"} <= set(step.region_ids)
    assert any(r.startswith("sb-") for r in step.region_ids)


def test_the_signature_step_frames_everything_it_lights():
    step = STEPS[SIGNATURE_STEP_ID]
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(ANATOMY).values())


def test_every_beat_frames_everything_it_lights():
    """A lit block off-camera is narration pointing at nothing: the camera
    must hold every block a beat lights, on every beat."""
    boxes = {r.id: r for r in ANATOMY.regions}
    eps = 1e-6
    for step in TOUR.steps:
        cam = step.camera
        for rid in step.region_ids:
            r = boxes[rid]
            assert cam.x - eps <= r.x and r.x + r.w <= cam.x + cam.w + eps, (step.id, rid)
            assert cam.y - eps <= r.y and r.y + r.h <= cam.y + cam.h + eps, (step.id, rid)


def test_the_map_is_read_while_nothing_is_ghosted():
    """The beat that teaches how to read the map (buses left, SoC centre,
    world right) must show the whole map with no layer peeled, or the blocks
    it describes are off-camera or ghosts."""
    first = TOUR.steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert "left" in first.script and "right" in first.script


def test_every_lit_block_is_active_in_the_pinned_trace_step():
    """The tour lights only what the engine says is doing work at that
    moment, so the diagram never claims more than the trace."""
    trace = simulate()
    for step in TOUR.steps:
        active = set(trace[step.trace_cursor].active_regions)
        assert set(step.region_ids) <= active, step.id


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
    assert base["tour"]["steps"][0]["id"] == "host-off"
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
