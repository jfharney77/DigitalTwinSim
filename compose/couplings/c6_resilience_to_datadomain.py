"""C6 — An attack timeline becomes a ransomware event in the backup
appliance, and comes back as restore time.

Two passes, open (not iterated): pass 1 PhysicsResilience gives the abstract
incident; PhysicsDataDomain reads it from the ingest side; pass 2 Resilience
reruns with detection timed from the appliance's entropy alarm.

Scope boundary, inherited from PhysicsResilience: this adapter passes rates,
sizes and timestamps. Nothing about technique crosses the seam, because
nothing about technique exists on either side of it.
"""

from __future__ import annotations

import copy
from typing import Any, Sequence

from ..reader import get, series
from ..seam import compare
from ..models import SeamResult

ID = "c6"


def incident(resilience_scenario: dict) -> dict | None:
    """The first scripted incident: start hour and spread rate (GB/h)."""
    for ev in sorted(resilience_scenario.get("events", []) or [], key=lambda e: e["atH"]):
        if ev.get("action") in ("incident", "slow-incident"):
            slow = ev["action"] == "slow-incident"
            rate = ev.get("value")
            if rate is None:
                rate = 20.0 if slow else 500.0
            return {"atH": int(ev["atH"]), "spreadGbH": float(rate), "slow": slow}
    return None


def contain_hour(resilience_trace: Sequence[Any]) -> int | None:
    for s in resilience_trace:
        if get(s, "contained", False):
            return int(get(s, "t_h"))
    return None


