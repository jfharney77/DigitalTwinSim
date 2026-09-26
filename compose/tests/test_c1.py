"""C1 — XE9712 liquid heat becomes the CDU's load."""

from __future__ import annotations

import copy

from compose import Chain, Link, assert_seams, presets, run
from compose.couplings import c1_compute_heat_to_cdu as c1


def _chain(compute: dict, racks: int = 2, cdu: dict | None = None) -> Chain:
    return Chain(id="t-c1", scenarios={"PhysicsCompute": compute, "PhysicsCDU": cdu or {}},
                 links=(Link("c1", "PhysicsCompute", "PhysicsCDU", {"racks": racks}),))


def test_heat_out_equals_heat_in_across_the_seam():
    starved = copy.deepcopy(presets.XE9712_RAMP)
    starved["events"].append({"atS": 400, "action": "set-data-feed", "value": 40})
    for compute in (presets.XE9712_RAMP, starved):
        for racks in (1, 2):
            trace = run(_chain(compute, racks))
            assert_seams(trace)
            tick, energy = trace.seams[0], trace.seams[1]
            assert tick.worst_tick is not None and tick.abs_error <= tick.tolerance
            assert energy.abs_error / energy.lhs <= 0.005
            # The stated quantization bound: 0.5% × (1 − idle) × banks × 40 kW.
            banks = trace.stages[1].scenario["config"]["trayGroups"]
            assert tick.tolerance <= 0.5 * 0.92 * banks * 40 / 100 + 0.05 + 1e-9


def test_the_per_tick_bound_is_the_documented_0_92_kw_at_five_banks():
    assert abs(0.5 * (1 - 0.08) * 5 * 40 / 100 - 0.92) < 1e-9


def test_air_share_never_crosses_the_seam():
    trace = run(_chain(presets.XE9712_RAMP))
    compute, cdu = trace.stages[0].trace, trace.stages[1].trace
    air_kw = sum(row["airWatts"] for row in compute) * 2 / 1000.0
    liquid_kw = sum(row["liquidWatts"] for row in compute) * 2 / 1000.0
    carried = sum(row["itLoadKw"] for row in cdu)
    assert air_kw > 0
    assert abs(carried - liquid_kw) < 0.005 * liquid_kw, "the CDU carries the liquid share"
    assert carried < liquid_kw + air_kw - 0.5 * air_kw, "and none of the air share"
    # Upstream, nothing is lost: liquid + air == dc, so the air goes to the room.
    for row in compute:
        assert abs(row["liquidWatts"] + row["airWatts"] - row["dcPowerW"]) <= 0.11
    assert trace.seams[2].holds


def test_sub_floor_heat_is_flagged_not_hidden():
    # A near-empty rack sized against six banks: its heat sits below the banks' idle floor.
    tiny = {"config": {"product": "xe9712", "trays": 1}, "workload": {"gpuPct": 0, "cpuPct": 0},
            "durationS": 60}
    compute = run(_chain(tiny, racks=1)).stages[0].trace
    plan = c1.plan(compute, racks=1)
    forced = c1._replan(plan, groups=6)
    assert all(forced["unexpressible"]), "1 tray idles far below 6 banks × 3.2 kW"
    scenario, injected, cfg, notes = c1.adapt(compute, {}, racks=1, groups=6)
    assert notes and "idle floor" in notes[0]
    seams = c1.check(compute, [{"itLoadKw": 19.2, "capPct": 100.0, "trips": 0}] * len(compute),
                     racks=1, groups=6)
    assert not seams[0].holds and "No tick was eligible" in seams[0].note


def test_a_broken_seam_is_reported_not_raised():
    import pytest
    from compose.seam import BrokenSeam
    trace = run(_chain(presets.XE9712_RAMP))
    trace.seams[0].holds = False
    with pytest.raises(BrokenSeam, match="c1"):
        assert_seams(trace)
