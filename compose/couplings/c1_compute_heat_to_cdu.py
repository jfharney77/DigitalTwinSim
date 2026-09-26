"""C1 — XE9712 liquid heat becomes the CDU's load.

PhysicsCDU has no "heat in kW" input. Its load is
``groups_online × group_kw × (idle + (1 − idle)·util) × cap``; the adapter
inverts that, choosing the bank count from the peak and the utilization per
tick. ``util_pct`` is an integer, so the seam carries a stated quantization
error; heat below the idle floor cannot be expressed and those ticks are
flagged rather than hidden.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Sequence

from .. import constants as K
from ..reader import get, series
from ..resample import integral, to_events
from ..seam import compare, per_tick
from ..models import SeamResult

ID = "c1"
CDU_DEFAULTS = {"group_kw": 40.0, "group_idle_fraction": 0.08, "max_groups": 6}


def liquid_kw(source_trace: Sequence[Any], racks: int = 1) -> list[float]:
    """Liquid heat of ``racks`` identical racks sharing one CDU, in kW."""
    return [racks * w / 1000.0 for w in series(source_trace, "liquid_watts")]


class OversizedPayload(ValueError):
    """More rack heat than the largest CDU the target engine can build.

    Past ``max_groups × group_kw`` the bank formula has nothing left to say: the
    utilization dial saturates at 100% and every further watt is silently
    dropped. Refused rather than clamped, for C5's reason — a clamped load makes
    the loop look able to carry heat it cannot, and the closed loop would then
    iterate against a CDU run that no longer answers the rack it was given.
    """


def plan(source_trace: Sequence[Any], cdu: dict | None = None, racks: int = 1) -> dict:
    """Bank count and per-tick integer utilization for a liquid-heat series."""
    c = {**CDU_DEFAULTS, **(cdu or {})}
    heat = liquid_kw(source_trace, racks)
    gkw, idle = c["group_kw"], c["group_idle_fraction"]
    peak = max(heat) if heat else 0.0
    ceiling = int(c["max_groups"]) * gkw
    if peak > ceiling:
        raise OversizedPayload(
            f"{racks} rack(s) peak at {peak:.0f} kW of liquid heat, above the "
            f"{ceiling:.0f} kW a CDU of {int(c['max_groups'])} × {gkw:.0f} kW banks can "
            f"carry. Refused rather than clamped: at most {int(ceiling // max(peak / max(racks, 1), 1e-9))} "
            "rack(s) of this run fit one CDU."
        )
    groups = min(int(c["max_groups"]), max(1, math.ceil(peak / gkw - 1e-9)))
    full = groups * gkw
    util: list[int] = []
    unexpressible: list[bool] = []
    for q in heat:
        raw = ((q / full) - idle) / (1.0 - idle)
        unexpressible.append(raw < -1e-9 or raw > 1.0 + 1e-9)
        util.append(int(round(100.0 * min(1.0, max(0.0, raw)))))
    return {"groups": groups, "util": util, "unexpressible": unexpressible,
            "heat_kw": heat, "group_kw": gkw, "idle": idle}


def util_events(util: Sequence[int]) -> tuple[list[tuple[int, float]], float]:
    """The ``set-util`` pairs and the deadband actually used.

    ``to_events`` widens the deadband until the series fits the event cap, and
    its contract is that the caller widens the seam tolerance by the same
    amount. ``adapt`` and ``check`` both come through here so neither can read
    a band the other did not use.
    """
    return to_events(
        [float(u) for u in util], K.value("util_deadband_pct") - 0.5,
        max_events=int(K.value("max_injected_events")), start=0, first=False,
    )


def held_util_points(band: float) -> int:
    """Utilization points the zero-order hold can be behind, on top of the
    ±0.5 integer rounding. Events fire when the integer utilization moves by
    more than ``band``, so at the nominal 0.5 every change is emitted and the
    hold costs nothing."""
    return int(math.floor(max(0.0, band)))


def deadband_used(util: Sequence[int]) -> float:
    """The band as ``injected_config["eventDeadbandUsed"]`` reports it: the
    raw ``to_events`` band plus the ±0.5 of integer rounding it sits on."""
    return util_events(util)[1] + 0.5


def _replan(p: dict, groups: int) -> dict:
    """Re-derive utilization for a bank count fixed earlier (closed loop: the
    hardware is sized once, from the open-loop peak)."""
    full, idle = groups * p["group_kw"], p["idle"]
    util, bad = [], []
    for q in p["heat_kw"]:
        raw = ((q / full) - idle) / (1.0 - idle)
        bad.append(raw < -1e-9 or raw > 1.0 + 1e-9)
        util.append(int(round(100.0 * min(1.0, max(0.0, raw)))))
    return {**p, "groups": groups, "util": util, "unexpressible": bad}


def expressible(
    source_trace: Sequence[Any],
    cdu: dict | None = None,
    racks: int = 1,
    groups: int | None = None,
) -> list[bool]:
    """Per tick: can the CDU's bank formula carry this much heat at all?

    The seam excludes the ticks where it cannot (below the idle floor, above the
    banks' ceiling). Anything reasoning about how well the two engines agree —
    the closed loop's residual included — has to exclude the same ticks, or it
    is measuring a quantity the coupling never claimed.
    """
    p = plan(source_trace, cdu, racks)
    if groups is not None and groups != p["groups"]:
        p = _replan(p, groups)
    return [not bad for bad in p["unexpressible"]]


def adapt(
    source_trace: Sequence[Any],
    base_scenario: dict | None = None,
    params: dict | None = None,
    cdu: dict | None = None,
    racks: int = 1,
    groups: int | None = None,
) -> tuple[dict, list[dict], dict, list[str]]:
    """PhysicsCompute trace -> PhysicsCDU scenario.

    Returns ``(scenario, injected_events, injected_config, notes)``.
    """
    p = plan(source_trace, cdu, racks)
    if groups is not None and groups != p["groups"]:
        p = _replan(p, groups)
    scenario = copy.deepcopy(base_scenario or {})
    config = scenario.setdefault("config", {})
    config["trayGroups"] = p["groups"]
    scenario.setdefault("workload", {})["utilPct"] = p["util"][0] if p["util"] else 0
    scenario["durationS"] = max(10, len(source_trace) - 1)
    pairs, band = util_events(p["util"])
    injected = [{"atS": t, "action": "set-util", "value": v} for t, v in pairs]
    kept = [e for e in scenario.get("events", []) if e.get("action") != "set-util"]
    scenario["events"] = sorted(kept + injected, key=lambda e: e["atS"])
    notes = []
    if held_util_points(band):
        notes.append(
            f"The utilization series needed more than {int(K.value('max_injected_events'))} "
            f"events, so the event deadband widened to {band + 0.5:g} utilization point(s); "
            "the seam tolerance widens with it."
        )
    n_bad = sum(p["unexpressible"])
    if n_bad:
        floor = p["groups"] * p["group_kw"] * p["idle"]
        notes.append(
            f"{n_bad} tick(s) carry heat the CDU's bank formula cannot express "
            f"(below the {floor:.1f} kW idle floor of {p['groups']} banks, or above "
            f"{p['groups'] * p['group_kw']:.0f} kW); they are excluded from the seam, not hidden."
        )
    return scenario, injected, {"trayGroups": p["groups"], "eventDeadbandUsed": band + 0.5}, notes


def check(
    source_trace: Sequence[Any],
    target_trace: Sequence[Any],
    cdu: dict | None = None,
    integral_tolerance: float = 0.005,
    extra_note: str = "",
    racks: int = 1,
    groups: int | None = None,
    deadband_pct: float | None = None,
) -> list[SeamResult]:
    """Heat out == heat in, per tick and over the run.

    ``deadband_pct`` is the band the adapter reported in
    ``injected_config["eventDeadbandUsed"]``. Left out, it is recomputed from
    the same series through the same ``util_events``, so the seam can never be
    judged against a band the events were not cut at.
    """
    p = plan(source_trace, cdu, racks)
    if groups is not None and groups != p["groups"]:
        p = _replan(p, groups)
    n = min(len(source_trace), len(target_trace))
    heat = p["heat_kw"][:n]
    load = series(target_trace, "it_load_kw")[:n]
    # PhysicsCDU computes a tick's heat with the cap left by the previous tick,
    # then updates the cap; so a tick is "uncapped" only if both read 100%.
    capped = [float(get(target_trace[i], "cap_pct", 100.0)) < 100.0 for i in range(n)]
    skip = [
        p["unexpressible"][i]
        or capped[i] or (i > 0 and capped[i - 1])
        or int(get(target_trace[i], "trips", 0)) > 0
        for i in range(n)
    ]
    # kW per utilization point, so a bound in util points converts to one in kW.
    kw_per_point = (1.0 - p["idle"]) * p["groups"] * p["group_kw"] / 100.0
    quantum = 0.5 * kw_per_point
    # The deadband the adapter actually used: widened when the series needed
    # more than the event cap, and the seam tolerance widens with it.
    band = deadband_pct if deadband_pct is not None else deadband_used(p["util"])
    held = held_util_points(band - 0.5)
    deadband_kw = held * kw_per_point
    skipped = sum(skip)
    note = (
        f"integer util quantization, <= {quantum:.2f} kW at {p['groups']} bank(s)"
        + (f"; event deadband widened to {held + 0.5:g} util point(s) to fit the "
           f"{int(K.value('max_injected_events'))}-event cap, <= {deadband_kw:.2f} kW more"
           if held else "")
        + (f"; {skipped} tick(s) excluded (CDU capped or tripped, or heat unexpressible)"
           if skipped else "")
        + (f"; {extra_note}" if extra_note else "")
    )
    tick = per_tick(
        ID, ("racks × " if racks > 1 else "") + "Compute.liquid_watts / 1000 == CDU.it_load_kw (every uncapped tick)",
        heat, load, "kW", quantum + deadband_kw + 0.05, skip=skip, note=note,
        lhs_key="PhysicsCompute.liquid_kw", rhs_key="PhysicsCDU.it_load_kw",
    )
    e_src = integral([h for h, s in zip(heat, skip) if not s]) / 3600.0
    e_dst = integral([q for q, s in zip(load, skip) if not s]) / 3600.0
    eligible = n - skipped
    # A held utilization can be behind on every eligible tick, so the energy
    # bound carries it for the whole eligible span (1 s ticks -> hours).
    tol = integral_tolerance * max(e_src, 1e-9) + deadband_kw * eligible / 3600.0
    run = compare(
        ID, "∫ Compute.liquid dt == ∫ CDU.it_load dt (over the run)",
        e_src, e_dst, "kWh", tol,
        holds=None if eligible else False,
        note=(f"relative tolerance {100 * integral_tolerance:g}% of the source energy"
              + (f", plus the widened deadband over {eligible} eligible tick(s)"
                 if deadband_kw else "")
              if eligible else
              "No tick was eligible for comparison: 0 kWh on both sides is not evidence."),
    )
    return [tick, run]


def air_share_kwh(source_trace: Sequence[Any]) -> float:
    """Heat that never crosses this seam: it goes to the room, not the loop."""
    return integral(series(source_trace, "air_watts")) / 3.6e6
