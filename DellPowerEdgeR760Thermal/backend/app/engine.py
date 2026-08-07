"""Pure physics engine for the R760 power & thermal simulator.

``simulate(scenario)`` returns the deterministic timestepped trace of the
configured server under the given workload, environment, and timed events
— the causal chain the spec exists to teach: configuration → load → power
→ heat → fan response → feedback. Same purity rule as every twin in this
repo: no FastAPI, no IO, no timers, no randomness — the frontend owns the
playback clock, and each ``SimState`` is plain data.

Two identities hold by construction and are asserted in the tests, in the
house style of the Alienware energy identity and the IR7000 heat balance:

* **Power balance, every tick**: the component powers sum exactly to the
  DC total, and wall AC equals DC ÷ efficiency at the load point. The fan
  feedback loop — fans heat the box they cool — is therefore an asserted
  fact, not a UI claim.
* **Heat balance**: all DC power becomes heat, and the exhaust
  temperature is inlet + Q ÷ (ṁ·cp) — the IR7000 twin's identity, seen
  from inside one server. (PSU conversion loss, AC − DC, is vented by the
  PSUs' own rear airflow and deliberately kept outside the front-to-back
  path — the spec's §5.1 simplification, stated honestly.)

The model is simplified and legible on purpose (spec §1): serial thermal
zones, first-order thermal masses, a proportional fan controller. Correct
relationships and orders of magnitude, not CFD.
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


def _cpu_power(cfg: ServerConfig, util: float, boost: bool, clamp: float) -> float:
    """Per spec §4: P = idle + (TDP − idle) × util^1.4, times sockets,
    boosted briefly at full load, clamped by the throttle multiplier."""
    tdp = float(cfg.cpu_tdp_w)
    idle = C("cpu_idle_fraction") * tdp
    p = idle + (tdp - idle) * (util ** C("cpu_util_exponent"))
    if boost and util >= 0.999:
        p = tdp * C("cpu_boost_multiplier")
    return cfg.sockets * p * clamp


def _gpu_power(cfg: ServerConfig, util: float, clamp: float) -> float:
    total = 0.0
    for count, tdp in (
        (cfg.gpus_double_wide, C("gpu_dw_tdp")),
        (cfg.accels_single_wide, C("gpu_sw_tdp")),
    ):
        if count:
            idle = C("gpu_idle_fraction") * tdp
            p = idle + (tdp - idle) * (util ** C("cpu_util_exponent"))
            total += count * p
    return total * clamp


def _drive_power(cfg: ServerConfig, sto: float) -> float:
    active, idle = {
        "12x3.5": (C("hdd_active_w"), C("hdd_idle_w")),
        "24x2.5": (C("ssd_active_w"), C("ssd_idle_w")),
        "16xE3.S": (C("nvme_active_w"), C("nvme_idle_w")),
    }[cfg.chassis]
    return cfg.drives * (idle + (active - idle) * sto)


def _airflow_kgps(cfg: ServerConfig, env: Environment, rpm_pct: float,
                  alive_fans: int) -> tuple[float, float]:
    """(mass flow kg/s, volumetric CFM) at the current fan state."""
    cfm_per = C("fan_cfm_gold") if cfg.fan_kit == "gold" else C("fan_cfm_std")
    penalty = min(0.15, cfg.drives * C("drive_airflow_penalty"))
    if cfg.dimms >= 32:
        penalty += C("dimm_airflow_penalty")
    penalty += env.blocked_intake_pct / 100.0
    cfm = cfm_per * alive_fans * (rpm_pct / 100.0) * max(0.0, 1.0 - penalty)
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

    has_dw_gpu = cfg.gpus_double_wide > 0
    floor = C("fan_floor_gpu_pct") if has_dw_gpu else C("fan_floor_pct")
    r_cpu = (
        C("cpu_r_th_hp") if cfg.heatsink == "high-performance" else C("cpu_r_th_std")
    )
    fan_pmax = C("fan_pmax_gold_w") if cfg.fan_kit == "gold" else C("fan_pmax_std_w")
    cp = C("air_cp")

    # Mutable machine state.
    powered_on = True
    alive_fans = int(C("fan_count"))
    dead_fans: set[int] = set()
    alive_psus = cfg.psu_count
    rpm = floor
    cpu_clamp = 1.0
    gpu_clamp = 1.0
    boost_left = C("cpu_boost_seconds")
    overtemp_s = 0
    overcurrent_s = 0
    exhaust_prev = env.inlet_c
    # Thermal-mass temperatures start at cold ambient.
    t_cpu = env.inlet_c
    t_gpu = env.inlet_c
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
                                    message=f"Inlet air set to {ev.value:g} °C"))
            elif ev.action == "set-recirculation" and ev.value is not None:
                env.recirculation_pct = int(ev.value)
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Recirculation set to {ev.value:g}%"))
            elif ev.action == "set-blocked-intake" and ev.value is not None:
                env.blocked_intake_pct = int(ev.value)
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Intake blockage set to {ev.value:g}%"))

        # Effective inlet: recirculation mixes yesterday's exhaust back in.
        inlet_eff = env.inlet_c + (env.recirculation_pct / 100.0) * (
            exhaust_prev - env.inlet_c
        )

        if powered_on:
            # --- Powers -------------------------------------------------
            cpu_util = wl.cpu_pct / 100.0
            boosting = boost_left > 0 and cpu_util >= 0.999
            cpu_w = _cpu_power(cfg, cpu_util, boosting, cpu_clamp)
            if boosting:
                boost_left -= DT
            gpu_w = _gpu_power(cfg, wl.gpu_pct / 100.0, gpu_clamp)
            dimm_w = cfg.dimms * (
                C("dimm_idle_w")
                + (C("dimm_active_w") - C("dimm_idle_w")) * wl.mem_pct / 100.0
            )
            drive_w = _drive_power(cfg, wl.storage_pct / 100.0)
            io_w = float(cfg.io_card_w)
            plat_w = C("platform_base_w")
            fan_w = alive_fans * fan_pmax * (rpm / 100.0) ** 3
            dc = cpu_w + gpu_w + dimm_w + drive_w + io_w + plat_w + fan_w

            active_capacity = alive_psus * cfg.psu_capacity_w
            if cfg.redundancy == "1+1" and alive_psus == 2:
                # Load shared; efficiency point per PSU at half load.
                load_frac = dc / active_capacity
            else:
                load_frac = dc / max(active_capacity, 1)
            eff = psu_efficiency(min(load_frac, 1.2))
            ac = dc / eff

            # PSU overcurrent trip (spec §3.5): the surviving budget for a
            # trip check is one PSU in 1+1, all PSUs otherwise.
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
                        message="Sustained overcurrent — PSU tripped, server hard-off",
                    ))
            else:
                overcurrent_s = 0

            # --- Airflow & zone temperatures -----------------------------
            m_dot, cfm = _airflow_kgps(cfg, env, rpm, alive_fans)
            # Front zone: drives heat the intake air first.
            front_out = inlet_eff + drive_w / (m_dot * cp)
            # Lane split after the fan wall.
            m_a = m_dot * C("lane_a_share")
            m_b = m_dot * (1.0 - C("lane_a_share"))
            lane_a_out = front_out + (cpu_w + dimm_w) / (m_a * cp)
            lane_b_out = front_out + (gpu_w + io_w) / (m_b * cp)
            # Whole-box heat balance: everything electrical becomes heat.
            exhaust = inlet_eff + dc / (m_dot * cp)

            # Component steady-states, approached with first-order lag.
            cpu_air = (front_out + lane_a_out) / 2.0
            t_cpu_ss = cpu_air + (cpu_w / max(cfg.sockets, 1)) * r_cpu
            gpu_air = (front_out + lane_b_out) / 2.0
            n_gpu = cfg.gpus_double_wide + cfg.accels_single_wide
            t_gpu_ss = gpu_air + (gpu_w / max(n_gpu, 1)) * C("gpu_r_th") if n_gpu else gpu_air
            t_drive_ss = inlet_eff + 8.0 + 10.0 * (wl.storage_pct / 100.0)

            t_cpu += (t_cpu_ss - t_cpu) * DT / C("cpu_tau")
            t_gpu += (t_gpu_ss - t_gpu) * DT / C("gpu_tau")
            t_drive += (t_drive_ss - t_drive) * DT / C("drive_tau")

            # --- Fan controller (proportional, spec §5.3) ----------------
            err = t_cpu - C("cpu_target_c")
            if n_gpu:
                err = max(err, t_gpu - C("gpu_target_c"))
            rpm = max(floor, min(100.0, rpm + C("fan_kp") * err))

            # --- Protective behaviors (spec §5.5) ------------------------
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
            if n_gpu and t_gpu > C("gpu_throttle_c"):
                if gpu_clamp >= 1.0:
                    log.append(LogEntry(t=t, severity="warning",
                                        message="GPU throttling engaged"))
                gpu_clamp = max(0.1, gpu_clamp - 0.10)
            elif gpu_clamp < 1.0 and t_gpu < C("gpu_throttle_c") - 4:
                gpu_clamp = min(1.0, gpu_clamp + 0.05)

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
                shutdown_reason = "inlet air over limit"
                log.append(LogEntry(
                    t=t, severity="critical",
                    message="Inlet air over limit — emergency power-off",
                ))

            exhaust_prev = exhaust
        else:
            # Dark server: no powers, temperatures decay toward ambient.
            cpu_w = gpu_w = dimm_w = drive_w = io_w = plat_w = fan_w = 0.0
            dc = ac = 0.0
            eff = 0.0
            load_frac = 0.0
            cfm = 0.0
            front_out = lane_b_out = inlet_eff
            exhaust = inlet_eff
            t_cpu += (inlet_eff - t_cpu) * DT / C("cpu_tau")
            t_gpu += (inlet_eff - t_gpu) * DT / C("gpu_tau")
            t_drive += (inlet_eff - t_drive) * DT / C("drive_tau")
            rpm = 0.0
            exhaust_prev = inlet_eff

        cpu_throttling = cpu_clamp < 1.0
        if cpu_throttling or gpu_clamp < 1.0:
            throttle_seconds += 1
        peak_dc = max(peak_dc, dc)
        peak_ac = max(peak_ac, ac)

        # Region temperatures for the chassis coloring (ids from anatomy.py).
        fan_air = inlet_eff + 1.0 if powered_on else inlet_eff
        region_temps = {
            "backplane": round(t_drive, 1),
            **{f"fan-{i}": round(inlet_eff if i in dead_fans else fan_air, 1)
               for i in range(int(C("fan_count")))},
            "dimm-a": round(t_cpu - 25 if powered_on else inlet_eff, 1),
            "cpu1": round(t_cpu, 1),
            "cpu2": round(t_cpu if cfg.sockets == 2 else inlet_eff, 1),
            "dimm-b": round(
                (t_cpu - 25 if cfg.sockets == 2 else inlet_eff)
                if powered_on else inlet_eff, 1,
            ),
            "gpu-riser": round(t_gpu, 1),
            "ocp": round(lane_b_out, 1),
            "idrac": round(front_out + 6 if powered_on else inlet_eff, 1),
            "psu-a": round(exhaust, 1),
            "psu-b": round(exhaust if cfg.psu_count == 2 else inlet_eff, 1),
        }

        trace.append(SimState(
            t=t,
            powered_on=powered_on,
            cpu_power_w=round(cpu_w, 1),
            gpu_power_w=round(gpu_w, 1),
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
            fan_rpm_pct=round(rpm, 1),
            alive_fans=alive_fans,
            airflow_cfm=round(cfm, 1),
            inlet_effective_c=round(inlet_eff, 2),
            cpu_temp_c=round(t_cpu, 2),
            gpu_temp_c=round(t_gpu, 2),
            drive_temp_c=round(t_drive, 2),
            exhaust_c=round(exhaust, 2),
            delta_t_c=round(exhaust - inlet_eff, 2),
            cpu_throttling=cpu_throttling,
            gpu_throttling=gpu_clamp < 1.0,
            perf_lost_pct=round(100 * (1 - cpu_clamp), 0),
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
