"""Pure physics engine for the PowerCool CDU / PowerRack / IRC twin.

``simulate(scenario)`` returns the deterministic timestepped trace of the
loop: facility water in, heat exchanger, pumped rack coolant out to the
tray banks and back — with the Integrated Rack Controller deciding what
happens when the loop can't keep up. Same purity rule as every twin in
this repo: no FastAPI, no IO, no timers, no randomness — the frontend
owns the playback clock, and each ``SimState`` is plain data.

The identity that holds by construction and is asserted in the tests, in
the house style of the IR7000 heat balance:

* **Both loops carry the same heat, every tick**: the IT heat equals
  ṁ·cp·ΔT on the secondary loop and ṁ·cp·ΔT on the primary loop. A
  CDU is a device for making those three numbers equal; the trace never
  lets them drift apart.

Simplifications, stated honestly: heat transport is quasi-static (the
return temperatures are derived exactly from the current heat and flows;
only the supply temperature and silicon carry first-order lags), pump
heat is not added to the coolant, and the heat exchanger is a UA ×
flow-factor lump rather than an NTU integration. Correct relationships
and orders of magnitude, not CFD.
"""

from __future__ import annotations

from .constants import value as C
from .models import (
    LogEntry,
    Scenario,
    SimState,
    Summary,
)

DT = 1.0  # sim timestep, seconds — fixed; playback pacing is the frontend's

AMBIENT_C = 24.0
MAX_BANKS = 6
SUPPLY_RUNAWAY_C = 95.0


def pump_flow_lpm(pumps_alive: int, setpoint_lpm: float) -> tuple[float, float]:
    """(delivered flow L/min, per-pump speed fraction).

    Parallel pumps on a shared system curve add flow sublinearly:
    Q_max(k) = Q_single · k^0.65. The controller runs the pumps at
    whatever speed hits the flow setpoint, clamped at 100%.
    """
    if pumps_alive <= 0:
        return 0.0, 0.0
    q_max = C("pump_single_flow_lpm") * pumps_alive ** C("pump_parallel_exponent")
    flow = min(setpoint_lpm, q_max)
    speed = flow / q_max
    return flow, speed


