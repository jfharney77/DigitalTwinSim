"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is the
Alienware twin's: the tour narrates one fixed scenario, and its signature
beat is the stalled PSID handshake."""

from __future__ import annotations

import pathlib
import re

from fastapi.testclient import TestClient

import app.tour
from app.catalog import PROFILES
from app.engine import simulate
from app.leveling import LEVELS, registry
from app.main import app as api
from app.models import Scenario
from app.tour import (
    SIGNATURE_STEP_ID,
    TOUR_ANATOMY,
    TOUR_RESPONSE,
    TOUR_SCENARIO,
    build_tour,
    layer_map,
)
from twinkit.testing import assert_deterministic, assert_tour_invariants

FRONTEND = pathlib.Path(__file__).resolve().parents[2] / "frontend"
PUBLIC = FRONTEND / "public"
TOUR = TOUR_RESPONSE.tour
STEPS = {s.id: s for s in TOUR.steps}


def _trace(scenario: Scenario = TOUR_SCENARIO):
    profile = PROFILES[scenario.profile_id]
    adapter = next(a for a in profile.adapters if a.id == scenario.adapter_id)
    return simulate(profile, adapter, scenario)


TRACE = _trace()


def _state(step_id: str):
    return TRACE[STEPS[step_id].trace_cursor]


def test_tour_invariants():
    assert_tour_invariants(
        TOUR_RESPONSE,
        TOUR_ANATOMY,
        TRACE,
        SIGNATURE_STEP_ID,
        module=app.tour,
        public_dir=PUBLIC,
    )


def test_tour_is_deterministic():
    assert_deterministic(lambda: build_tour(TOUR_ANATOMY))


def test_the_tour_map_is_the_tour_scenarios_machine():
    assert PROFILES[TOUR_SCENARIO.profile_id].anatomy_id == TOUR_ANATOMY.id


def test_six_to_nine_beats_exterior_first():
    """The storyboard shape: 6-9 beats, beat one shows the whole machine at
    layer 0, beat two peels the bottom cover, the last closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (TOUR_ANATOMY.width, TOUR_ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_pins_the_stalled_handshake():
    """The narration and the trace say the same thing at the same moment: the
    PSID read is the stalled, dwelt-on step, and nothing downstream of the
    EC is powered yet."""
    state = _state(SIGNATURE_STEP_ID)
    assert state.label == "PSID handshake"
    assert state.phase == "handshake"
    assert state.stalled and state.cycle_cost > 1
    assert state.cycle_cost == max(s.cycle_cost for s in TRACE)
    assert state.cpu_w == 0 and state.gpu_w == 0 and state.charge_w == 0


def test_the_signature_step_lights_and_frames_the_pin_and_the_ec():
    step = STEPS[SIGNATURE_STEP_ID]
    assert set(_state(SIGNATURE_STEP_ID).active_regions) <= set(step.region_ids)
    assert {"dc-in", "ec"} <= set(step.region_ids)
    boxes = {r.id: r for r in TOUR_ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.layer_reveal == max(layer_map(TOUR_ANATOMY).values())
    assert step.duration_ms == max(s.duration_ms for s in TOUR.steps)


def test_the_unknown_adapter_path_the_signature_beat_narrates():
    """The signature script explains the throttled path; the engine must do
    what it says: no charging, CPU+GPU near 35 W, and the boot still finishes."""
    profile = PROFILES[TOUR_SCENARIO.profile_id]
    unknown = next(a for a in profile.adapters if not a.recognized)
    trace = _trace(TOUR_SCENARIO.model_copy(update={"adapter_id": unknown.id}))
    assert all(s.charge_w == 0 for s in trace)
    assert max(s.cpu_w + s.gpu_w for s in trace) <= 35
    assert trace[-1].phase == "steady"
    budget = next(s for s in trace if s.stage_id == "s4-power-budget")
    assert "Unknown" in budget.description


def test_each_beat_pins_the_step_it_narrates():
    assert _state("closed-laptop").label == "Unplugged"
    assert _state("adapter-brick").label == "Adapter converts AC to 19.5 V"
    budget = _state("power-budget")
    assert budget.label == "EC sets the power budget"
    assert "battery will have to supplement" in budget.description
    charge = _state("charge-ramp")
    assert charge.phase == "charge" and charge.charge_stage == "cc"
    assert charge.charge_w == 90.0
    hybrid = _state("hybrid-power")
    assert hybrid.hybrid and hybrid.battery_w > 0
    assert hybrid.ac_w == 280.0
    assert round(hybrid.system_w) == 294
    steady = _state("steady-state")
    assert steady.phase == "steady" and steady.hybrid


def test_every_max_cost_stage_gets_a_beat():
    """Two stages tie for the longest dwell — the handshake and the CC bulk
    charge — and the tour stops on both."""
    top = max(s.cycle_cost for s in TRACE)
    stalled_kinds = {TRACE[s.trace_cursor].phase for s in TOUR.steps
                     if TRACE[s.trace_cursor].cycle_cost == top}
    assert {"handshake", "charge"} <= stalled_kinds


def test_the_frontend_plays_the_same_scenario():
    """App.tsx switches the scenario controls to TOUR_SCENARIO; the trace
    cursors only mean something if the two agree."""
    source = (FRONTEND / "src" / "App.tsx").read_text()
    block = re.search(r"const TOUR_SCENARIO[^{]*\{([^}]*)\}", source)
    assert block, "App.tsx has no TOUR_SCENARIO"
    body = block.group(1)
    assert f'profileId: "{TOUR_SCENARIO.profile_id}"' in body
    assert f'adapterId: "{TOUR_SCENARIO.adapter_id}"' in body
    assert f"startBatteryPct: {TOUR_SCENARIO.start_battery_pct:g}" in body
    assert f'thermalMode: "{TOUR_SCENARIO.thermal_mode}"' in body
    assert f'workload: "{TOUR_SCENARIO.workload}"' in body


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
    assert base["tour"]["steps"][0]["id"] == "closed-laptop"
    assert set(base["layers"]) == {r.id for r in TOUR_ANATOMY.regions}
    assert base["mapWidth"] == TOUR_ANATOMY.width
    scripts = {}
    for level in LEVELS:
        body = client.get(f"/api/tour?level={level}").json()
        assert [s["id"] for s in body["tour"]["steps"]] == list(STEPS)
        scripts[level] = [s["script"] for s in body["tour"]["steps"]]
        assert all(text.strip() for text in scripts[level])
    assert scripts[3] == [s.script for s in TOUR.steps]
    assert scripts[1] != scripts[5]


def test_every_camera_frames_the_regions_its_beat_lights():
    """A beat that lights a region the camera cuts off is talking about
    something the reader cannot see."""
    boxes = {r.id: r for r in TOUR_ANATOMY.regions}
    for step in TOUR.steps:
        cam = step.camera
        for rid in step.region_ids:
            r = boxes[rid]
            assert cam.x - 1e-6 <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, (step.id, rid)
            assert cam.y - 1e-6 <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, (step.id, rid)


def test_the_two_exits_the_last_beat_names_are_real():
    """The closing beat offers two ways to stop the hybrid drain; the engine
    must agree on both, and on the ~254 W the level-3 script quotes."""
    perf = _trace(TOUR_SCENARIO.model_copy(update={"thermal_mode": "performance"}))
    assert not perf[-1].hybrid and perf[-1].battery_w == 0
    assert round(perf[-1].system_w) == 254
    assert perf[-1].cpu_w + perf[-1].gpu_w < _state("steady-state").cpu_w + _state("steady-state").gpu_w
    big = _trace(TOUR_SCENARIO.model_copy(update={"adapter_id": "barrel-360"}))
    assert not big[-1].hybrid and big[-1].battery_w == 0
    assert big[-1].system_w == _state("steady-state").system_w


def test_level_one_drops_the_acronyms():
    """Level 1 is a change of register, not a paraphrase: none of the
    acronyms the level-3 scripts lean on survive into the novice text
    (the DC-in jack keeps the name printed on the map)."""
    reg = registry()
    jargon = re.compile(r"\b(PSID|EEPROM|CRC|EC|TGP|IC|CC|CV|OS|DC(?!-in)|AC|1-Wire)\b")
    for step in TOUR.steps:
        novice = reg[step.script][1]
        assert not jargon.search(novice), (step.id, jargon.search(novice).group())