def adapt(
    resilience_scenario: dict,
    resilience_trace: Sequence[Any],
    base_scenario: dict | None = None,
) -> tuple[dict, list[dict], dict, list[str]]:
    """PhysicsResilience run -> PhysicsDataDomain scenario."""
    cfg = resilience_scenario.get("config", {}) or {}
    estate = float(cfg.get("estateTb", 200))
    change = float(cfg.get("changeGbDay", 500))
    inc = incident(resilience_scenario)
    scenario = copy.deepcopy(base_scenario or {})
    dataset = scenario.setdefault("dataset", {})
    dataset["fullTb"] = estate
    dataset["dailyChangePct"] = round(100.0 * change / (1000.0 * estate), 4)
    hours = len(resilience_trace) - 1
    scenario["durationDays"] = max(2, min(730, hours // 24))
    injected: list[dict] = []
    notes: list[str] = []
    if inc:
        pct_day = 100.0 * (inc["spreadGbH"] * 24.0 / 1000.0) / estate
        # PhysicsDataDomain encrypts for the whole of the day the event lands
        # on, so day d's backup reads the damage done between hours 24(d−1)
        # and 24d. An attack that starts at hour H therefore first shows up in
        # the backup after it — day H//24 + 1 — and starting it on day H//24
        # would put the appliance a whole day ahead of the attack's own clock.
        first_readable = inc["atH"] // 24 + 1
        # DataDomain takes its first full on day 1; an incident before that has
        # no baseline to be read against, so it starts on day 2 at the earliest.
        start_day = max(2, first_readable)
        if start_day != first_readable:
            notes.append("Incident moved to backup day 2: the appliance needs a first full to compare against.")
        injected.append({"atDay": start_day, "action": "ransomware-start",
                         "value": round(pct_day, 4)})
        stop = contain_hour(resilience_trace)
        if stop is not None:
            # Same clock, same shift: the last backup that still carries a day
            # of encryption is the one after containment, so the appliance
            # stops on the day after that.
            injected.append({"atDay": max(start_day + 1, stop // 24 + 1),
                             "action": "ransomware-stop"})
    kept = [e for e in scenario.get("events", []) or []
            if e.get("action") not in ("ransomware-start", "ransomware-stop")]
    scenario["events"] = sorted(kept + injected, key=lambda e: e["atDay"])
    config = {"fullTb": estate, "dailyChangePct": dataset["dailyChangePct"]}
    return scenario, injected, config, notes


def detection_from_alarm(
    resilience_scenario: dict, datadomain_summary: Any, datadomain_injected: list[dict],
    detect_base_h: float,
) -> tuple[dict, dict, list[str]]:
    """The appliance's entropy alarm, as PhysicsResilience detection timing.

    Resilience has no "detection latency" input: latency is
    ``detect_threshold_base_h / sensitivity`` (doubled for a slow incident).
    The adapter picks the integer sensitivity whose latency is closest to the
    alarm's without being earlier than it.
    """
    notes: list[str] = []
    scenario = copy.deepcopy(resilience_scenario)
    alarm_day = int(get(datadomain_summary, "alarm_day", -1))
    start = next((e["atDay"] for e in datadomain_injected if e["action"] == "ransomware-start"), None)
    info = {"alarmDay": alarm_day, "startDay": start, "latencyH": None, "sensitivity": None}
    if alarm_day < 0 or start is None:
        notes.append("The entropy alarm never fired; pass 2 is pass 1.")
        return scenario, info, notes
    # A daily instrument reads the damage at the next backup after it starts.
    latency_h = max(24.0, (alarm_day - start + 1) * 24.0)
    inc = incident(resilience_scenario) or {"slow": False}
    factor = 2.0 if inc["slow"] else 1.0
    sens = 1
    for s in range(10, 0, -1):
        if detect_base_h * factor / s >= latency_h - 1e-9:
            sens = s
            break
    cfg = scenario.setdefault("config", {})
    own = None
    if cfg.get("detection"):
        own = detect_base_h * factor / int(cfg.get("sensitivity", 5))
    if own is not None and own <= latency_h:
        notes.append("Resilience's own detection is already earlier than the entropy alarm; unchanged.")
    else:
        cfg["detection"] = True
        cfg["sensitivity"] = sens
    info.update({"latencyH": latency_h, "sensitivity": cfg.get("sensitivity"),
                 "modelLatencyH": round(detect_base_h * factor / cfg.get("sensitivity", sens), 2)})
    return scenario, info, notes


def check_encrypted(
    resilience_scenario: dict,
    resilience_trace: Sequence[Any],
    datadomain_trace: Sequence[Any],
    datadomain_injected: list[dict],
    full_tb: float,
) -> SeamResult:
    """Both engines agree how much is encrypted, day by day until containment."""
    inc = incident(resilience_scenario)
    start_day = next((e["atDay"] for e in datadomain_injected
                      if e["action"] == "ransomware-start"), None)
    if not inc or start_day is None:
        return compare(ID, "encrypted TB agrees across the seam", 0.0, 0.0, "TB", 0.0,
                       note="no incident in the chain")
    one_day = inc["spreadGbH"] * 24.0 / 1000.0
    corrupted = series(resilience_trace, "corrupted_tb")
    stop = contain_hour(resilience_trace)
    recovered_at = next((int(get(s, "t_h")) for s in resilience_trace if get(s, "recovered", False)),
                        len(resilience_trace))
    last_h = min(stop if stop is not None else len(resilience_trace) - 1, recovered_at - 1)
    worst, worst_day, lhs, rhs = -1.0, None, 0.0, 0.0
    for state in datadomain_trace:
        day = int(get(state, "day"))
        hour = day * 24
        if day < start_day or hour > last_h or hour >= len(corrupted):
            continue
        dd_tb = float(get(state, "encrypted_fraction_pct", 0.0)) / 100.0 * full_tb
        e = abs(dd_tb - corrupted[hour])
        if e > worst:
            worst, worst_day, lhs, rhs = e, day, dd_tb, corrupted[hour]
    return compare(
        ID, "DataDomain.encrypted_fraction × full_tb == Resilience.corrupted_tb (each day, until containment)",
        lhs, rhs, "TB", one_day + 0.01 * full_tb / 100.0,
        worst_tick=worst_day,
        holds=None if worst_day is not None else False,
        note=(f"tolerance is one day of spread ({one_day:.2f} TB): the appliance reads daily, "
              "the attack runs hourly") if worst_day is not None else
             "No backup day fell inside the incident window: 0 TB on both sides is not evidence.",
        lhs_key="PhysicsDataDomain.encrypted_tb", rhs_key="PhysicsResilience.corrupted_tb",
    )


def check_rto(resilience_scenario: dict, resilience_summary: Any, decide_h: float) -> SeamResult:
    """Resilience's own restore-time law, unchanged by the seam."""
    cfg = resilience_scenario.get("config", {}) or {}
    estate = float(cfg.get("estateTb", 200))
    gbps = float(cfg.get("restoreGbps", 1.0))
    law = decide_h + estate * 1000.0 / (gbps * 3600.0)
    got = float(get(resilience_summary, "rto_hours", 0.0))
    return compare(
        ID, "pass-2 rto_hours == decide_h + estate_TB × 1000 / (restore GB/s × 3600)",
        got, law, "h", 1.0,
        note="1 h tolerance: the engine ticks hourly and completes on the next tick",
    )
