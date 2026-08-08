"""Pure physics engine for the AI-compute simulator (physics_specs/01).

One engine, three personalities:

* **XE7745** tracks a per-slot GPU temperature vector — each riser
  position inhales air the previous positions have warmed, so the worst
  slot throttles first (positional thermal inequality).
* **XE9680** treats the HGX baseboard as one thermal zone with shared
  fate: all eight GPUs throttle together. Its distinctive dial is
  ``data_feed_pct`` — a starved GPU still burns most of its power while
  producing few tokens.
* **XE9712** swaps the fan wall for a liquid loop: the heat split
  identity (liquid + air = DC, exactly) and ΔT = Q/(ṁ·cp) with water's
  cp are the spec's core physics; pump degradation, CDU supply
  excursions, and per-tray restrictions are timed events.

Purity rule as everywhere: no FastAPI, no IO, no timers, no randomness.
"""

from __future__ import annotations

from .constants import PSU_EFFICIENCY_CURVE, value as C
from .models import (
    Environment,
    LogEntry,
    Scenario,
    SimState,
    Summary,
    SystemConfig,
    Workload,
)

DT = 1.0

PSU_COUNT = {"xe7745": 4, "xe9680": 6}


def psu_efficiency(load_fraction: float) -> float:
    pts = PSU_EFFICIENCY_CURVE
    if load_fraction <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if load_fraction <= x1:
            f = (load_fraction - x0) / (x1 - x0)
            return y0 + f * (y1 - y0)
    return pts[-1][1]


def gpu_count(cfg: SystemConfig) -> int:
    if cfg.product == "xe7745":
        return cfg.pcie_gpus
    if cfg.product == "xe9680":
        return 8
    return cfg.trays * 4


def gpu_tdp(cfg: SystemConfig) -> float:
    if cfg.product == "xe7745":
        return float(cfg.pcie_gpu_tdp_w)
    if cfg.product == "xe9680":
        # Per-GPU share of the HGX baseboard's own draw rides along.
        return float(cfg.sxm_gpu_tdp_w) + C("hgx_board_per_gpu_w")
    return C("tray_gpu_w")


def max_dc_w(cfg: SystemConfig) -> float:
    """Worst-case draw, for the validation rules."""
    n = gpu_count(cfg)
    if cfg.product == "xe9712":
        it = (
            cfg.trays * (4 * C("tray_gpu_w") + 2 * C("tray_cpu_w") + C("tray_base_w"))
            + C("nvswitch_trays") * C("nvswitch_tray_w")
        )
        return it + C("pump_w_max")
    fans = (
        C("fan_count_7745") if cfg.product == "xe7745" else C("fan_count_9680")
    ) * C("fan_pmax_w")
    nics = (cfg.nics if cfg.product == "xe9680" else 2) * C("nic_w")
    return (
        n * gpu_tdp(cfg)
        + 2 * cfg.cpu_tdp_w
        + nics
        + C("dimm_bank_w")
        + C("base_w")
        + fans
    )


