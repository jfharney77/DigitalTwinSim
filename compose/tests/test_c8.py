"""C8 — the capstone fed by real engines: agree, or name the gap."""

from __future__ import annotations

import copy

from compose import Chain, assert_seams, presets, run
from compose.couplings import c8_factory_fed as c8
from compose.loader import load_engine

CAUSES = {"stall_power", "hourly_rounding", "cap_vs_shed", "checkpoint_burst",
          "gpu_tier_vs_detailed", "gray_fabric"}


def _steady(trace, mode: str, instrument: str) -> float:
    rows = [t.values[f"{mode}.{instrument}"] for t in trace.timeline]
    agg = next(s for s in trace.stages if s.id == "PhysicsAIFactory/aggregate").trace
    train = [i for i, row in enumerate(agg) if row["phase"] == "train"]
    window = train[int(0.8 * len(train)):]
    return sum(rows[i] for i in window) / len(window)


def test_fed_and_aggregate_agree_when_nothing_is_wrong():
    trace = run(presets.chain("factory-fed"))
    assert_seams(trace)
    tok_a, tok_f = _steady(trace, "aggregate", "tokens_per_s"), _steady(trace, "fed", "tokens_per_s")
    assert abs(tok_f - tok_a) / tok_a <= 0.05
    assert abs(_steady(trace, "fed", "gpu_idle_data_pct") - _steady(trace, "aggregate", "gpu_idle_data_pct")) <= 2.0
    assert abs(_steady(trace, "fed", "pue") - _steady(trace, "aggregate", "pue")) <= 0.05
    # Facility MW is the one gap on a design day, and it is named and sized: the
    # detailed rack draws more per GPU than the aggregate tier assumes.
    named = {d.instrument: d for d in trace.divergences}
    assert set(named) <= {"facility_mw"}
    if "facility_mw" in named:
        d = named["facility_mw"]
        assert d.cause == "gpu_tier_vs_detailed"
        compute = load_engine("PhysicsCompute")
        ratio = compute.C("tray_gpu_w") / 1200
        assert d.fed > d.aggregate and d.fed / d.aggregate <= ratio * 1.02


def test_where_they_disagree_the_reason_is_named():
    for chain_id in ("factory-fed", "factory-fed-bad-day"):
        trace = run(presets.chain(chain_id))
        for d in trace.divergences:
            assert d.cause in CAUSES, f"{chain_id}: {d.instrument} diverges unexplained"
            assert d.explanation
        assert_seams(trace)
    bad = run(presets.chain("factory-fed-bad-day"))
    causes = {d.instrument: d.cause for d in bad.divergences}
    assert causes.get("tokens_per_s") in {"gray_fabric", "cap_vs_shed"}
    tokens = next(d for d in bad.divergences if d.instrument == "tokens_per_s")
    assert tokens.fed < tokens.aggregate


def test_an_unexplained_gap_is_not_waved_through():
    rows = [{"phase": "train", "tokensPerS": 100.0, "facilityMw": 1.0, "gpuIdleDataPct": 0.0, "pue": 1.15}] * 10
    off = [{**r, "gpuIdleDataPct": 30.0} for r in rows]
    facts = {"fedGpuPeakW": 1200, "aggregateGpuPeakW": 1200, "capScale": 1.0,
             "fabricScale": 1.0, "burstHours": []}
    gaps = c8.compare_modes(rows, off, facts)
    assert [g.instrument for g in gaps] == ["gpu_idle_data_pct"] and gaps[0].cause is None


def test_starvation_is_the_same_story_in_both_modes():
    # Halve what storage can deliver below what the GPUs ask for, in both modes.
    base = presets.chain("factory-fed")
    scenarios = copy.deepcopy(base.scenarios)
    storage = scenarios["PhysicsStorage"]
    storage["config"].update({"units": 4, "lightningUnits": 2, "fileUnits": 1,
                              "objectUnits": 1, "blockUnits": 0})
    sh = load_engine("PhysicsStorage")
    probe = sh.simulate(sh.Scenario.model_validate(storage))[0][0]
    nameplate = probe.iops_capacity_k * sh.C("gbps_per_iopsk_8k") * 1024 / 8
    demand = 8 * 72 * 1.5
    assert nameplate < demand, "the shrunken pool must actually starve the factory"
    scenarios["PhysicsAIFactory"] = {"durationH": 720,
                                     "config": {"data": {"storageGbps": round(nameplate, 1)}}}
    trace = run(Chain(id="t-c8-starved", scenarios=scenarios, links=base.links, closed=True))
    shortfall = 100.0 * (1.0 - nameplate / demand)
    idle_a = _steady(trace, "aggregate", "gpu_idle_data_pct")
    idle_f = _steady(trace, "fed", "gpu_idle_data_pct")
    assert abs(idle_a - shortfall) <= 2.0
    for d in trace.divergences:
        assert d.cause in CAUSES, d
    healthy = run(base)
    for mode, idle in (("aggregate", idle_a), ("fed", idle_f)):
        fell = _steady(trace, mode, "tokens_per_s") / _steady(healthy, mode, "tokens_per_s")
        assert abs(fell - (1.0 - idle / 100.0)) <= 0.03, (mode, fell, idle)
    assert idle_f > 10, "the fed mode starves too"
