"""Pure physics engine for the PowerEdge XR rugged-edge simulator.

``simulate(scenario)`` returns the deterministic timestepped trace of the
configured sled under the given workload, environment, and timed events.
Same purity rule as every twin in this repo: no FastAPI, no IO, no timers,
no randomness — the frontend owns the playback clock, and each ``SimState``
is plain data.

This is the R760Thermal engine with the environment unlocked, which is the
whole product story: same causal chain (configuration → load → power →
heat → fan response → feedback), hostile inputs. Three additions carry the
rugged personality:

* **Filter fouling** raises the system's airflow resistance, so the same
  fan rpm moves less air — and the controller answers with more rpm, at
  the cubic power cost. Months of dust become watts.
* **Vibration** taxes spinning drives (head repositioning) and leaves
  SSDs untouched — reported as ``storage_perf_lost_pct``.
* **The feed can sag.** At constant power, current = P/V rises as voltage
  falls; a brownout that idles through at 2 A trips the input limit at
  full load. Deep sags drop the PSUs outright.

Two identities hold by construction and are asserted in the tests, house
style: **power balance every tick** (component powers sum to DC; wall AC =
DC ÷ efficiency at the load point) and **heat balance** (exhaust = inlet +
DC/(ṁ·cp) — the IR7000 identity inside one short-depth box).
"""

from __future__ import annotations

from .constants import PSU_EFFICIENCY_CURVE, value as C
from .models import (
    Environment,
    LogEntry,
    Scenario,
    ServerConfig,
    SimState,
    Summary,
    Workload,
)

DT = 1.0  # sim timestep, seconds — fixed; playback pacing is the frontend's


def psu_efficiency(load_fraction: float) -> float:
    """Piecewise-linear interpolation over the Titanium-class curve."""
    pts = PSU_EFFICIENCY_CURVE
    if load_fraction <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if load_fraction <= x1:
            f = (load_fraction - x0) / (x1 - x0)
            return y0 + f * (y1 - y0)
    return pts[-1][1]


def fouling_fraction(env: Environment) -> float:
    """Airflow resistance added by the filter's accumulated dust."""
    rate = {
        "clean": C("fouling_rate_clean"),
        "moderate": C("fouling_rate_moderate"),
        "heavy": C("fouling_rate_heavy"),
    }[env.dust]
    return min(C("fouling_cap"), env.filter_months * rate)


def storage_perf_lost(cfg: ServerConfig, env: Environment) -> float:
    """Throughput a spinning drive loses to vibration. SSDs lose nothing."""
    if cfg.drive_type != "hdd" or cfg.drives == 0:
        return 0.0
    return {
        "none": 0.0,
        "roadside": C("vib_hdd_roadside_pct"),
        "vehicle": C("vib_hdd_vehicle_pct"),
    }[env.vibration]


def _cpu_power(cfg: ServerConfig, util: float, boost: bool, clamp: float) -> float:
    """P = idle + (TDP − idle) × util^1.4, boosted briefly at full load,
    clamped by the throttle multiplier. XR sleds are single-socket."""
    tdp = float(cfg.cpu_tdp_w)
    idle = C("cpu_idle_fraction") * tdp
    p = idle + (tdp - idle) * (util ** C("cpu_util_exponent"))
    if boost and util >= 0.999:
        p = tdp * C("cpu_boost_multiplier")
    return p * clamp


def _accel_power(cfg: ServerConfig, util: float, clamp: float) -> float:
    if not cfg.accels_single_wide:
        return 0.0
    tdp = C("accel_sw_tdp")
    idle = C("accel_idle_fraction") * tdp
    p = idle + (tdp - idle) * (util ** C("cpu_util_exponent"))
    return cfg.accels_single_wide * p * clamp


def _drive_power(cfg: ServerConfig, sto: float) -> float:
    if cfg.drive_type == "hdd":
        active, idle = C("hdd_active_w"), C("hdd_idle_w")
    else:
        active, idle = C("ssd_active_w"), C("ssd_idle_w")
    return cfg.drives * (idle + (active - idle) * sto)


