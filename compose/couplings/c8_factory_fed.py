"""C8 — The capstone fed by real engines.

PhysicsAIFactory's engine is not changed. This module builds the factory's
inputs from upstream engine runs and calls the same ``simulate``; then it
compares the fed run with the aggregate run and *names* every gap it finds.

| Factory input        | Aggregate mode          | Fed mode                                         |
|----------------------|-------------------------|--------------------------------------------------|
| job.tokens_per_gpu_s | one constant            | × C4 tokens_scale per fabric regime, × C2 cap     |
| data.storage_gbps    | one number              | PhysicsStorage exascale ceiling; shortfalls as    |
|                      |                         | degrade-storage events on the hour they happen    |
| compute.gpu_peak_w   | a tier constant         | PhysicsCompute xe9712 GPU watts per GPU at 100%   |
| PUE                  | a per-cooling constant  | 1 + CDU pump share + facility overhead (estimate) |
"""

from __future__ import annotations

import copy
from typing import Any, Sequence

from .. import constants as K
from ..models import Divergence
from ..reader import get

ID = "c8"

TOLERANCES = {           # instrument -> (tolerance, kind)
    "tokens_per_s": (0.05, "relative"),
    "facility_mw": (0.08, "relative"),
    "gpu_idle_data_pct": (2.0, "absolute"),
    "pue": (0.05, "absolute"),
}


def storage_workload_for(factory_scenario: dict, storage_scenario: dict, per_k_gbs: float) -> dict:
    """Size the storage run's demand from the factory's GPUs: the same demand
    on both sides of the seam, or the two idle gauges cannot be compared."""
    compute = (factory_scenario.get("config", {}) or {}).get("compute", {}) or {}
    job = factory_scenario.get("job", {}) or {}
    gpus = int(compute.get("racks", 8)) * int(compute.get("gpusPerRack", 72))
    demand_gbps = gpus * float(job.get("dataGbpsPerGpu", 1.5))
    scenario = copy.deepcopy(storage_scenario)
    wl = scenario.setdefault("workload", {})
    block_kb = int(wl.get("blockKb", 1024))
    wl["blockKb"] = block_kb
    wl["iopsDemandK"] = max(1, int(round(demand_gbps / (per_k_gbs * block_kb / 8.0))))
    return scenario


