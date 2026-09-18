"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is PowerMax's."""

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


def test_the_signature_step_frames_the_vault_the_sps_and_the_cache():
    """Vault-to-flash needs all three on stage: the volatile DRAM cache, the
    SPS that funds the flush, and the flash it lands in. Both directors' copies
    are lit, and the camera closes in on director A's: the two directors stack
    top and bottom, so a box holding both copies is the whole map — no zoom
    at all on the tour's most important beat."""
    step = STEPS[SIGNATURE_STEP_ID]
    need = {"vault-a", "vault-b", "sps-a", "sps-b", "cache-a", "cache-b"}
    assert need <= set(step.region_ids)
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in ("vault-a", "sps-a", "cache-a"):
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert cam.w * cam.h <= 0.4 * ANATOMY.width * ANATOMY.height, (
        "the signature camera must actually zoom"
    )


def test_every_zoom_frames_what_the_trace_lights():
    """A beat that zooms must keep the trace step's lit director-A regions in
    frame (or the camera is looking away from what the trace is doing).
    Whole-map beats trivially pass."""
    trace = simulate()
    boxes = {r.id: r for r in ANATOMY.regions}
    for step in TOUR.steps:
        cam = step.camera
        lit = [
            rid for rid in trace[step.trace_cursor].active_regions
            if rid.endswith("-a") and rid in step.region_ids
        ]
        for rid in lit:
            r = boxes[rid]
            assert cam.x <= r.x + 1e-6 and r.x + r.w <= cam.x + cam.w + 1e-6, (step.id, rid)
            assert cam.y <= r.y + 1e-6 and r.y + r.h <= cam.y + cam.h + 1e-6, (step.id, rid)


def test_the_signature_step_pins_the_vault_phase():
    """The narration and the trace say the same thing at the same moment:
    the vault is validated before PowerMaxOS boots."""
    trace = simulate()
    i = STEPS[SIGNATURE_STEP_ID].trace_cursor
    state = trace[i]
    assert state.phase == "vault"
    assert state.label == "Validate the vault"
    assert {"vault-a", "vault-b"} <= set(state.active_regions)
    first_boot = next(j for j, s in enumerate(trace) if s.phase == "boot")
    assert i < first_boot


def test_the_sps_beat_pins_the_sps_self_test():
    """The SPS is introduced at the step where the trace tests it."""
    state = simulate()[STEPS["global-memory"].trace_cursor]
    assert state.label == "Standby power supply self-test"
    assert {"sps-a", "sps-b"} <= set(state.active_regions)


def test_the_fabric_beat_precedes_the_drives_beat():
    """Drives hang off the fabric: the tour, like the trace, brings the
    fabric up before it finds the DME."""
    trace = simulate()
    fabric = trace[STEPS["dynamic-fabric"].trace_cursor]
    drives = trace[STEPS["drives-on-the-fabric"].trace_cursor]
    assert fabric.phase == "fabric"
    assert drives.phase == "drives"
    assert "dme" in drives.active_regions
    assert "dme" in STEPS["drives-on-the-fabric"].region_ids
    assert STEPS["dynamic-fabric"].layer_reveal == max(layer_map(ANATOMY).values())


def test_the_longest_stage_gets_a_beat():
    """PowerMaxOS boot is the trace's longest stage; the tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert longest in {s.trace_cursor for s in TOUR.steps}


def test_a_to_b_symmetry_in_what_the_tour_lights():
    """Every lit -a region lights its -b twin — the tour never tells half
    the dual-director story."""
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
    assert base["tour"]["steps"][0]["id"] == "rack-elevation"
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
