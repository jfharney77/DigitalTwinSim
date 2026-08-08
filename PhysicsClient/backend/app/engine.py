"""Pure physics engine for the client-device simulator (physics_specs/07).

``simulate(scenario)`` returns the deterministic timestepped trace of the
configured Alienware or Pro Max Plus under workload, environment, and
timed events. Same purity rule as every twin: no FastAPI, no IO, no
timers, no randomness — the frontend owns the playback clock.

The identities and mechanics this app exists to teach, all asserted in
``tests/test_engine.py``:

* **Power balance, every tick**: component powers sum to the system
  total, and supply balances demand — adapter DC + battery discharge =
  system power + charge power (the Alienware twin's energy identity,
  carried into the physics suite).
* **PL2 → PL1 burst-then-fade**: on a load step the CPU runs at the burst
  limit for a boost window (τ ≈ 28 s), then settles to the sustained
  limit — the shape that defines laptop benchmarks.
* **The shared thermal budget**: laptop CPU, GPU, and NPU share heat
  pipes; when their demands exceed what the chassis can dissipate, the
  allocator favors the GPU (game-load logic) and clips the CPU.
* **The skin cap**: unlike servers, the chassis touches humans — a slow
  skin zone with a hard cap that overrides fan logic and forces power
  limits down.
* **The battery is just arithmetic**: runtime = Wh × η ÷ W; an
  undersized charger under full load drains the battery while plugged in.
"""

from __future__ import annotations

from .constants import PSU_EFFICIENCY_CURVE, value as C
from .models import (
    DeviceConfig,
    Environment,
    LogEntry,
    PlState,
    Scenario,
    SimState,
    Summary,
    Workload,
)

DT = 1.0  # sim timestep, seconds

CPU_FLOOR_W = 8.0  # the allocator never starves the CPU below this


def psu_efficiency(load_fraction: float) -> float:
    """Piecewise-linear interpolation over the desktop PSU curve."""
    pts = PSU_EFFICIENCY_CURVE
    if load_fraction <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if load_fraction <= x1:
            f = (load_fraction - x0) / (x1 - x0)
            return y0 + f * (y1 - y0)
    return pts[-1][1]


def thermal_budget_w(cfg: DeviceConfig, env: Environment) -> float:
    """Sustained heat the chassis can dissipate — the laptop's shared
    ceiling. Desktops have separate towers of fin per component; modeled
    as unbounded (their limits are the PSU and per-part throttle)."""
    if cfg.form_factor == "desktop":
        return 10_000.0
    budget = C("budget_laptop_base_w") + C("budget_per_gpu_tier_w") * cfg.gpu_tgp_w
    if env.perf_mode == "quiet":
        budget *= C("budget_quiet_factor")
    elif env.perf_mode == "performance":
        budget *= C("budget_perf_factor")
    if env.on_lap:
        budget *= C("on_lap_budget_factor")
    return budget