def bank_heat_kw(util_frac: float, cap: float) -> float:
    """One tray bank's liquid heat at the given utilization and IRC cap."""
    idle = C("group_idle_fraction")
    return C("group_kw") * (idle + (1.0 - idle) * util_frac) * cap


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    env = scenario.environment.model_copy()
    util = scenario.workload.util_pct / 100.0
    min_supply = float(cfg.min_supply_c)
    events = sorted(scenario.events, key=lambda e: e.at_s)

    ua = C("hx_ua_kw_per_k")
    ff_exp = C("flow_ff_exponent")
    flow_nom = C("flow_nominal_lpm")
    cp_pg = C("cp_pg25")
    rho_pg = C("rho_pg25")
    cp_w = C("cp_water")
    rho_w = C("rho_water")
    design_dt = C("fac_design_dt_c")
    r_chip = C("r_chip_k_per_kw")
    dew_margin = C("dew_margin_c")
    target = C("chip_target_c")
    trip_c = C("chip_trip_c")

    # Mutable machine state.
    present = [i < cfg.tray_groups for i in range(MAX_BANKS)]
    tripped = [False] * MAX_BANKS
    sustain = [0.0] * MAX_BANKS
    dead_pumps: set[int] = set()
    cap = 1.0
    floor0 = max(min_supply, env.dew_point_c + dew_margin)
    supply = max(env.facility_supply_c, floor0)
    chip = AMBIENT_C
    was_capping = False
    floor_was_active = False

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    peak_it = 0.0
    peak_chip = 0.0
    min_cap = 1.0
    capped_seconds = 0
    delivered_kwh = 0.0

    steps = int(scenario.duration_s / DT)
    for step in range(steps + 1):
        t = int(step * DT)

        # Apply due events.
        while ei < len(events) and events[ei].at_s <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-util" and ev.value is not None:
                util = max(0.0, min(1.0, ev.value / 100.0))
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Utilization set to {ev.value:g}%"))
            elif ev.action == "set-facility-supply" and ev.value is not None:
                log.append(LogEntry(
                    t=t, severity="warning" if ev.value > env.facility_supply_c
                    else "info",
                    message=f"Facility supply water now {ev.value:g} °C",
                ))
                env.facility_supply_c = ev.value
            elif ev.action == "set-dew-point" and ev.value is not None:
                env.dew_point_c = ev.value
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Room dew point now {ev.value:g} °C"))
            elif ev.action == "set-min-supply" and ev.value is not None:
                min_supply = ev.value
                log.append(LogEntry(
                    t=t, severity="info",
                    message=f"Minimum-supply setpoint now {ev.value:g} °C",
                ))
            elif ev.action == "fail-pump" and ev.index is not None:
                if 0 <= ev.index < cfg.pumps and ev.index not in dead_pumps:
                    dead_pumps.add(ev.index)
                    log.append(LogEntry(
                        t=t, severity="warning",
                        message=f"Pump {ev.index + 1} failed — survivors "
                                "ramping to hold flow",
                    ))
            elif ev.action == "restore-pump" and ev.index is not None:
                if ev.index in dead_pumps:
                    dead_pumps.discard(ev.index)
                    log.append(LogEntry(t=t, severity="info",
                                        message=f"Pump {ev.index + 1} restored"))
            elif ev.action == "add-tray-group":
                for i in range(MAX_BANKS):
                    if not present[i]:
                        present[i] = True
                        tripped[i] = False
                        sustain[i] = 0.0
                        log.append(LogEntry(
                            t=t, severity="info",
                            message=f"Tray bank {i + 1} installed "
                                    f"(+{C('group_kw'):g} kW of load)",
                        ))
                        break
            elif ev.action == "remove-tray-group":
                for i in reversed(range(MAX_BANKS)):
                    if present[i]:
                        present[i] = False
                        log.append(LogEntry(t=t, severity="info",
                                            message=f"Tray bank {i + 1} removed"))
                        break

        # --- Hydraulics ---------------------------------------------------
        pumps_alive = cfg.pumps - len(dead_pumps)
        flow, speed = pump_flow_lpm(pumps_alive, cfg.flow_setpoint_lpm)
        pump_kw = pumps_alive * C("pump_max_kw") * speed ** 3
        m_dot_sec = flow / 60.0 * rho_pg  # kg/s

        # --- Heat in ---------------------------------------------------------
        online = [i for i in range(MAX_BANKS) if present[i] and not tripped[i]]
        n_present = sum(present)
        q_it = sum(bank_heat_kw(util, cap) for _ in online)

        # --- Heat exchanger & supply temperature ---------------------------
        floor_c = max(min_supply, env.dew_point_c + dew_margin)
        if flow > 0:
            ff = (flow / flow_nom) ** ff_exp
            emergent = env.facility_supply_c + q_it / (ua * ff)
        else:
            emergent = SUPPLY_RUNAWAY_C if q_it > 0 else env.facility_supply_c
        supply_ss = min(max(emergent, floor_c), SUPPLY_RUNAWAY_C)
        supply += (supply_ss - supply) * DT / C("tau_loop_s")
        # The mixing valve is instantaneous: the condensation floor holds
        # on every tick, not just at steady state.
        supply = max(supply, env.dew_point_c + dew_margin)
        floor_active = floor_c > emergent + 0.01
        if floor_active and not floor_was_active:
            log.append(LogEntry(
                t=t, severity="info",
                message="Mixing valve holding supply at the floor "
                        f"({floor_c:g} °C) — condensation guard",
            ))
        floor_was_active = floor_active

        # --- Loop temperatures (returns derived exactly from Q and flow) ---
        if m_dot_sec > 0:
            sec_ret = supply + q_it / (m_dot_sec * cp_pg)
        else:
            sec_ret = supply
        if q_it > 0:
            m_dot_fac = q_it / (cp_w * design_dt)
            fac_ret = env.facility_supply_c + design_dt
        else:
            m_dot_fac = 0.0
            fac_ret = env.facility_supply_c
        fac_flow_lpm = m_dot_fac / rho_w * 60.0

        # --- Silicon ---------------------------------------------------------
        if online and m_dot_sec > 0:
            q_bank = q_it / len(online)
            chip_ss = supply + q_it / (2.0 * m_dot_sec * cp_pg) + q_bank * r_chip
        elif online:
            chip_ss = SUPPLY_RUNAWAY_C
        else:
            chip_ss = supply if n_present else AMBIENT_C
        chip += (chip_ss - chip) * DT / C("tau_chip_s")

        # --- IRC policy --------------------------------------------------------
        if cfg.policy == "coordinated":
            err = chip - target
            if err > 0.25:
                cap = max(C("cap_floor"), cap - C("cap_kp") * err * DT)
            elif err < -0.75 and cap < 1.0:
                cap = min(1.0, cap + C("cap_recover_per_s") * DT)
        else:
            cap = 1.0
            for i in online:
                if chip > trip_c:
                    sustain[i] += DT
                    if sustain[i] >= (C("trip_sustain_base_s")
                                      + C("trip_sustain_step_s") * i):
                        tripped[i] = True
                        log.append(LogEntry(
                            t=t, severity="critical",
                            message=f"Tray bank {i + 1} hit its own trip "
                                    f"({trip_c:g} °C) and powered off",
                        ))
                else:
                    sustain[i] = 0.0

        capping = cap < 0.999
        if capping and not was_capping:
            log.append(LogEntry(
                t=t, severity="warning",
                message="IRC shedding load — power caps engaged across "
                        "all tray banks",
            ))
        elif was_capping and not capping:
            log.append(LogEntry(t=t, severity="info",
                                message="IRC caps released — margin restored"))
        was_capping = capping

        # --- Bookkeeping ---------------------------------------------------------
        peak_it = max(peak_it, q_it)
        peak_chip = max(peak_chip, chip)
        min_cap = min(min_cap, cap)
        if capping:
            capped_seconds += 1
        delivered_kwh += q_it * DT / 3600.0
        trips = sum(tripped)

        region_temps = {
            "facility-plant": round(env.facility_supply_c, 1),
            "pipe-fac-supply": round(env.facility_supply_c, 1),
            "pipe-fac-return": round(fac_ret, 1),
            "hx": round((env.facility_supply_c + supply) / 2.0, 1),
            "irc": 28.0,
            **{f"pump-{i}": round(AMBIENT_C if (i in dead_pumps or i >= cfg.pumps)
                                  else sec_ret + 1.0, 1)
               for i in range(3)},
            "pipe-sec-supply": round(supply, 1),
            "pipe-sec-return": round(sec_ret, 1),
            "manifold-supply": round(supply, 1),
            "manifold-return": round(sec_ret, 1),
            **{f"tray-{i}": round(
                chip if (present[i] and not tripped[i])
                else (28.0 if tripped[i] else AMBIENT_C), 1)
               for i in range(MAX_BANKS)},
        }

        trace.append(SimState(
            t=t,
            it_load_kw=round(q_it, 2),
            heat_removed_kw=round(q_it, 2),
            hx_load_pct=round(100.0 * q_it / C("hx_rated_kw"), 1),
            fac_supply_c=round(env.facility_supply_c, 2),
            fac_return_c=round(fac_ret, 2),
            fac_flow_lpm=round(fac_flow_lpm, 1),
            sec_supply_c=round(supply, 2),
            sec_return_c=round(sec_ret, 2),
            sec_flow_lpm=round(flow, 1),
            approach_c=round(supply - env.facility_supply_c, 2),
            pump_speed_pct=round(100.0 * speed, 1),
            pumps_alive=pumps_alive,
            pump_power_kw=round(pump_kw, 2),
            groups_present=n_present,
            groups_online=len(online),
            bank_status=[
                ("tripped" if tripped[i] else "online") if present[i] else "absent"
                for i in range(MAX_BANKS)
            ],
            trips=trips,
            cap_pct=round(100.0 * cap, 1),
            capping=capping,
            chip_temp_c=round(chip, 2),
            dew_margin_c=round(supply - env.dew_point_c, 2),
            floor_active=floor_active,
            region_temps=region_temps,
        ))

    last = trace[-1]
    summary = Summary(
        peak_it_kw=round(peak_it, 1),
        steady_it_kw=last.it_load_kw,
        peak_chip_c=round(peak_chip, 2),
        min_cap_pct=round(100.0 * min_cap, 1),
        capped_seconds=capped_seconds,
        trips=last.trips,
        delivered_kwh=round(delivered_kwh, 3),
    )
    return trace, log, summary
