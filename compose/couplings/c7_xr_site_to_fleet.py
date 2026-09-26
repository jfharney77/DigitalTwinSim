"""C7 — A hostile edge site becomes admin hours and truck rolls.

One PhysicsXR run is "a hostile day at this class of site". A site class whose
day ends in a shutdown — or spends most of it throttled — raises a service
fault each time that day comes round. The faults are scheduled into
PhysicsFleet (NativeEdge personality) deterministically, MTBF-division style:
no dice, evenly spread.
"""

from __future__ import annotations

import copy
from typing import Any, Sequence

from .. import constants as K
from ..reader import get
from ..seam import compare
from ..models import SeamResult

ID = "c7"
THROTTLE_FAULT_FRACTION = 0.5   # a day mostly spent throttled raises a service call
SCHEDULE_SPAN = 0.9             # faults land in the first 90% so the backlog can drain


def site_outcome(xr_summary: Any, duration_s: int, throttle_fault_fraction: float) -> dict:
    shutdown = bool(get(xr_summary, "shutdown", False))
    throttled = int(get(xr_summary, "throttle_seconds", 0))
    share = throttled / max(duration_s, 1)
    faults = shutdown or share >= throttle_fault_fraction
    return {
        "shutdown": shutdown,
        "shutdownReason": get(xr_summary, "shutdown_reason", "") or "",
        "throttleSeconds": throttled,
        "throttledShare": round(share, 3),
        "faultsOnHostileDay": bool(faults),
        "degradedOnly": (not faults) and throttled > 0,
    }


def fault_count(sites: int, duration_d: int, days_per_year: float) -> int:
    return int(round(sites * duration_d / 365.0 * days_per_year))


def schedule(n: int, duration_d: int) -> list[int]:
    """``n`` fault days, evenly spread, fixed by arithmetic."""
    return [int((i + 0.5) * SCHEDULE_SPAN * duration_d / n) for i in range(n)]


def adapt(
    outcomes: Sequence[dict],
    base_scenario: dict | None = None,
    params: dict | None = None,
) -> tuple[dict, list[dict], dict, list[str]]:
    """Per-site-class outcomes (each with ``sites``) -> PhysicsFleet scenario."""
    params = params or {}
    rate = float(params.get("heatwave_days_per_year", K.value("heatwave_days_per_year")))
    scenario = copy.deepcopy(base_scenario or {})
    cfg = scenario.setdefault("config", {})
    cfg["product"] = "nativeedge"
    total_sites = sum(int(o["sites"]) for o in outcomes)
    cfg["sites"] = max(1, min(1000, total_sites))
    duration = int(scenario.get("durationD", 180))
    scenario["durationD"] = duration
    n = 0
    notes: list[str] = []
    for o in outcomes:
        o["faultsInjected"] = fault_count(o["sites"], duration, rate) if o["faultsOnHostileDay"] else 0
        n += o["faultsInjected"]
        if o["degradedOnly"]:
            notes.append(f"{o['id']}: throttled {o['throttleSeconds']} s but stayed up — "
                         "degraded, no fault injected.")
    injected = [{"atD": d, "action": "node-fault"} for d in schedule(n, duration)] if n else []
    kept = list(scenario.get("events", []) or [])
    scenario["events"] = sorted(kept + injected, key=lambda e: e["atD"])
    return scenario, injected, {"sites": cfg["sites"], "faultsInjected": n}, notes


def per_fault_hours(fleet_scenario: dict, fleet_constants: dict) -> float:
    cfg = fleet_scenario.get("config", {}) or {}
    automated = cfg.get("opsMode", "automated") == "automated"
    hours = fleet_constants["remediate_auto_h"] if automated else fleet_constants["remediate_manual_h"]
    if cfg.get("product") == "nativeedge" and not automated:
        hours += fleet_constants["truck_roll_h"]
    return hours


def check(
    baseline_trace: Sequence[Any],
    coupled_trace: Sequence[Any],
    n_injected: int,
    hours_per_fault: float,
) -> list[SeamResult]:
    d_faults = int(get(coupled_trace[-1], "faults_cum")) - int(get(baseline_trace[-1], "faults_cum"))
    faults = compare(
        ID, "Fleet.faults_cum(coupled) − Fleet.faults_cum(baseline) == faults injected",
        float(d_faults), float(n_injected), "faults", 0.0,
        note="exact: every fault the hostile sites cost is one the adapter scheduled",
        lhs_key="PhysicsFleet.extra_faults", rhs_key="PhysicsXR.faults_injected",
    )
    d_hours = float(get(coupled_trace[-1], "admin_hours_cum")) - \
        float(get(baseline_trace[-1], "admin_hours_cum"))
    want = n_injected * hours_per_fault
    hours = compare(
        ID, "Δ admin_hours_cum == faults injected × per-fault hours",
        d_hours, want, "admin-hours", 0.01 * max(want, 1e-9) + 0.2,
        note="1% + output rounding; per-fault hours read from PhysicsFleet's constants "
             "(truck roll included when ops are manual)",
        lhs_key="PhysicsFleet.extra_admin_hours", rhs_key="PhysicsXR.expected_admin_hours",
    )
    return [faults, hours]
