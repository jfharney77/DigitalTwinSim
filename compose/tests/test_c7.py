"""C7 — a hostile edge site becomes admin hours and truck rolls."""

from __future__ import annotations

import copy

from compose import Chain, Link, assert_seams, presets, run
from compose import constants as K
from compose.couplings import c7_xr_site_to_fleet as c7


def _fleet(trace):
    return next(s for s in trace.stages if s.id == "PhysicsFleet")


def test_injected_faults_are_all_accounted_for():
    trace = run(presets.chain("hostile-sites"))
    assert_seams(trace)
    faults, hours = trace.seams
    assert faults.lhs == faults.rhs > 0, "exactly"
    assert abs(hours.lhs - hours.rhs) <= 0.01 * hours.rhs + 0.2
    fleet = _fleet(trace)
    outcomes = {o["id"]: o for o in fleet.injected_config["siteOutcomes"]}
    assert outcomes["rooftop-fouled"]["faultsOnHostileDay"] and not outcomes["rooftop-fouled"]["shutdown"]
    assert outcomes["brownout-cell-site"]["shutdown"]
    assert outcomes["clean-closet"]["faultsInjected"] == 0


def test_a_filter_change_upstream_is_cheaper_than_the_truck_rolls_downstream():
    dirty = run(presets.chain("hostile-sites"))
    mix = copy.deepcopy(presets.SITE_MIX)
    mix[0]["scenario"] = presets.XR_CLEANED
    clean = run(Chain(id="t-c7-clean", scenarios={"PhysicsFleet": presets.FLEET},
                      links=(Link("c7", "PhysicsXR", "PhysicsFleet", {"site_mix": mix}),)))
    assert_seams(clean)
    saved = _fleet(dirty).trace[-1]["adminHoursCum"] - _fleet(clean).trace[-1]["adminHoursCum"]
    visits = mix[0]["sites"] * K.value("filter_visit_h")
    assert saved > visits, (saved, visits)


def test_fault_schedule_is_deterministic():
    assert c7.schedule(5, 100) == c7.schedule(5, 100) == [9, 27, 45, 63, 81]
    assert c7.fault_count(60, 180, 12) == 355
    a = _fleet(run(presets.chain("hostile-sites"))).injected_events
    b = _fleet(run(presets.chain("hostile-sites"))).injected_events
    assert a == b and a == sorted(a, key=lambda e: e["atD"])
    assert max(e["atD"] for e in a) < 0.9 * 180
