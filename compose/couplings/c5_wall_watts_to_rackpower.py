"""C5 — Server wall watts load the rack's phases.

Up to eight source runs (PowerEdge R760 from DellPowerEdgeR760Thermal, or an
XE7745 / XE9680 from PhysicsCompute) become PhysicsRackPower load slots.
``RackLoad.power_w`` is capped at 2000 W: an R760 fits; a multi-kW GPU server
is split one slot per PSU feed, and refused — not clamped — when a single PSU
share still exceeds the slot. The busbar-fed XE9712 is out of scope.
"""

from __future__ import annotations

import copy
from typing import Any, Sequence

from .. import constants as K
from ..reader import get, series
from ..resample import integral, to_events
from ..seam import compare, per_tick
from ..models import SeamResult

ID = "c5"
SLOT_MAX_W = 2000.0
SLOTS = 8
PHASES = ("A", "B", "C")


class OversizedServer(ValueError):
    """A server whose per-PSU share exceeds what one rack slot can carry."""


def slot_series(source_trace: Sequence[Any], label: str) -> list[tuple[str, list[float]]]:
    """One wall-watt series per rack slot this server occupies."""
    ac = series(source_trace, "ac_power_w")
    peak = max(ac) if ac else 0.0
    if peak <= SLOT_MAX_W:
        return [(label, ac)]
    psus = [max(1, int(get(s, "alive_psus", 1) or 1)) for s in source_trace]
    feeds = max(psus)
    shares = [a / n for a, n in zip(ac, psus)]
    if max(shares) > SLOT_MAX_W:
        raise OversizedServer(
            f"{label}: {peak:.0f} W over {feeds} PSU feed(s) is {max(shares):.0f} W per feed, "
            f"above the {SLOT_MAX_W:.0f} W a PhysicsRackPower slot carries. Refused rather "
            "than clamped: clamping would make the rack look safer than it is."
        )
    # A dead PSU's slot reads zero and the survivors carry its share.
    out = []
    for k in range(feeds):
        out.append((f"{label} PSU {k + 1}",
                    [a / n if k < n else 0.0 for a, n in zip(ac, psus)]))
    return out


def adapt(
    sources: Sequence[tuple[str, Sequence[Any]]],
    base_scenario: dict | None = None,
    params: dict | None = None,
) -> tuple[dict, list[dict], dict, list[str]]:
    """``[(label, source_trace), ...]`` -> PhysicsRackPower scenario."""
    params = params or {}
    slots: list[tuple[str, list[float]]] = []
    for label, trace in sources:
        slots.extend(slot_series(trace, label))
    if len(slots) > SLOTS:
        raise OversizedServer(f"{len(slots)} feeds need more than the rack's {SLOTS} slots")
    phases = list(params.get("phases") or [])
    n = min(len(s) for _, s in slots)
    scenario = copy.deepcopy(base_scenario or {})
    loads = []
    for i in range(SLOTS):
        if i < len(slots):
            loads.append({"label": slots[i][0], "powerW": round(slots[i][1][0], 1),
                          "phase": phases[i] if i < len(phases) else PHASES[i % 3]})
        else:
            loads.append({"label": "Empty", "powerW": 0, "phase": PHASES[i % 3]})
    scenario.setdefault("config", {})["loads"] = loads
    scenario["durationS"] = max(10, n - 1)
    injected: list[dict] = []
    band_used = K.value("load_deadband_w")
    per_slot = max(1, int(K.value("max_injected_events")) // max(len(slots), 1))
    for i, (_, watts) in enumerate(slots):
        pairs, band = to_events(watts[:n], K.value("load_deadband_w"),
                                max_events=per_slot, first=False)
        band_used = max(band_used, band)
        injected += [{"atS": t, "action": "set-load", "index": i, "value": round(v, 1)}
                     for t, v in pairs]
    injected.sort(key=lambda e: (e["atS"], e["index"]))
    kept = [e for e in scenario.get("events", []) or [] if e.get("action") != "set-load"]
    scenario["events"] = sorted(kept + injected, key=lambda e: e["atS"])
    config = {"slotsUsed": len(slots), "deadbandW": band_used,
              "loads": [{"label": l["label"], "phase": l["phase"]} for l in loads[:len(slots)]]}
    return scenario, injected, config, []


def total_wall_w(sources: Sequence[tuple[str, Sequence[Any]]]) -> list[float]:
    n = min(len(t) for _, t in sources)
    return [sum(float(get(t[i], "ac_power_w", 0.0)) for _, t in sources) for i in range(n)]


def check(
    sources: Sequence[tuple[str, Sequence[Any]]],
    rack_trace: Sequence[Any],
    slots_used: int,
    deadband_w: float | None = None,
) -> list[SeamResult]:
    band = deadband_w if deadband_w is not None else K.value("load_deadband_w")
    wall = total_wall_w(sources)
    n = min(len(wall), len(rack_trace))
    pdu = series(rack_trace, "pdu_input_w")[:n]
    skip = [bool(get(rack_trace[i], "tripped_phases", [])) or
            not get(rack_trace[i], "rack_powered", True) for i in range(n)]
    tick = per_tick(
        ID, "Σ servers ac_power_w == RackPower.pdu_input_w (every tick, no phase tripped)",
        wall[:n], pdu, "W", band * slots_used + 0.1 * slots_used, skip=skip,
        note=f"{band:g} W event deadband × {slots_used} slot(s) + 0.1 W output rounding each"
             + (f"; {sum(skip)} tick(s) excluded (a breaker had tripped)" if any(skip) else ""),
        lhs_key="servers.ac_power_w", rhs_key="PhysicsRackPower.pdu_input_w",
    )
    e_src = integral([w for w, s in zip(wall, skip) if not s]) / 3.6e6
    e_dst = integral([w for w, s in zip(pdu, skip) if not s]) / 3.6e6
    eligible = n - sum(skip[:n])
    run = compare(ID, "∫ servers dt == ∫ PDU input dt (over the run)", e_src, e_dst, "kWh",
                  0.002 * max(e_src, 1e-9),
                  holds=None if eligible else False,
                  note=("relative tolerance 0.2% of the source energy" if eligible else
                        "No tick was eligible for comparison: 0 kWh on both sides is not evidence."))
    return [tick, run]
