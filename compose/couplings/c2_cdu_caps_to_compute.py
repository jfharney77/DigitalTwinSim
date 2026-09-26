"""C2 — CDU caps and supply temperature come back as compute throttling.

With C1 this closes a loop: XE9712 heat loads the CDU, and what the CDU does
about it (supply temperature, IRC power cap, pump flow, tripped banks) comes
back as events in the compute scenario.

PhysicsCompute has no power-cap event, so the cap is applied as demanded
``gpu_pct × cap``. That is the honest approximation: tokens fall with the cap,
which is the point. The cap is *carried*: each iteration multiplies the carried
series by the cap the CDU still asked for, so at the fixed point the CDU no
longer needs to cap (its cap reads 100%) and the C1 identity holds again.
"""

from __future__ import annotations

import copy
from typing import Any, Sequence

from .. import constants as K
from ..reader import get, series
from ..resample import integral, to_events
from ..seam import compare, per_tick
from ..models import SeamResult

ID = "c2"
SUPPLY_MIN_C, SUPPLY_MAX_C = 17.0, 45.0   # PhysicsCompute SystemConfig bounds


def clamp_supply(c: float) -> float:
    return min(SUPPLY_MAX_C, max(SUPPLY_MIN_C, c))


def tray_span(bank: int, bank_status: Sequence[str], trays: int) -> range:
    """The trays one CDU bank cools.

    C1 sizes the CDU between one and six banks from the heat peak, so the
    banks-to-trays ratio is not a constant: the present banks partition the rack
    between them. A bank of a two-bank CDU cools half the trays, and a tripped
    one takes half the rack's cooling with it.
    """
    present = [i for i, s in enumerate(bank_status) if s != "absent"]
    if bank not in present:
        return range(0)
    n, rank = len(present), present.index(bank)
    return range(rank * trays // n, (rank + 1) * trays // n)


def supply_series(cdu_trace: Sequence[Any]) -> list[float]:
    """The CDU's rack supply with the first tick clamped into PhysicsCompute's
    config range — the series the events are cut from."""
    supply = series(cdu_trace, "sec_supply_c")
    return [clamp_supply(supply[0])] + supply[1:] if supply else supply


def supply_events(cdu_trace: Sequence[Any]) -> tuple[list[tuple[int, float]], float]:
    """The ``set-coolant-supply`` pairs and the deadband actually used.

    ``to_events`` widens the deadband until the series fits the event cap, and
    its contract is that the caller widens the seam tolerance by the same
    amount. ``adapt`` and ``check`` both come through here, so the seam can
    never be judged against a band the events were not cut at.
    """
    return to_events(supply_series(cdu_trace), K.value("supply_deadband_c"),
                     max_events=int(K.value("max_injected_events")), first=False)


def supply_deadband(cdu_trace: Sequence[Any]) -> float:
    return supply_events(cdu_trace)[1]


def dial_timeline(base_scenario: dict, n: int) -> list[tuple[int, int, int]]:
    """The base scenario's (gpu_pct, cpu_pct, data_feed_pct) on every tick,
    replaying its own set-workload / set-data-feed events."""
    wl = base_scenario.get("workload", {}) or {}
    gpu, cpu, feed = int(wl.get("gpuPct", 0)), int(wl.get("cpuPct", 0)), int(wl.get("dataFeedPct", 100))
    events = sorted(base_scenario.get("events", []) or [], key=lambda e: e["atS"])
    out, ei = [], 0
    for t in range(n):
        while ei < len(events) and events[ei]["atS"] <= t:
            ev = events[ei]
            ei += 1
            if ev.get("action") == "set-workload" and ev.get("workload"):
                w = ev["workload"]
                gpu, cpu = int(w.get("gpuPct", 0)), int(w.get("cpuPct", 0))
                feed = int(w.get("dataFeedPct", 100))
            elif ev.get("action") == "set-data-feed" and ev.get("value") is not None:
                feed = int(ev["value"])
        out.append((gpu, cpu, feed))
    return out


def adapt(
    cdu_trace: Sequence[Any],
    base_scenario: dict,
    carried_cap: Sequence[float],
    flow_setpoint_lpm: float,
    trays: int = 18,
) -> tuple[dict, list[dict], list[str]]:
    """PhysicsCDU trace (+ the carried cap series) -> PhysicsCompute scenario."""
    n = len(cdu_trace)
    max_ev = int(K.value("max_injected_events"))
    scenario = copy.deepcopy(base_scenario)
    notes: list[str] = []

    # Supply temperature.
    # SystemConfig bounds the *initial* supply to 17–45 °C; the event takes any value.
    supply = series(cdu_trace, "sec_supply_c")
    first = clamp_supply(supply[0])
    if abs(first - supply[0]) > 1e-9:
        notes.append("The CDU's starting supply is outside PhysicsCompute's 17–45 °C "
                     "config range; the first tick is clamped and the event at t=1 corrects it.")
    scenario.setdefault("config", {})["coolantSupplyC"] = round(first, 2)
    pairs, _ = supply_events(cdu_trace)
    injected = [{"atS": t, "action": "set-coolant-supply", "value": round(v, 2)} for t, v in pairs]

    # The carried cap, as scaled demand.
    dials = dial_timeline(base_scenario, n)
    scaled = [
        (int(round(g * min(1.0, max(0.0, carried_cap[t])))), c, f)
        for t, (g, c, f) in enumerate(dials)
    ]
    wl0 = scaled[0]
    scenario["workload"] = {"gpuPct": wl0[0], "cpuPct": wl0[1], "dataFeedPct": wl0[2]}
    last = wl0
    dial_events = []
    for t in range(1, n):
        if scaled[t] != last:
            last = scaled[t]
            dial_events.append({
                "atS": t, "action": "set-workload",
                "workload": {"gpuPct": last[0], "cpuPct": last[1], "dataFeedPct": last[2]},
            })
    if len(dial_events) > max_ev:
        step = len(dial_events) / max_ev
        dial_events = [dial_events[int(i * step)] for i in range(max_ev)]
        notes.append("Cap series thinned to the 240-event limit.")
    injected += dial_events

    # Pump flow lost.
    flow = series(cdu_trace, "sec_flow_lpm")
    lost = [round(max(0.0, 1.0 - f / flow_setpoint_lpm), 2) for f in flow]
    pairs, _ = to_events(lost, 0.005, max_events=max_ev, first=lost[0] > 0)
    injected += [{"atS": t, "action": "degrade-pump", "value": v} for t, v in pairs]

    # Tripped banks -> restricted trays.
    seen: set[int] = set()
    for t, state in enumerate(cdu_trace):
        status_row = list(get(state, "bank_status", []) or [])
        for bank, status in enumerate(status_row):
            if status == "tripped" and bank not in seen:
                seen.add(bank)
                for tray in tray_span(bank, status_row, trays):
                    injected.append({"atS": t, "action": "restrict-tray", "index": tray})

    kept = [
        e for e in scenario.get("events", []) or []
        if e.get("action") not in ("set-workload", "set-data-feed", "set-coolant-supply",
                                   "degrade-pump", "restrict-tray")
    ]
    injected.sort(key=lambda e: e["atS"])
    scenario["events"] = sorted(kept + injected, key=lambda e: e["atS"])
    return scenario, injected, notes


def check(
    compute_trace: Sequence[Any],
    cdu_trace: Sequence[Any],
    open_loop_trace: Sequence[Any],
    loop_residual_c: float = 0.0,
) -> list[SeamResult]:
    n = min(len(compute_trace), len(cdu_trace))
    got = series(compute_trace, "coolant_supply_c")[:n]
    want = series(cdu_trace, "sec_supply_c")[:n]
    if want:
        want[0] = clamp_supply(want[0])
    nominal = K.value("supply_deadband_c")
    band = supply_deadband(cdu_trace)
    supply = per_tick(
        ID, "Compute.coolant_supply_c == CDU.sec_supply_c (every tick)",
        got, want, "°C", band + 0.01 + loop_residual_c,
        note=f"{band:g} °C event deadband + 0.01 °C output rounding"
             + (f" (widened from {nominal:g} °C to fit the "
                f"{int(K.value('max_injected_events'))}-event cap)"
                if band > nominal + 1e-9 else "")
             + (f" + {loop_residual_c:.2f} °C the loop still moved on its last iteration"
                if loop_residual_c else ""),
        lhs_key="PhysicsCompute.coolant_supply_c", rhs_key="PhysicsCDU.sec_supply_c",
    )
    coupled = integral(series(compute_trace, "tokens_per_s")) / 1e6
    free = integral(series(open_loop_trace, "tokens_per_s")) / 1e6
    tokens = compare(
        ID, "∫ tokens (coupled) <= ∫ tokens (open loop)",
        coupled, free, "M tokens", 0.0,
        holds=coupled <= free + 1e-9,
        note="a closed loop can only cost compute, never add it",
    )
    return [supply, tokens]