def _demand(idle_frac: float, full: float, util: float) -> float:
    idle = idle_frac * full
    return idle + (full - idle) * (util ** C("util_exponent"))


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    env: Environment = scenario.environment.model_copy()
    wl: Workload = scenario.workload.model_copy()
    events = sorted(scenario.events, key=lambda e: e.at_s)

    product = cfg.product
    liquid = product == "xe9712"
    n_gpu = gpu_count(cfg)
    tdp = gpu_tdp(cfg)
    n_cpu = cfg.trays * 2 if liquid else 2
    cpu_tdp = C("tray_cpu_w") if liquid else float(cfg.cpu_tdp_w)
    fan_n = 0 if liquid else int(
        C("fan_count_7745") if product == "xe7745" else C("fan_count_9680")
    )
    nic_n = cfg.nics if product == "xe9680" else (0 if liquid else 2)
    base_w = (
        cfg.trays * C("tray_base_w") + C("nvswitch_trays") * C("nvswitch_tray_w")
        if liquid else C("dimm_bank_w") + C("base_w")
    )

    # Thermal positions: XE7745 = one per riser slot; XE9680 = one shared
    # zone; XE9712 = one per tray.
    n_pos = n_gpu if product == "xe7745" else (1 if product == "xe9680" else cfg.trays)

    powered_on = True
    alive_psus = PSU_COUNT.get(product, 0)
    rpm = C("fan_floor_pct")
    clamps = [1.0] * max(n_pos, 1)
    t_gpu = [env.inlet_c] * max(n_pos, 1)
    t_cpu = env.inlet_c
    coolant_supply = cfg.coolant_supply_c
    coolant_return = coolant_supply
    flow_lpm = float(cfg.coolant_flow_lpm)
    pump_degrade = 0.0
    restricted: set[int] = set()
    overcurrent_s = 0.0
    wasted_gpu_hours = 0.0
    shutdown_reason = ""

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    peak_dc = 0.0
    peak_tokens = 0.0
    idle_dc = 0.0
    throttle_seconds = 0

    steps = int(scenario.duration_s / DT)
    for step in range(steps + 1):
        t = int(step * DT)

        while ei < len(events) and events[ei].at_s <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                wl = ev.workload.model_copy()
                log.append(LogEntry(t=t, severity="info", message="Workload changed"))
            elif ev.action == "set-inlet" and ev.value is not None:
                env.inlet_c = ev.value
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Inlet air set to {ev.value:g} °C"))
            elif ev.action == "set-data-feed" and ev.value is not None:
                wl.data_feed_pct = int(ev.value)
                log.append(LogEntry(
                    t=t, severity="warning" if ev.value < 60 else "info",
                    message=f"Data pipeline delivering {ev.value:g}% of demand",
                ))
            elif ev.action == "set-coolant-supply" and ev.value is not None:
                coolant_supply = ev.value
                log.append(LogEntry(
                    t=t, severity="warning" if ev.value > 35 else "info",
                    message=f"CDU supply temperature now {ev.value:g} °C",
                ))
            elif ev.action == "degrade-pump" and ev.value is not None:
                pump_degrade = min(0.9, max(0.0, ev.value))
                flow_lpm = cfg.coolant_flow_lpm * (1.0 - pump_degrade)
                log.append(LogEntry(
                    t=t, severity="warning",
                    message=f"Pump degraded — flow down {100 * pump_degrade:.0f}%",
                ))
            elif ev.action == "restrict-tray" and ev.index is not None:
                if 0 <= ev.index < n_pos:
                    restricted.add(ev.index)
                    log.append(LogEntry(
                        t=t, severity="warning",
                        message=f"Tray {ev.index + 1} coolant restricted",
                    ))
            elif ev.action == "kill-psu":
                if alive_psus > 0:
                    alive_psus -= 1
                    log.append(LogEntry(
                        t=t, severity="warning",
                        message="PSU failed — survivors carrying the load",
                    ))

        if powered_on:
            gpu_util = wl.gpu_pct / 100.0
            feed = wl.data_feed_pct / 100.0
            eff_util = gpu_util * min(1.0, feed)
            # A starved GPU busy-waits: most of the demanded-but-undelivered
            # utilization still burns power (tokens don't).
            power_util = eff_util + (gpu_util - eff_util) * C("stall_power_fraction")

            per_gpu_at = [
                _demand(C("gpu_idle_fraction"), tdp, power_util) * clamps[p]
                for p in range(n_pos)
            ]
            gpus_per_pos = n_gpu // max(n_pos, 1)
            gpu_w = sum(w * gpus_per_pos for w in per_gpu_at) if n_gpu else 0.0
            cpu_w = n_cpu * _demand(
                C("cpu_idle_fraction"), cpu_tdp, wl.cpu_pct / 100.0
            )
            nic_w = nic_n * C("nic_w")
            fan_w = fan_n * C("fan_pmax_w") * (rpm / 100.0) ** 3
            pump_w = (
                C("pump_w_max") * (flow_lpm / 240.0) if liquid else 0.0
            )
            dc = gpu_w + cpu_w + nic_w + base_w + fan_w + pump_w

            # Wall side.
            if liquid:
                eff = 0.97  # busbar shelf conversion, single point
                capacity = cfg.shelf_capacity_kw * 1000.0
            else:
                capacity = alive_psus * cfg.psu_capacity_w
                eff = psu_efficiency(min(dc / max(capacity, 1.0), 1.2))
            ac = dc / eff if eff else 0.0
            if dc > C("psu_trip_fraction") * capacity:
                overcurrent_s += DT
                if overcurrent_s >= C("psu_trip_seconds"):
                    powered_on = False
                    shutdown_reason = (
                        "power-shelf overcurrent" if liquid else "PSU overcurrent trip"
                    )
                    log.append(LogEntry(
                        t=t, severity="critical",
                        message="Sustained overcurrent — power tripped, system off",
                    ))
            else:
                overcurrent_s = 0.0

            # --- Thermals -------------------------------------------------
            if liquid:
                liquid_w = dc * (1.0 - C("residual_air_fraction"))
                air_w = dc - liquid_w
                m_dot = max(flow_lpm, 1.0) / 60.0  # kg/s (water ≈ 1 kg/L)
                delta_t = liquid_w / (m_dot * C("water_cp"))
                # The loop's water volume lags the target return temp.
                target_return = coolant_supply + delta_t
                coolant_return += (target_return - coolant_return) * DT / C("coolant_tau")
                for p in range(n_pos):
                    # Supply-side trays run coolest; return-side hottest.
                    local = coolant_supply + (coolant_return - coolant_supply) * (p + 1) / n_pos
                    if p in restricted:
                        local += 32.0  # starved cold plate runs hot
                    per_gpu = per_gpu_at[p]
                    t_ss = local + per_gpu * C("gpu_r_th_liquid")
                    t_gpu[p] += (t_ss - t_gpu[p]) * DT / C("gpu_tau")
                t_cpu_ss = coolant_return + 5.0
                t_cpu += (t_cpu_ss - t_cpu) * DT / C("cpu_tau")
            else:
                liquid_w = 0.0
                air_w = dc
                delta_t = 0.0
                coolant_return = coolant_supply
                cool = 0.35 + 0.65 * (rpm / 100.0)
                r_gpu_air = (
                    C("gpu_r_th_pcie") if product == "xe7745" else C("gpu_r_th_sxm")
                )
                for p in range(n_pos):
                    preheat = (
                        p * C("positional_preheat_c") if product == "xe7745" else 4.0
                    )
                    per_gpu = per_gpu_at[p]
                    t_ss = env.inlet_c + preheat + per_gpu * r_gpu_air / cool
                    t_gpu[p] += (t_ss - t_gpu[p]) * DT / C("gpu_tau")
                t_cpu_ss = env.inlet_c + (cpu_w / 2) * C("cpu_r_th") / cool
                t_cpu += (t_cpu_ss - t_cpu) * DT / C("cpu_tau")

            # --- Fan controller (air) ------------------------------------
            if not liquid and n_pos:
                err = max(max(t_gpu) - C("gpu_target_c"), t_cpu - C("cpu_target_c"))
                rpm = max(C("fan_floor_pct"), min(100.0, rpm + C("fan_kp") * err))

            # --- Throttle -------------------------------------------------
            was = sum(1 for c in clamps if c < 1.0)
            if liquid and coolant_return > C("coolant_throttle_c"):
                # Loop-level protection throttles every tray together.
                clamps = [max(0.2, c - 0.05) for c in clamps]
            for p in range(n_pos):
                if t_gpu[p] > C("gpu_throttle_c"):
                    clamps[p] = max(0.2, clamps[p] - 0.10)
                elif clamps[p] < 1.0 and t_gpu[p] < C("gpu_throttle_c") - 4 and (
                    not liquid or coolant_return < C("coolant_throttle_c") - 2
                ):
                    clamps[p] = min(1.0, clamps[p] + 0.05)
            now = sum(1 for c in clamps if c < 1.0)
            if now > was:
                which = (
                    "HGX board (all 8 GPUs together)" if product == "xe9680"
                    else f"{now} of {n_pos} positions"
                )
                log.append(LogEntry(t=t, severity="warning",
                                    message=f"GPU throttling engaged — {which}"))

            if liquid and coolant_return >= C("coolant_trip_c"):
                powered_on = False
                shutdown_reason = "coolant over temperature"
                log.append(LogEntry(
                    t=t, severity="critical",
                    message="Coolant return over limit — rack emergency power-off",
                ))
            if not liquid and alive_psus == 0:
                powered_on = False
                shutdown_reason = "all PSUs lost"
                log.append(LogEntry(t=t, severity="critical",
                                    message="No PSU remaining — power lost"))
        else:
            gpu_w = cpu_w = nic_w = fan_w = pump_w = 0.0
            dc = ac = 0.0
            eff = 0.0
            eff_util = 0.0
            liquid_w = air_w = 0.0
            delta_t = 0.0
            coolant_return = coolant_supply
            rpm = 0.0
            for p in range(n_pos):
                t_gpu[p] += (env.inlet_c - t_gpu[p]) * DT / C("gpu_tau")
            t_cpu += (env.inlet_c - t_cpu) * DT / C("cpu_tau")

        # --- Performance ledger ------------------------------------------
        mean_clamp = sum(clamps) / len(clamps)
        tokens = (
            n_gpu * C("tokens_per_gpu") * eff_util * mean_clamp
            if powered_on else 0.0
        )
        demanded = wl.gpu_pct / 100.0 if powered_on else 0.0
        delivered = eff_util * mean_clamp if powered_on else 0.0
        wasted_gpu_hours += n_gpu * max(0.0, demanded - delivered) * DT / 3600.0
        it_w = dc - fan_w - pump_w
        overhead = (fan_w + pump_w) / it_w * 100.0 if it_w > 0 else 0.0

        gpus_throttled = (
            sum(gpus_per_pos if product != "xe9680" else 8
                for p in range(n_pos) if clamps[p] < 1.0)
            if powered_on and n_gpu else 0
        )
        if powered_on and gpus_throttled:
            throttle_seconds += 1
        peak_dc = max(peak_dc, dc)
        peak_tokens = max(peak_tokens, tokens)
        if t == 0:
            idle_dc = dc

        amb = env.inlet_c
        off = not powered_on
        if product == "xe7745":
            region_temps = {
                "fanwall": round(amb + 2 if not off else amb, 1),
                "cpu1": round(t_cpu, 1),
                "cpu2": round(t_cpu, 1),
                "dimm": round(amb if off else t_cpu - 20, 1),
                "nvme": round(amb if off else amb + 10, 1),
                "psu": round(amb if off else amb + 15, 1),
                "idrac": round(amb if off else amb + 8, 1),
                **{f"gpu-{p}": round(t_gpu[p] if p < n_pos else amb, 1)
                   for p in range(8)},
            }
        elif product == "xe9680":
            region_temps = {
                "nvme": round(amb if off else amb + 10, 1),
                "fanwall": round(amb + 2 if not off else amb, 1),
                "cpu": round(t_cpu, 1),
                "dimm": round(amb if off else t_cpu - 20, 1),
                "hgx": round(t_gpu[0], 1),
                "nvswitch": round(amb if off else t_gpu[0] - 8, 1),
                "nic": round(amb if off else amb + 18, 1),
                "psu": round(amb if off else amb + 15, 1),
                "idrac": round(amb if off else amb + 8, 1),
            }
        else:
            def tray_temp(i: int) -> float:
                p = min(i, n_pos - 1)
                return t_gpu[p]
            region_temps = {
                "shelf": round(amb if off else amb + 12, 1),
                "rmc": round(amb if off else amb + 8, 1),
                "nvsw": round(amb if off else coolant_return + 8, 1),
                "cdu": round(coolant_supply, 1),
                "manifold-supply": round(coolant_supply, 1),
                "manifold-return": round(coolant_return, 1),
                **{f"tray-{i}": round(tray_temp(i * max(n_pos // 4, 1)), 1)
                   for i in range(4)},
            }

        trace.append(SimState(
            t=t,
            powered_on=powered_on,
            cpu_power_w=round(cpu_w, 1),
            gpu_power_w=round(gpu_w, 1),
            nic_power_w=round(nic_w, 1),
            base_power_w=round(base_w if powered_on else 0.0, 1),
            fan_power_w=round(fan_w, 1),
            pump_power_w=round(pump_w, 1),
            dc_power_w=round(dc, 1),
            ac_power_w=round(ac, 1),
            psu_efficiency=round(eff, 4),
            alive_psus=alive_psus,
            gpu_temp_hot_c=round(max(t_gpu), 2) if n_pos else round(amb, 2),
            gpu_temp_cool_c=round(min(t_gpu), 2) if n_pos else round(amb, 2),
            cpu_temp_c=round(t_cpu, 2),
            gpus_throttled=gpus_throttled,
            liquid_watts=round(liquid_w, 1),
            air_watts=round(air_w, 1),
            coolant_supply_c=round(coolant_supply, 2),
            coolant_return_c=round(coolant_return, 2),
            coolant_delta_t_c=round(delta_t, 2),
            flow_lpm=round(flow_lpm if (liquid and powered_on) else 0.0, 1),
            fan_rpm_pct=round(rpm, 1),
            effective_gpu_util_pct=round(100 * eff_util * mean_clamp, 1),
            tokens_per_s=round(tokens, 1),
            gpu_hours_wasted=round(wasted_gpu_hours, 3),
            cooling_overhead_pct=round(overhead, 2),
            region_temps=region_temps,
        ))

    last = trace[-1]
    summary = Summary(
        peak_dc_w=round(peak_dc, 1),
        steady_dc_w=last.dc_power_w,
        idle_dc_w=round(idle_dc, 1),
        peak_tokens_per_s=round(peak_tokens, 1),
        gpu_hours_wasted=round(wasted_gpu_hours, 3),
        throttle_seconds=throttle_seconds,
        shutdown=not last.powered_on,
        shutdown_reason=shutdown_reason,
    )
    return trace, log, summary
