"""Fidelity review: does each adapter respect what the engines on both sides
actually model, and does a seam that reports "holds" actually have something in it?

Three defects, each proven here before it was fixed:

1. The closed loop's convergence test mixed C1's integer-utilization
   quantization error into the residual, so a loop that was provably stationary
   (the CDU never caps, so the carried cap never moves) still burned all twelve
   iterations and reported ``converged=False``.
2. C2 mapped a tripped CDU bank onto a fixed three compute trays, although C1
   sizes the CDU between one and six banks from the heat peak. On a two-bank
   CDU a tripped bank cools nine trays and the adapter restricted three.
3. A run-integral seam whose every tick had been excluded compared 0 kWh with
   0 kWh and reported ``holds=True``. The per-tick seams already refused that
   ("No tick was eligible for comparison"); the integrals did not.
"""

from __future__ import annotations

from compose.couplings import c1_compute_heat_to_cdu as c1
from compose.couplings import c2_cdu_caps_to_compute as c2
from compose.couplings import c5_wall_watts_to_rackpower as c5
from compose.couplings import c6_resilience_to_datadomain as c6
from compose.loop import fixed_point
from compose.reader import series


# --- 1. the fixed point --------------------------------------------------------

def _uncapped_loop(trays: int, gpu_pct: int):
    scenario = {"config": {"product": "xe9712", "trays": trays},
                "workload": {"gpuPct": gpu_pct, "cpuPct": 20}, "durationS": 200}
    return fixed_point(scenario, {}, racks=1)


def test_the_loop_settles_when_the_cdu_never_caps():
    """A loop whose CDU asks for no cap has nothing left to iterate: the carried
    cap is 1.0 on every tick and the compute run cannot move again. It must be
    reported as converged, not as twelve iterations of failure."""
    for trays, gpu_pct in ((1, 20), (1, 100), (2, 40), (4, 70), (6, 40)):
        loop = _uncapped_loop(trays, gpu_pct)
        cap = series(loop.cdu.trace, "cap_pct")
        assert min(cap) == 100.0, (trays, gpu_pct, "this case must not cap at all")
        assert loop.converged, (trays, gpu_pct, loop.iterations, loop.residuals)
        assert loop.iterations <= 3, (trays, gpu_pct, loop.residuals)


def test_the_residual_measures_the_loop_not_the_adapter():
    """C1's integer-util quantization is a fixed offset between the two engines'
    numbers; iterating cannot reduce it, so it does not belong in the residual.
    A quantization-contaminated residual shows up as a floor no run can clear."""
    loop = _uncapped_loop(1, 20)
    heat = [w / 1000.0 for w in series(loop.compute.trace, "liquid_watts")]
    load = series(loop.cdu.trace, "it_load_kw")
    quantization = abs(sum(heat) - sum(load)) / sum(heat)
    assert quantization > 0.005, "this case really is quantized past the loop tolerance"
    assert loop.residuals[-1] < 0.005, loop.residuals


# --- 2. a tripped bank cools the trays it actually cools -----------------------

def _cdu_trace(present: int, tripped: set[int], n: int = 5) -> list[dict]:
    status = ["absent"] * 6
    for i in range(present):
        status[i] = "tripped" if i in tripped else "online"
    return [{"secSupplyC": 30.0, "secFlowLpm": 100.0, "capPct": 100.0,
             "bankStatus": list(status)}] * n


def _restricted(present: int, tripped: set[int], trays: int = 18) -> list[int]:
    base = {"config": {"product": "xe9712", "trays": trays},
            "workload": {"gpuPct": 50, "cpuPct": 20}}
    trace = _cdu_trace(present, tripped)
    _, injected, _ = c2.adapt(trace, base, [1.0] * len(trace), 100.0, trays=trays)
    return sorted(e["index"] for e in injected if e["action"] == "restrict-tray")


def test_a_tripped_bank_restricts_the_trays_it_actually_cools():
    # Six banks over eighteen trays: three trays each, the case the presets hit.
    assert _restricted(6, {0}) == [0, 1, 2]
    assert _restricted(6, {5}) == [15, 16, 17]
    # Two banks over the same eighteen trays: each bank cools nine.
    assert _restricted(2, {0}) == list(range(9))
    assert _restricted(2, {1}) == list(range(9, 18))
    # One bank cools the whole rack.
    assert _restricted(1, {0}) == list(range(18))


def test_the_banks_partition_the_rack_however_many_there_are():
    for present in (1, 2, 3, 4, 5, 6):
        for trays in (12, 17, 18):
            got = _restricted(present, set(range(present)), trays)
            assert got == list(range(trays)), (present, trays, got)


# --- 3. a seam with nothing in it does not hold --------------------------------

def test_c1s_run_integral_does_not_hold_when_every_tick_was_excluded():
    source = [{"liquidWatts": 1000.0, "airWatts": 0.0}] * 10
    # Capped on every tick, so C1 excludes every tick from both seams.
    target = [{"itLoadKw": 19.2, "capPct": 90.0, "trips": 0}] * 10
    tick, run_integral = c1.check(source, target, racks=1, groups=6)
    assert not tick.holds and "No tick was eligible" in tick.note
    assert not run_integral.holds, "0 kWh == 0 kWh is not evidence"
    assert "no tick" in run_integral.note.lower()


def test_c5s_run_integral_does_not_hold_when_every_tick_was_excluded():
    sources = [("R760", [{"acPowerW": 500.0}] * 10)]
    rack = [{"pduInputW": 0.0, "trippedPhases": ["A"], "rackPowered": True}] * 10
    tick, run_integral = c5.check(sources, rack, 1, 10.0)
    assert not tick.holds
    assert not run_integral.holds, "0 kWh == 0 kWh is not evidence"


def test_c6s_encryption_seam_does_not_hold_when_no_day_was_comparable():
    scenario = {"config": {"estateTb": 200, "changeGbDay": 500},
                "events": [{"atH": 240, "action": "incident", "value": 500}]}
    # Contained in the first hour, so no backup day falls inside the window.
    res_trace = [{"tH": h, "corruptedTb": 0.0, "contained": True} for h in range(72)]
    dd_trace = [{"day": d, "encryptedFractionPct": 0.0} for d in range(5)]
    injected = [{"atDay": 2, "action": "ransomware-start", "value": 6.0}]
    seam = c6.check_encrypted(scenario, res_trace, dd_trace, injected, 200.0)
    assert not seam.holds, "an incident nobody compared is not an agreement"


def test_c6s_encryption_seam_still_reports_a_chain_with_no_incident():
    scenario = {"config": {"estateTb": 200, "changeGbDay": 500}, "events": []}
    seam = c6.check_encrypted(scenario, [], [], [], 200.0)
    assert seam.holds and "no incident" in seam.note
