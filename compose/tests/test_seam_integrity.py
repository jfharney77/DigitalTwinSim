"""Adversarial pass over the seams: units, conservation, and time bases.

Each test here was written against a defect that the suite did not catch. They
are the regression fence for four of them:

1. C4's "green and slower" seam passed on a fabric run with no gray tick at
   all — it asserted an adversarial property over an empty set.
2. C1 and C2 widen their event deadband when a series needs more than the
   240-event cap (``resample.to_events`` says the caller must widen its seam
   tolerance by the same amount — C5 does), then checked the seam against the
   unwidened bound. The seam broke, and its note blamed integer quantization.
3. C6's encrypted-TB seam reported ``lhs == rhs == 0`` and ``holds=True`` when
   no backup day was eligible for comparison — while 10 TB was being
   encrypted on the other side of the seam.
4. C6 started the appliance's ransomware one backup day early on the
   resilience clock, and the resulting systematic full-day offset used 95% of
   the tolerance that exists for sub-day rounding.
"""

from __future__ import annotations

import math

from compose import Chain, Link, presets, run
from compose import constants as K
from compose.couplings import c1_compute_heat_to_cdu as c1
from compose.couplings import c2_cdu_caps_to_compute as c2
from compose.couplings import c6_resilience_to_datadomain as c6
from compose.loader import load_engine
from compose.loop import cdu_constants
from compose.reader import dump
from compose.runner import run_engine

FAST_ATTACK = {
    "config": {"product": "powerprotect", "estateTb": 200, "changeGbDay": 500,
               "vault": True, "detection": False, "restoreGbps": 1.0},
    "durationH": 1440,
    "events": [{"atH": 10, "action": "incident", "value": 500},
               {"atH": 30, "action": "contain"},
               {"atH": 40, "action": "attempt-restore"}],
}


# --- 1. an adversarial seam over an empty set ------------------------------------

def test_c4_does_not_claim_the_gray_half_when_no_link_went_gray():
    chain = Chain(
        id="t-integrity-c4-healthy",
        scenarios={"PhysicsFabric": presets.HEALTHY_FABRIC, "PhysicsAIFactory": presets.FACTORY},
        links=(Link("c4", "PhysicsFabric", "PhysicsAIFactory"),),
    )
    trace = run(chain)
    fabric = trace.stages[0].trace
    assert not any(row["goodputPenaltyPct"] > 0 for row in fabric), "no gray tick exists"
    green = next(s for s in trace.seams if "status_all_green" in s.identity)
    assert not green.holds, "an identity about gray ticks cannot hold with no gray tick"
    assert "no gray" in green.note.lower(), green.note


# --- 2. a widened deadband must widen the seam tolerance -------------------------

def _oscillating_liquid_heat(n: int = 700) -> list[dict]:
    """A 1 s liquid-heat series whose integer utilization needs far more than
    the 240-event cap — so the adapter has to widen its deadband."""
    return [{"liquidWatts": 120000.0 + 40000.0 * math.sin(i / 3.0), "t": i} for i in range(n)]


def test_c1_carries_the_deadband_it_actually_used_into_the_seam():
    consts = cdu_constants(load_engine("PhysicsCDU"))
    source = _oscillating_liquid_heat()
    scenario, injected, cfg, _ = c1.adapt(source, {}, cdu=consts, racks=1)
    assert len(injected) <= int(K.value("max_injected_events"))
    assert cfg["eventDeadbandUsed"] > K.value("util_deadband_pct"), \
        "this series must force the deadband to widen, or the test proves nothing"
    cdu = run_engine("PhysicsCDU", scenario)
    tick, energy = c1.check(source, cdu.trace, cdu=consts, racks=1)
    assert tick.holds, f"{tick.abs_error} kW against {tick.tolerance} kW: {tick.note}"
    assert energy.holds, f"{energy.abs_error} kWh against {energy.tolerance} kWh"
    assert "deadband" in tick.note, tick.note


def test_c2_carries_the_deadband_it_actually_used_into_the_seam():
    n = 700
    cdu_trace = [{"secSupplyC": 30.0 + 3.0 * math.sin(i / 2.0), "secFlowLpm": 200.0,
                  "bankStatus": ["ok"] * 6, "capPct": 100.0} for i in range(n)]
    base = {"config": {"product": "xe9712"}, "workload": {"gpuPct": 100, "cpuPct": 40},
            "durationS": n - 1}
    scenario, injected, _ = c2.adapt(cdu_trace, base, [1.0] * n, 200.0, 18)
    supply_events = [e for e in injected if e["action"] == "set-coolant-supply"]
    assert len(supply_events) <= int(K.value("max_injected_events"))
    assert c2.supply_deadband(cdu_trace) > K.value("supply_deadband_c"), \
        "this series must force the deadband to widen, or the test proves nothing"
    compute = run_engine("PhysicsCompute", scenario)
    supply = c2.check(compute.trace, cdu_trace, compute.trace)[0]
    assert supply.holds, f"{supply.abs_error} °C against {supply.tolerance} °C: {supply.note}"
    assert "deadband" in supply.note, supply.note


def test_the_nominal_deadbands_do_not_loosen_anything():
    """The widening is the exception: at the nominal deadband the tolerances
    are exactly what C1's and C2's own tests pin."""
    trace = run(presets.chain("heat-to-cdu"))
    banks = trace.stages[1].scenario["config"]["trayGroups"]
    tick = trace.seams[0]
    assert tick.tolerance <= 0.5 * 0.92 * banks * 40 / 100 + 0.05 + 1e-9
    loop = run(presets.chain("closed-loop"))
    supply = next(s for s in loop.seams if "coolant_supply_c" in s.identity)
    assert supply.tolerance <= K.value("supply_deadband_c") + 0.01 + 0.5 + 1e-9


# --- 3. a seam that compared nothing ---------------------------------------------

def test_c6_refuses_to_pass_when_no_backup_day_was_comparable():
    pass1 = run_engine("PhysicsResilience", FAST_ATTACK)
    res_scn = dump(pass1.scenario)
    dd_scn, dd_injected, _, _ = c6.adapt(res_scn, pass1.trace, {"appliance": "dd9910"})
    dd = run_engine("PhysicsDataDomain", dd_scn)
    seam = c6.check_encrypted(res_scn, pass1.trace, dd.trace, dd_injected, 200.0)
    assert max(s.corrupted_tb for s in pass1.trace) > 5, "real damage happened"
    assert not seam.holds, "nothing was compared, so nothing was shown to agree"
    assert seam.worst_tick is None and "not evidence" in seam.note.lower(), seam.note


# --- 4. the appliance's day and the attack's hour --------------------------------

def test_c6_puts_the_appliance_on_the_attack_clock_not_a_day_ahead():
    trace = run(presets.chain("attack-to-appliance"))
    seam = trace.seams[0]
    one_day_tb = 100 * 24 / 1000.0          # the ATTACK preset spreads 100 GB/h
    assert seam.holds
    assert seam.abs_error <= 0.55 * one_day_tb, (
        "a systematic full-day offset is a bug, not the sub-day rounding the "
        f"tolerance exists for: {seam.abs_error} TB of {one_day_tb} TB"
    )
    dd = next(s for s in trace.stages if s.component == "PhysicsDataDomain")
    start = next(e["atDay"] for e in dd.injected_events if e["action"] == "ransomware-start")
    incident_h = next(e["atH"] for e in presets.ATTACK["events"]
                      if e["action"] in ("incident", "slow-incident"))
    assert start == incident_h // 24 + 1, (
        "the first backup that can contain encrypted data is the one after a "
        "day of attack, not the one taken as it begins"
    )