def storage_inputs(storage_trace: Sequence[Any], per_k_gbs: float, block_kb: int,
                   racks: int, demand_gbps: float) -> tuple[float, list[dict], list[int]]:
    """``(storage_gbps, degrade/restore events, burst hours)`` for the factory."""
    ceiling = float(get(storage_trace[0], "iops_capacity_k")) * per_k_gbs * block_kb / 8.0 * racks
    ceiling = round(ceiling, 1)
    events: list[dict] = []
    bursts: list[int] = []
    feeds = [1.0 - float(get(s, "gpu_idle_due_to_data_pct", 0.0)) / 100.0 for s in storage_trace]
    # The usual hour sets storage_gbps; only departures from it become events.
    usual = sorted(feeds)[len(feeds) // 2]
    supply = ceiling if usual >= 0.999 else round(usual * demand_gbps, 1)
    last = 100.0
    for state, feed in zip(storage_trace, feeds):
        hour = int(get(state, "t_h"))
        # Fraction of the configured supply that reproduces this hour's feed.
        pct = 100.0 if feed >= usual - 1e-9 else round(100.0 * feed * demand_gbps / supply, 2)
        pct = min(100.0, pct)
        if pct < 100.0:
            bursts.append(hour)
        if abs(pct - last) > 1e-9:
            events.append({"atH": hour, "action": "restore-storage"} if pct >= 100.0 else
                          {"atH": hour, "action": "degrade-storage", "value": pct})
            last = pct
    return supply, events, bursts


def gpu_peak_w(compute_trace: Sequence[Any], gpus: int) -> int:
    tail = compute_trace[int(0.8 * len(compute_trace)):]
    watts = sum(float(get(s, "gpu_power_w", 0.0)) for s in tail) / max(len(tail), 1)
    return int(round(watts / max(gpus, 1)))


def derived_pue(cdu_trace: Sequence[Any]) -> float:
    tail = cdu_trace[int(0.8 * len(cdu_trace)):]
    pump = sum(float(get(s, "pump_power_kw", 0.0)) for s in tail) / max(len(tail), 1)
    it = sum(float(get(s, "it_load_kw", 0.0)) for s in tail) / max(len(tail), 1)
    return round(1.0 + (pump / it if it > 0 else 0.0) + K.value("facility_overhead_pue"), 3)


def steady(trace: Sequence[dict], key: str) -> float:
    train = [s for s in trace if s.get("phase") == "train"]
    tail = train[int(0.8 * len(train)):] or train
    return sum(float(s[key]) for s in tail) / max(len(tail), 1)


INSTRUMENT_KEYS = {
    "tokens_per_s": "tokensPerS", "facility_mw": "facilityMw",
    "gpu_idle_data_pct": "gpuIdleDataPct", "pue": "pue",
}


def compare_modes(aggregate: Sequence[dict], fed: Sequence[dict], facts: dict) -> list[Divergence]:
    """Every instrument outside tolerance, with a cause from the closed list —
    or ``cause=None``, which the agreement test refuses."""
    out: list[Divergence] = []
    for instrument, (tol, kind) in TOLERANCES.items():
        a = steady(aggregate, INSTRUMENT_KEYS[instrument])
        f = steady(fed, INSTRUMENT_KEYS[instrument])
        gap = abs(f - a) / max(abs(a), 1e-9) if kind == "relative" else abs(f - a)
        if gap <= tol:
            continue
        cause, why = None, ""
        cap, fab = facts.get("capScale", 1.0), facts.get("fabricScale", 1.0)
        if instrument == "facility_mw":
            ratio = facts["fedGpuPeakW"] / max(facts["aggregateGpuPeakW"], 1)
            if abs(ratio - 1.0) > 0.02 and (f - a) * (ratio - 1.0) > 0:
                cause = "gpu_tier_vs_detailed"
                why = (f"The detailed XE9712 model draws {facts['fedGpuPeakW']} W per GPU at full "
                       f"load; the aggregate tier is {facts['aggregateGpuPeakW']} W "
                       f"(×{ratio:.2f}). Both are labeled estimates; they are different ones.")
            elif cap < 0.995:
                cause = "cap_vs_shed"
                why = ("The CDU caps the racks on silicon temperature; the aggregate model "
                       "only sheds at the MW budget. Different walls.")
        elif instrument == "tokens_per_s":
            if cap < 0.995 and cap <= fab:
                cause = "cap_vs_shed"
                why = (f"The closed CDU loop holds the racks at {100 * cap:.0f}% on warm water; "
                       "the aggregate model has no temperature wall."
                       + (f" A gray link also stretches the step ×{1 / fab:.2f}." if fab < 0.995 else ""))
            elif fab < 0.995:
                cause = "gray_fabric"
                why = (f"A gray link stretches the step ×{1 / fab:.2f}; the aggregate model's "
                       "fabric is one efficiency number and cannot see it."
                       + (f" Warm water also holds the racks at {100 * cap:.0f}%." if cap < 0.995 else ""))
        elif instrument == "gpu_idle_data_pct":
            if facts.get("burstHours"):
                cause = "checkpoint_burst"
                why = (f"PhysicsStorage's checkpoint bursts starve the GPUs in "
                       f"{len(facts['burstHours'])} hour(s); the aggregate model pays its "
                       "checkpoint as an overhead fraction instead.")
        elif instrument == "pue":
            if cap < 0.995:
                cause = "cap_vs_shed"
                why = ("On warm water the detailed loop spends tokens, not cooling energy; the "
                       "aggregate model spends PUE.")
        out.append(Divergence(instrument=instrument, aggregate=round(a, 4), fed=round(f, 4),
                              tolerance=tol, cause=cause, explanation=why))
    return out