def _airflow_kgps(cfg: ServerConfig, env: Environment, rpm_pct: float,
                  alive_fans: int, fouling: float) -> tuple[float, float]:
    """(mass flow kg/s, volumetric CFM) at the current fan state.

    Fouling folds into the resistance penalty: a dirty filter means the
    same rpm delivers less air, so the controller must buy the deficit
    back at the cubic power price."""
    penalty = min(0.05, cfg.drives * C("drive_airflow_penalty"))
    penalty += fouling
    cfm = C("fan_cfm") * alive_fans * (rpm_pct / 100.0) * max(0.0, 1.0 - penalty)
    density = C("air_density_sl") * (
        1.0 - C("altitude_density_per_km") * env.altitude_m / 1000.0
    )
    m_dot = max(cfm, 1.0) * C("cfm_to_m3s") * density  # floor avoids div-by-0
    return m_dot, cfm


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    env = scenario.environment.model_copy()
    wl: Workload = scenario.workload.model_copy()
    events = sorted(scenario.events, key=lambda e: e.at_s)

    floor = (
        C("fan_floor_accel_pct") if cfg.accels_single_wide else C("fan_floor_pct")
    )
    cp = C("air_cp")
    nominal_v = C("psu_input_nominal_v")

    # Mutable machine state.
    powered_on = True
    alive_fans = int(C("fan_count"))
    dead_fans: set[int] = set()
    alive_psus = cfg.psu_count
    rpm = floor
    cpu_clamp = 1.0
    accel_clamp = 1.0
    boost_left = C("cpu_boost_seconds")
    overtemp_s = 0
    overcurrent_s = 0
    brownout_s = 0
    sag_v_pct = 100.0
    sag_left = 0.0
    # Thermal-mass temperatures start at ambient — which out here can be
    # well below freezing.
    t_cpu = env.inlet_c
    t_accel = env.inlet_c
    t_drive = env.inlet_c

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    peak_dc = peak_ac = 0.0
    throttle_seconds = 0
    shutdown_reason = ""

    steps = int(scenario.duration_s / DT)
    for step in range(steps + 1):
        t = int(step * DT)

        # Apply due events.
        while ei < len(events) and events[ei].at_s <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                wl = ev.workload.model_copy()
                log.append(LogEntry(t=t, severity="info", message="Workload changed"))
            elif ev.action == "kill-fan" and ev.index is not None:
                if ev.index not in dead_fans and len(dead_fans) < int(C("fan_count")):
                    dead_fans.add(ev.index)
                    alive_fans -= 1
                    log.append(LogEntry(
                        t=t, severity="warning",
                        message=f"Fan {ev.index + 1} failed — survivors ramping",
                    ))
            elif ev.action == "restore-fan" and ev.index is not None:
                if ev.index in dead_fans:
                    dead_fans.discard(ev.index)
                    alive_fans += 1
                    log.append(LogEntry(t=t, severity="info",
                                        message=f"Fan {ev.index + 1} replaced"))
            elif ev.action == "kill-psu":
                if alive_psus > 0:
                    alive_psus -= 1
                    if alive_psus == 0:
                        powered_on = False
                        shutdown_reason = "PSU failure with no redundancy"
                        log.append(LogEntry(t=t, severity="critical",
                                            message="PSU failed — no survivor; power lost"))
                    else:
                        log.append(LogEntry(
                            t=t, severity="warning",
                            message="PSU failed — survivor carrying full load",
                        ))
            elif ev.action == "set-inlet" and ev.value is not None:
                env.inlet_c = ev.value
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Ambient air now {ev.value:g} °C"))
            elif ev.action == "set-filter-months" and ev.value is not None:
                env.filter_months = ev.value
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Filter fouling set to {ev.value:g} months"))
            elif ev.action == "clean-filter":
                env.filter_months = 0
                log.append(LogEntry(t=t, severity="info",
                                    message="Filter changed — airflow restored"))
            elif ev.action == "voltage-sag" and ev.value is not None:
                sag_v_pct = ev.value
                sag_left = ev.seconds if ev.seconds is not None else 10.0
                log.append(LogEntry(
                    t=t, severity="warning",
                    message=f"Feed sagging to {ev.value:g}% of nominal "
                            f"for {sag_left:g} s",
                ))

        # The feed this tick.
        if sag_left > 0:
            v_pct = sag_v_pct
            sag_left -= DT
            if sag_left <= 0:
                sag_v_pct = 100.0
                log.append(LogEntry(t=t, severity="info",
                                    message="Feed voltage recovered"))
        else:
            v_pct = 100.0

        inlet_eff = env.inlet_c
        fouling = fouling_fraction(env)
        sto_lost = storage_perf_lost(cfg, env)

        if powered_on and v_pct < C("brownout_deep_cutoff_pct"):
            powered_on = False
            shutdown_reason = "feed sag beyond ride-through"
            log.append(LogEntry(
                t=t, severity="critical",
                message="Deep sag — below PSU ride-through; power lost",
            ))

        if powered_on:
            # --- Powers -------------------------------------------------
            cpu_util = wl.cpu_pct / 100.0
            boosting = boost_left > 0 and cpu_util >= 0.999
            cpu_w = _cpu_power(cfg, cpu_util, boosting, cpu_clamp)
            if boosting:
                boost_left -= DT
            accel_w = _accel_power(cfg, wl.accel_pct / 100.0, accel_clamp)
            dimm_w = cfg.dimms * (
                C("dimm_idle_w")
                + (C("dimm_active_w") - C("dimm_idle_w")) * wl.mem_pct / 100.0
            )
            drive_w = _drive_power(cfg, wl.storage_pct / 100.0)
            io_w = float(cfg.io_card_w)
            plat_w = C("platform_base_w")
            fan_w = alive_fans * C("fan_pmax_w") * (rpm / 100.0) ** 3
            dc = cpu_w + accel_w + dimm_w + drive_w + io_w + plat_w + fan_w

            active_capacity = alive_psus * cfg.psu_capacity_w
            if cfg.redundancy == "1+1" and alive_psus == 2:
                load_frac = dc / active_capacity
            else:
                load_frac = dc / max(active_capacity, 1)
            eff = psu_efficiency(min(load_frac, 1.2))
            ac = dc / eff

            # The brownout arithmetic: constant power, falling voltage,
            # rising current — shared across the surviving PSUs, against
            # an input limit sized to their rating.
            input_v = nominal_v * v_pct / 100.0
            input_a = ac / input_v
            input_limit = (
                alive_psus * cfg.psu_capacity_w / nominal_v
                * C("psu_input_margin")
            )
            if input_a > input_limit:
                brownout_s += DT
                if brownout_s >= C("brownout_trip_seconds"):
                    powered_on = False
                    shutdown_reason = "input overcurrent during brownout"
                    log.append(LogEntry(
                        t=t, severity="critical",
                        message="Brownout: input current over the PSU limit — tripped",
                    ))
            else:
                brownout_s = 0

            # DC-side overcurrent trip: the surviving budget is one PSU in
            # 1+1, all PSUs otherwise.
            trip_budget = (
                cfg.psu_capacity_w if cfg.redundancy == "1+1"
                else alive_psus * cfg.psu_capacity_w
            )
            if dc > C("psu_overcurrent_trip_fraction") * trip_budget:
                overcurrent_s += DT
                if overcurrent_s >= C("psu_overcurrent_trip_seconds"):
                    powered_on = False
                    shutdown_reason = "PSU overcurrent trip"
                    log.append(LogEntry(
                        t=t, severity="critical",
                        message="Sustained overcurrent — PSU tripped, sled hard-off",
                    ))
            else:
                overcurrent_s = 0

            # --- Airflow & zone temperatures -----------------------------
            m_dot, cfm = _airflow_kgps(cfg, env, rpm, alive_fans, fouling)
            # Front zone: filter, then drives, heat the intake air first.
            front_out = inlet_eff + drive_w / (m_dot * cp)
            # Lane split after the fan wall.
            m_a = m_dot * C("lane_a_share")
            m_b = m_dot * (1.0 - C("lane_a_share"))
            lane_a_out = front_out + (cpu_w + dimm_w) / (m_a * cp)
            lane_b_out = front_out + (accel_w + io_w) / (m_b * cp)
            # Whole-box heat balance: everything electrical becomes heat.
            exhaust = inlet_eff + dc / (m_dot * cp)

            # Component steady-states, approached with first-order lag.
            # The socket inhales at its lane's exit — in a short-depth
            # sled the DIMM bank is immediately upstream of it, so the
            # CPU sees the lane's full preheat (the airflow reality the
            # short chassis makes stark).
            t_cpu_ss = lane_a_out + cpu_w * C("cpu_r_th")
            n_accel = cfg.accels_single_wide
            t_accel_ss = (
                lane_b_out + (accel_w / max(n_accel, 1)) * C("accel_r_th")
                if n_accel else lane_b_out
            )
            t_drive_ss = inlet_eff + 8.0 + 10.0 * (wl.storage_pct / 100.0)

            t_cpu += (t_cpu_ss - t_cpu) * DT / C("cpu_tau")
            t_accel += (t_accel_ss - t_accel) * DT / C("accel_tau")
            t_drive += (t_drive_ss - t_drive) * DT / C("drive_tau")

            # --- Fan controller (proportional) ----------------------------
            err = t_cpu - C("cpu_target_c")
            if n_accel:
                err = max(err, t_accel - C("accel_target_c"))
            rpm = max(floor, min(100.0, rpm + C("fan_kp") * err))

            # --- Protective behaviors -------------------------------------
            was_throttling = cpu_clamp < 1.0
            if t_cpu > C("cpu_throttle_c"):
                cpu_clamp = max(0.1, cpu_clamp - 0.10)
                if not was_throttling:
                    log.append(LogEntry(t=t, severity="warning",
                                        message="CPU throttling engaged"))
            elif cpu_clamp < 1.0 and t_cpu < C("cpu_throttle_c") - 4:
                cpu_clamp = min(1.0, cpu_clamp + 0.05)
                if cpu_clamp >= 1.0:
                    log.append(LogEntry(t=t, severity="info",
                                        message="CPU throttling released"))
            if n_accel and t_accel > C("accel_throttle_c"):
                if accel_clamp >= 1.0:
                    log.append(LogEntry(t=t, severity="warning",
                                        message="Accelerator throttling engaged"))
                accel_clamp = max(0.1, accel_clamp - 0.10)
            elif accel_clamp < 1.0 and t_accel < C("accel_throttle_c") - 4:
                accel_clamp = min(1.0, accel_clamp + 0.05)

            if t_cpu >= C("cpu_shutdown_c"):
                overtemp_s += DT
                if overtemp_s >= C("shutdown_sustain_seconds"):
                    powered_on = False
                    shutdown_reason = "critical CPU overtemperature"
                    log.append(LogEntry(
                        t=t, severity="critical",
                        message="Critical CPU overtemp — emergency power-off",
                    ))
            else:
                overtemp_s = 0
            if inlet_eff >= C("inlet_shutdown_c") and powered_on:
                powered_on = False
                shutdown_reason = "ambient air over limit"
                log.append(LogEntry(
                    t=t, severity="critical",
                    message="Ambient over limit — emergency power-off",
                ))
        else:
            # Dark sled: no powers, temperatures decay toward ambient.
            cpu_w = accel_w = dimm_w = drive_w = io_w = plat_w = fan_w = 0.0
            dc = ac = 0.0
            eff = 0.0
            load_frac = 0.0
            cfm = 0.0
            input_a = 0.0
            front_out = lane_b_out = inlet_eff
            exhaust = inlet_eff
            t_cpu += (inlet_eff - t_cpu) * DT / C("cpu_tau")
            t_accel += (inlet_eff - t_accel) * DT / C("accel_tau")
            t_drive += (inlet_eff - t_drive) * DT / C("drive_tau")
            rpm = 0.0

        cpu_throttling = cpu_clamp < 1.0
        if cpu_throttling or accel_clamp < 1.0:
            throttle_seconds += 1
        peak_dc = max(peak_dc, dc)
        peak_ac = max(peak_ac, ac)

        # Region temperatures for the chassis coloring (ids from anatomy.py).
        fan_air = inlet_eff + 1.0 if powered_on else inlet_eff
        region_temps = {
            "filter": round(inlet_eff, 1),
            "backplane": round(t_drive, 1),
            **{f"fan-{i}": round(inlet_eff if i in dead_fans else fan_air, 1)
               for i in range(int(C("fan_count")))},
            "dimm-a": round(t_cpu - 25 if powered_on else inlet_eff, 1),
            "cpu1": round(t_cpu, 1),
            "dimm-b": round(t_cpu - 25 if powered_on else inlet_eff, 1),
            "accel-riser": round(t_accel, 1),
            "ocp": round(lane_b_out, 1),
            "bmc": round(front_out + 6 if powered_on else inlet_eff, 1),
            "psu-a": round(exhaust, 1),
            "psu-b": round(exhaust if cfg.psu_count == 2 else inlet_eff, 1),
        }

        trace.append(SimState(
            t=t,
            powered_on=powered_on,
            cpu_power_w=round(cpu_w, 1),
            accel_power_w=round(accel_w, 1),
            dimm_power_w=round(dimm_w, 1),
            drive_power_w=round(drive_w, 1),
            io_power_w=round(io_w, 1),
            platform_power_w=round(plat_w, 1),
            fan_power_w=round(fan_w, 1),
            dc_power_w=round(dc, 1),
            ac_power_w=round(ac, 1),
            psu_efficiency=round(eff, 4),
            psu_load_pct=round(100 * load_frac, 1),
            alive_psus=alive_psus,
            input_v_pct=round(v_pct, 1),
            input_current_a=round(input_a, 2),
            fan_rpm_pct=round(rpm, 1),
            alive_fans=alive_fans,
            airflow_cfm=round(cfm, 1),
            fouling_pct=round(100 * fouling, 1),
            inlet_effective_c=round(inlet_eff, 2),
            cpu_temp_c=round(t_cpu, 2),
            accel_temp_c=round(t_accel, 2),
            drive_temp_c=round(t_drive, 2),
            exhaust_c=round(exhaust, 2),
            delta_t_c=round(exhaust - inlet_eff, 2),
            cpu_throttling=cpu_throttling,
            accel_throttling=accel_clamp < 1.0,
            perf_lost_pct=round(100 * (1 - cpu_clamp), 0),
            storage_perf_lost_pct=round(sto_lost, 0),
            region_temps=region_temps,
        ))

    last = trace[-1]
    summary = Summary(
        peak_dc_w=round(peak_dc, 1),
        peak_ac_w=round(peak_ac, 1),
        steady_dc_w=last.dc_power_w,
        steady_cpu_temp_c=last.cpu_temp_c,
        throttle_seconds=throttle_seconds,
        shutdown=not last.powered_on,
        shutdown_reason=shutdown_reason,
    )
    return trace, log, summary