def _demand(idle: float, full: float, util: float) -> float:
    return idle + (full - idle) * (util ** C("cpu_util_exponent"))


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    env = scenario.environment.model_copy()
    wl: Workload = scenario.workload.model_copy()
    events = sorted(scenario.events, key=lambda e: e.at_s)
    laptop = cfg.form_factor == "laptop"

    pl1 = float(cfg.cpu_pl1_w)
    pl2 = pl1 * C("pl2_multiplier")
    tgp = float(cfg.gpu_tgp_w)
    npu_max = C("npu_max_w") if cfg.npu else 0.0
    fan_n = int(C("fan_count_laptop") if laptop else C("fan_count_desktop"))
    fan_pmax = C("fan_pmax_laptop_w") if laptop else C("fan_pmax_desktop_w")
    base_w = (
        (C("base_laptop_w") if laptop else C("base_desktop_w"))
        + C("ram_w_per_16gb") * cfg.ram_gb / 16.0
        + C("nvme_w_each") * cfg.nvme_count
    )
    capacity_wh = cfg.battery_wh * cfg.battery_health_pct / 100.0

    # Mutable machine state.
    powered_on = True
    plugged = env.plugged_in
    charger_w = float(cfg.charger_w)
    energy_wh = capacity_wh * env.start_charge_pct / 100.0 if laptop else 0.0
    boost_left = C("pl2_tau_s")  # a cold start is itself a load step
    skin_clamp = 1.0
    cpu_clamp = 1.0
    gpu_clamp = 1.0
    rpm = C("fan_floor_pct")
    overcurrent_s = 0.0
    t_cpu = env.ambient_c
    t_gpu = env.ambient_c
    t_skin = env.ambient_c
    shutdown_reason = ""

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    peak_sys = 0.0
    min_batt = 100.0
    throttle_seconds = 0

    steps = int(scenario.duration_s / DT)
    for step in range(steps + 1):
        t = int(step * DT)

        # Apply due events.
        while ei < len(events) and events[ei].at_s <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                if ev.workload.cpu_pct > wl.cpu_pct or ev.workload.gpu_pct > wl.gpu_pct:
                    boost_left = C("pl2_tau_s")  # a load step re-arms PL2
                wl = ev.workload.model_copy()
                log.append(LogEntry(t=t, severity="info", message="Workload changed"))
            elif ev.action == "unplug":
                if plugged:
                    plugged = False
                    log.append(LogEntry(t=t, severity="warning",
                                        message="Unplugged — running on battery"))
            elif ev.action == "plug-in":
                if not plugged:
                    plugged = True
                    log.append(LogEntry(t=t, severity="info",
                                        message="Charger connected"))
            elif ev.action == "set-ambient" and ev.value is not None:
                env.ambient_c = ev.value
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Ambient set to {ev.value:g} °C"))
            elif ev.action == "set-on-lap" and ev.value is not None:
                env.on_lap = ev.value >= 1
                log.append(LogEntry(
                    t=t, severity="warning" if env.on_lap else "info",
                    message="Moved onto a lap — bottom intake blocked"
                    if env.on_lap else "Back on the desk",
                ))
            elif ev.action == "set-mode" and ev.mode is not None:
                env.perf_mode = ev.mode
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Performance mode: {ev.mode}"))
            elif ev.action == "set-charger" and ev.value is not None:
                charger_w = ev.value
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Charger swapped: {ev.value:g} W"))

        if powered_on:
            # --- Demands under the current power limits -------------------
            cpu_util = wl.cpu_pct / 100.0
            gpu_util = wl.gpu_pct / 100.0 if tgp else 0.0
            npu_util = wl.npu_pct / 100.0 if npu_max else 0.0

            boosting = boost_left > 0 and (cpu_util >= 0.6 or gpu_util >= 0.6)
            pl_limit = (pl2 if boosting else pl1) * skin_clamp * cpu_clamp
            if boosting:
                boost_left -= DT
            cpu_idle = C("cpu_idle_fraction") * pl1
            cpu_demand = min(_demand(cpu_idle, pl2, cpu_util), max(pl_limit, cpu_idle))
            gpu_idle = C("gpu_idle_fraction") * tgp
            gpu_full = tgp * (C("gpu_boost_multiplier") if boosting else 1.0)
            gpu_demand = _demand(gpu_idle, gpu_full, gpu_util) * gpu_clamp * skin_clamp if tgp else 0.0
            npu_demand = (
                C("npu_idle_w") + (npu_max - C("npu_idle_w")) * npu_util
                if npu_max else 0.0
            )

            # --- Shared thermal budget allocator (laptop lesson) ----------
            budget = thermal_budget_w(cfg, env)
            budget_limited = False
            if cpu_demand + gpu_demand + npu_demand > budget:
                budget_limited = True
                npu_w = min(npu_demand, budget)
                remaining = budget - npu_w
                # Dynamic power shift favors the GPU under game load: it
                # takes what it asked for, up to all but the CPU's floor.
                gpu_w = min(gpu_demand, max(0.0, remaining - CPU_FLOOR_W))
                cpu_w = max(min(CPU_FLOOR_W, cpu_demand), remaining - gpu_w)
                cpu_w = min(cpu_w, cpu_demand)
            else:
                cpu_w, gpu_w, npu_w = cpu_demand, gpu_demand, npu_demand

            fan_w = fan_n * fan_pmax * (rpm / 100.0) ** 3
            system_w = cpu_w + gpu_w + npu_w + base_w + fan_w

            # --- Supply side ---------------------------------------------
            charge_w = 0.0
            batt_out = 0.0
            adapter_dc = 0.0
            eff = 1.0
            if laptop:
                if plugged:
                    if system_w <= charger_w:
                        adapter_dc = system_w
                        surplus = charger_w - system_w
                        if energy_wh < capacity_wh:
                            pct = 100.0 * energy_wh / capacity_wh
                            taper = 1.0
                            if pct > C("charge_taper_pct"):
                                taper = max(
                                    0.0,
                                    (100.0 - pct) / (100.0 - C("charge_taper_pct")),
                                )
                            charge_w = min(surplus, C("charge_rate_max_w") * taper)
                            adapter_dc += charge_w
                    else:
                        # Undersized charger: the pack covers the deficit
                        # even though the machine is plugged in.
                        adapter_dc = charger_w
                        batt_out = system_w - charger_w
                else:
                    batt_out = system_w
                eff = C("charger_efficiency") if adapter_dc > 0 else 1.0
                ac_w = adapter_dc / eff if adapter_dc > 0 else 0.0
                # Battery bookkeeping.
                if batt_out > 0:
                    energy_wh -= (batt_out / C("discharge_efficiency")) * DT / 3600.0
                if charge_w > 0:
                    energy_wh = min(capacity_wh, energy_wh + charge_w * DT / 3600.0)
                energy_wh = max(0.0, energy_wh)
            else:
                load_frac = system_w / max(cfg.psu_capacity_w, 1)
                eff = psu_efficiency(min(load_frac, 1.2))
                ac_w = system_w / eff
                adapter_dc = system_w
                if system_w > C("psu_trip_fraction") * cfg.psu_capacity_w:
                    overcurrent_s += DT
                    if overcurrent_s >= C("psu_trip_seconds"):
                        powered_on = False
                        shutdown_reason = "PSU overcurrent trip"
                        log.append(LogEntry(
                            t=t, severity="critical",
                            message="Sustained overcurrent — PSU tripped, tower hard-off",
                        ))
                else:
                    overcurrent_s = 0.0

            # --- Thermals -------------------------------------------------
            # Extra internal heat: charge inefficiency + worn-pack IR loss.
            extra_heat = charge_w * C("charge_heat_fraction")
            if batt_out > 0 and cfg.battery_health_pct < 100:
                wear = (100 - cfg.battery_health_pct) / 20.0
                extra_heat += C("battery_health_r_heat_w") * wear * (
                    batt_out / max(system_w, 1.0)
                )
            internal_heat = system_w + extra_heat

            cool = 0.35 + 0.65 * (rpm / 100.0)          # airflow factor
            preheat = 6.0 if (env.on_lap and laptop) else 0.0
            r_cpu = C("cpu_r_th") if laptop else C("cpu_r_th_desktop")
            r_gpu = C("gpu_r_th") if laptop else C("gpu_r_th_desktop")
            t_cpu_ss = env.ambient_c + preheat + cpu_w * r_cpu / cool
            t_gpu_ss = (
                env.ambient_c + preheat + gpu_w * r_gpu / cool
                if tgp else env.ambient_c
            )
            lap_block = 1.0 - (0.45 if (env.on_lap and laptop) else 0.0)
            r_skin = C("skin_r_th") if laptop else C("skin_r_th_desktop")
            t_skin_ss = env.ambient_c + internal_heat * r_skin / lap_block

            t_cpu += (t_cpu_ss - t_cpu) * DT / C("cpu_tau")
            t_gpu += (t_gpu_ss - t_gpu) * DT / C("gpu_tau")
            t_skin += (t_skin_ss - t_skin) * DT / C("skin_tau")

            # --- Fan controller (with the quiet-mode cap) -----------------
            err = t_cpu - C("cpu_target_c")
            if tgp:
                err = max(err, t_gpu - C("gpu_target_c"))
            ceiling = (
                C("quiet_fan_cap_pct")
                if (env.perf_mode == "quiet" and laptop) else 100.0
            )
            rpm = max(C("fan_floor_pct"), min(ceiling, rpm + C("fan_kp") * err))
            noise = C("noise_floor_dba") + C("noise_span_dba") * (rpm / 100.0) ** 2

            # --- Skin governor (overrides everything, spec 07) ------------
            was_skin = skin_clamp < 1.0
            if laptop and t_skin > C("skin_cap_c"):
                skin_clamp = max(0.3, skin_clamp - 0.02)
                if not was_skin:
                    log.append(LogEntry(
                        t=t, severity="warning",
                        message="Skin over the contact cap — power limits reduced",
                    ))
            elif skin_clamp < 1.0 and t_skin < C("skin_cap_c") - 1.5:
                skin_clamp = min(1.0, skin_clamp + 0.01)

            # --- Silicon throttle -----------------------------------------
            if t_cpu > C("cpu_throttle_c"):
                if cpu_clamp >= 1.0:
                    log.append(LogEntry(t=t, severity="warning",
                                        message="CPU throttling engaged"))
                cpu_clamp = max(0.2, cpu_clamp - 0.10)
            elif cpu_clamp < 1.0 and t_cpu < C("cpu_throttle_c") - 4:
                cpu_clamp = min(1.0, cpu_clamp + 0.05)
            if tgp and t_gpu > C("gpu_throttle_c"):
                if gpu_clamp >= 1.0:
                    log.append(LogEntry(t=t, severity="warning",
                                        message="GPU throttling engaged"))
                gpu_clamp = max(0.2, gpu_clamp - 0.10)
            elif gpu_clamp < 1.0 and t_gpu < C("gpu_throttle_c") - 4:
                gpu_clamp = min(1.0, gpu_clamp + 0.05)

            # --- Battery shutdown -----------------------------------------
            batt_pct = 100.0 * energy_wh / capacity_wh if laptop else 100.0
            if laptop and not plugged and batt_pct <= C("battery_shutdown_pct"):
                powered_on = False
                shutdown_reason = "battery exhausted"
                log.append(LogEntry(t=t, severity="critical",
                                    message="Battery exhausted — emergency power-off"))
        else:
            cpu_w = gpu_w = npu_w = fan_w = 0.0
            system_w = ac_w = adapter_dc = charge_w = batt_out = 0.0
            eff = 1.0
            noise = 0.0
            rpm = 0.0
            budget_limited = False
            boosting = False
            t_cpu += (env.ambient_c - t_cpu) * DT / C("cpu_tau")
            t_gpu += (env.ambient_c - t_gpu) * DT / C("gpu_tau")
            t_skin += (env.ambient_c - t_skin) * DT / C("skin_tau")
            batt_pct = 100.0 * energy_wh / capacity_wh if laptop else 100.0

        # --- Derived readouts --------------------------------------------
        if not powered_on:
            pl_state: PlState = "idle"
        elif skin_clamp < 1.0:
            pl_state = "skin-limited"
        elif budget_limited:
            pl_state = "budget-limited"
        elif boosting and wl.cpu_pct >= 60:
            pl_state = "pl2-boost"
        elif wl.cpu_pct < 5 and wl.gpu_pct < 5 and wl.npu_pct < 5:
            pl_state = "idle"
        else:
            pl_state = "pl1"

        cpu_throttling = cpu_clamp < 1.0
        gpu_throttling = gpu_clamp < 1.0
        if powered_on and (cpu_throttling or gpu_throttling or skin_clamp < 1.0):
            throttle_seconds += 1

        fps = (
            C("fps_ref") * ((gpu_w / tgp) ** C("fps_exponent"))
            if (powered_on and tgp and wl.gpu_pct > 0) else 0.0
        )
        active = None
        tokps = tokpj = 0.0
        if powered_on:
            if npu_max and wl.npu_pct > 0:
                active, rate, p = "npu", C("tokps_npu"), npu_w
                full = npu_max
            elif tgp and wl.gpu_pct > 0:
                active, rate, p = "gpu", C("tokps_gpu"), gpu_w
                full = tgp
            elif wl.cpu_pct > 0:
                active, rate, p = "cpu", C("tokps_cpu"), cpu_w
                full = pl1
            else:
                rate = p = full = 0.0
            if active and full > 0:
                tokps = rate * min(1.0, p / full)
                tokpj = tokps / p if p > 0 else 0.0

        runtime_min = (
            (energy_wh * C("discharge_efficiency") / batt_out) * 60.0
            if (laptop and batt_out > 1e-6) else 0.0
        )
        peak_sys = max(peak_sys, system_w)
        if laptop:
            min_batt = min(min_batt, batt_pct)

        # Region temperatures for the device map (ids in anatomy.py).
        off = not powered_on
        amb = env.ambient_c
        common = {
            "cpu": round(t_cpu, 1),
            "gpu": round(t_gpu if tgp else amb, 1),
            "dimm": round(amb if off else t_cpu - 20, 1),
            "nvme": round(amb if off else amb + 12, 1),
            "board": round(amb if off else amb + 10, 1),
            "skin": round(t_skin, 1),
        }
        if laptop:
            region_temps = {
                **common,
                "fan-0": round(amb if off else amb + 4, 1),
                "fan-1": round(amb if off else amb + 4, 1),
                "battery": round(
                    amb if off else amb + 6 + (4 if charge_w > 0 else 0), 1
                ),
            }
            if cfg.product == "promax":
                region_temps["npu"] = round(
                    amb if (off or not cfg.npu) else amb + 8 + npu_w * 0.5, 1
                )
        else:
            region_temps = {
                **common,
                **{f"fan-{i}": round(amb if off else amb + 3, 1) for i in range(4)},
                "psu": round(amb if off else amb + 15, 1),
            }

        trace.append(SimState(
            t=t,
            powered_on=powered_on,
            cpu_power_w=round(cpu_w, 1),
            gpu_power_w=round(gpu_w, 1),
            npu_power_w=round(npu_w, 1),
            base_power_w=round(base_w if powered_on else 0.0, 1),
            fan_power_w=round(fan_w, 1),
            system_power_w=round(system_w, 1),
            ac_input_w=round(ac_w, 1),
            battery_discharge_w=round(batt_out, 1),
            charge_w=round(charge_w, 1),
            battery_pct=round(batt_pct, 2),
            runtime_min=round(runtime_min, 1),
            psu_efficiency=round(eff, 4),
            pl_state=pl_state,
            cpu_temp_c=round(t_cpu, 2),
            gpu_temp_c=round(t_gpu, 2),
            skin_temp_c=round(t_skin, 2),
            fan_rpm_pct=round(rpm, 1),
            noise_dba=round(noise, 1),
            cpu_throttling=cpu_throttling,
            gpu_throttling=gpu_throttling,
            fps_proxy=round(fps, 1),
            tokens_per_s=round(tokps, 2),
            tokens_per_joule=round(tokpj, 4),
            active_engine=active,
            region_temps=region_temps,
        ))

    minute = int(60 / DT)
    fps_1 = trace[min(minute, len(trace) - 1)].fps_proxy
    fps_15 = trace[min(15 * minute, len(trace) - 1)].fps_proxy
    last = trace[-1]
    summary = Summary(
        peak_system_w=round(peak_sys, 1),
        steady_system_w=last.system_power_w,
        fps_minute_1=fps_1,
        fps_minute_15=fps_15,
        min_battery_pct=round(min_batt, 1),
        throttle_seconds=throttle_seconds,
        shutdown=not last.powered_on,
        shutdown_reason=shutdown_reason,
    )
    return trace, log, summary
