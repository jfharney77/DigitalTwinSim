"""Pure physics engine for the MX7000 shared-infrastructure simulator.

``simulate(scenario)`` returns the deterministic timestepped trace of the
configured chassis under the given per-sled workloads, environment, and
timed events. Same purity rule as every twin in this repo: no FastAPI, no
IO, no timers, no randomness — the frontend owns the playback clock, and
each ``SimState`` is plain data.

What the model exists to teach — sharing:

* **The fan wall belongs to the chassis.** The controller holds the
  *hottest* sled to target, so one 100%-load sled sets the rpm for all
  eight bays, and fan power (cubic in rpm) is billed to the chassis, not
  to the sled that caused it. The noisy-neighbor tax is an asserted fact:
  fan watts are inside the per-tick power balance.
* **The PSU pool is a policy, not a pair.** Grid redundancy splits the
  PSUs across two AC feeds and survives losing a whole feed; N+1 guards
  against a PSU failing but puts every PSU on one feed, so a feed loss is
  lights-out. The difference is a config toggle and a scenario.
* **Composability**: a storage sled has no workload of its own — its
  drive activity follows the compute sled that owns it, and reassignment
  is a timed event, not a recable.

Identities asserted in the tests, house style: per-tick power balance
(Σ sled powers + fabric + management + fans = DC; AC = DC ÷ η(load)) and
the steady-state heat balance ΔT = DC/(ṁ·cp).
"""

from __future__ import annotations

from .constants import PSU_EFFICIENCY_CURVE, value as C
from .models import (
    ChassisConfig,
    Environment,
    LogEntry,
    Scenario,
    SimState,
    SledConfig,
    SledLoad,
    Summary,
)

DT = 1.0  # sim timestep, seconds — fixed; playback pacing is the frontend's

SLED_COUNT = 8


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


def psu_feed(index: int, cfg: ChassisConfig) -> str:
    """Which AC feed a PSU hangs off. Grid redundancy alternates PSUs
    across feeds A/B; every other policy puts the whole pool on feed A —
    which is exactly why a whole-feed loss defeats it."""
    if cfg.redundancy == "grid":
        return "A" if index % 2 == 0 else "B"
    return "A"


def compute_sled_power(sled: SledConfig, load: SledLoad, clamp: float) -> float:
    """One compute sled's DC draw: two sockets on the superlinear curve,
    DIMMs, local drives, and the sled's fixed platform power."""
    tdp = float(sled.cpu_tdp_w)
    idle = C("cpu_idle_fraction") * tdp
    util = load.cpu_pct / 100.0
    cpu = C("sled_sockets") * (idle + (tdp - idle) * util ** C("cpu_util_exponent")) * clamp
    dimm = sled.dimms * (
        C("dimm_idle_w")
        + (C("dimm_active_w") - C("dimm_idle_w")) * load.mem_pct / 100.0
    )
    drives = sled.drives * (
        C("local_drive_idle_w")
        + (C("local_drive_active_w") - C("local_drive_idle_w")) * load.storage_pct / 100.0
    )
    return cpu + dimm + drives + C("sled_base_w")


def storage_sled_power(owner_storage_pct: float) -> float:
    """A storage sled's draw follows its *owner's* storage dial — the sled
    itself has nothing to be busy about."""
    per_drive = C("sas_drive_idle_w") + (
        C("sas_drive_active_w") - C("sas_drive_idle_w")
    ) * owner_storage_pct / 100.0
    return C("storage_sled_base_w") + C("storage_sled_drives") * per_drive


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    env: Environment = scenario.environment.model_copy()
    sleds = [s.model_copy() for s in cfg.sleds]
    while len(sleds) < SLED_COUNT:
        sleds.append(SledConfig(kind="empty"))
    loads = [ld.model_copy() for ld in scenario.workload.loads]
    while len(loads) < SLED_COUNT:
        loads.append(SledLoad())
    events = sorted(scenario.events, key=lambda e: e.at_s)

    cp = C("air_cp")
    floor = C("fan_floor_pct")
    fan_count = int(C("fan_count"))
    psu_cap = C("psu_capacity_w")

    # Mutable machine state.
    powered_on = True
    dead_fans: set[int] = set()
    dead_psus: set[int] = set()
    feed_up = {"A": True, "B": True}
    rpm = floor
    clamps = [1.0] * SLED_COUNT       # per-sled throttle multipliers
    chassis_clamp = 1.0               # power-budget clamp, applied to all
    overtemp_s = 0.0
    overcurrent_s = 0.0
    t_sled = [env.inlet_c] * SLED_COUNT

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    peak_dc = peak_ac = 0.0
    throttle_seconds = 0
    shutdown_reason = ""

    def alive_psu_count() -> int:
        return sum(
            1 for i in range(cfg.psu_count)
            if i not in dead_psus and feed_up[psu_feed(i, cfg)]
        )

    steps = int(scenario.duration_s / DT)
    for step in range(steps + 1):
        t = int(step * DT)

        # Apply due events.
        while ei < len(events) and events[ei].at_s <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-sled-load" and ev.index is not None and ev.load is not None:
                if 0 <= ev.index < SLED_COUNT:
                    loads[ev.index] = ev.load.model_copy()
                    log.append(LogEntry(
                        t=t, severity="info",
                        message=f"Sled {ev.index + 1} workload changed",
                    ))
            elif ev.action == "set-all-load" and ev.load is not None:
                for i in range(SLED_COUNT):
                    loads[i] = ev.load.model_copy()
                log.append(LogEntry(t=t, severity="info",
                                    message="All sled workloads changed"))
            elif ev.action == "kill-fan" and ev.index is not None:
                if 0 <= ev.index < fan_count and ev.index not in dead_fans:
                    dead_fans.add(ev.index)
                    log.append(LogEntry(
                        t=t, severity="warning",
                        message=f"Fan {ev.index + 1} failed — the other {fan_count - len(dead_fans)} carry all eight bays",
                    ))
            elif ev.action == "restore-fan" and ev.index is not None:
                if ev.index in dead_fans:
                    dead_fans.discard(ev.index)
                    log.append(LogEntry(t=t, severity="info",
                                        message=f"Fan {ev.index + 1} replaced"))
            elif ev.action == "kill-psu":
                alive = [
                    i for i in range(cfg.psu_count)
                    if i not in dead_psus and feed_up[psu_feed(i, cfg)]
                ]
                if alive:
                    dead_psus.add(alive[0])
                    log.append(LogEntry(
                        t=t, severity="warning",
                        message=f"PSU {alive[0] + 1} failed — pool of {len(alive) - 1} carries the chassis",
                    ))
            elif ev.action == "lose-feed" and ev.index is not None:
                feed = "A" if ev.index == 0 else "B"
                if feed_up[feed]:
                    feed_up[feed] = False
                    on_feed = sum(
                        1 for i in range(cfg.psu_count) if psu_feed(i, cfg) == feed
                    )
                    log.append(LogEntry(
                        t=t, severity="critical" if on_feed == cfg.psu_count else "warning",
                        message=f"AC feed {feed} lost — {on_feed} of {cfg.psu_count} PSUs dark",
                    ))
            elif ev.action == "restore-feed" and ev.index is not None:
                feed = "A" if ev.index == 0 else "B"
                if not feed_up[feed]:
                    feed_up[feed] = True
                    log.append(LogEntry(t=t, severity="info",
                                        message=f"AC feed {feed} restored"))
            elif ev.action == "set-inlet" and ev.value is not None:
                env.inlet_c = ev.value
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Inlet air set to {ev.value:g} °C"))
            elif ev.action == "reassign-storage" and ev.index is not None and ev.value is not None:
                i = ev.index
                if 0 <= i < SLED_COUNT and sleds[i].kind == "storage":
                    sleds[i] = sleds[i].model_copy(update={"owner_slot": int(ev.value)})
                    log.append(LogEntry(
                        t=t, severity="info",
                        message=f"Storage sled {i + 1} reassigned to compute sled {int(ev.value)} — no recabling, a config action",
                    ))

        alive_psus = alive_psu_count()
        if powered_on and alive_psus == 0:
            powered_on = False
            shutdown_reason = "no PSUs alive — AC feed lost"
            log.append(LogEntry(
                t=t, severity="critical",
                message="No PSUs alive — chassis dark. Grid redundancy would have survived this.",
            ))

        alive_fans = fan_count - len(dead_fans)

        if powered_on:
            # --- Per-sled powers -----------------------------------------
            sled_w = [0.0] * SLED_COUNT
            for i, sled in enumerate(sleds):
                if sled.kind == "compute":
                    sled_w[i] = compute_sled_power(
                        sled, loads[i], clamps[i] * chassis_clamp
                    )
                elif sled.kind == "storage":
                    owner = sled.owner_slot
                    pct = 0.0
                    if owner is not None and 1 <= owner <= SLED_COUNT:
                        if sleds[owner - 1].kind == "compute":
                            pct = float(loads[owner - 1].storage_pct)
                    sled_w[i] = storage_sled_power(pct)

            fabric_w = 2 * C("fabric_iom_w")
            mgmt_w = 2 * C("mgmt_module_w")
            fan_w = alive_fans * C("fan_pmax_w") * (rpm / 100.0) ** 3
            dc = sum(sled_w) + fabric_w + mgmt_w + fan_w

            capacity = alive_psus * psu_cap
            load_frac = dc / max(capacity, 1.0)
            eff = psu_efficiency(min(load_frac, 1.2))
            ac = dc / eff

            # Chassis power budget (spec module M11): a cap set below the
            # pool's ability throttles every compute sled together.
            if cfg.power_cap_w > 0:
                if dc > cfg.power_cap_w:
                    if chassis_clamp >= 1.0:
                        log.append(LogEntry(
                            t=t, severity="warning",
                            message=f"Chassis power budget {cfg.power_cap_w} W exceeded — capping all compute sleds",
                        ))
                    chassis_clamp = max(0.3, chassis_clamp - 0.05)
                elif dc < cfg.power_cap_w * 0.95 and chassis_clamp < 1.0:
                    chassis_clamp = min(1.0, chassis_clamp + 0.02)

            # PSU pool overcurrent (sustained overload of the survivors).
            if dc > C("psu_overcurrent_trip_fraction") * capacity:
                overcurrent_s += DT
                if overcurrent_s >= C("psu_overcurrent_trip_seconds"):
                    powered_on = False
                    shutdown_reason = "PSU pool overcurrent trip"
                    log.append(LogEntry(
                        t=t, severity="critical",
                        message="Sustained overcurrent on the surviving PSU pool — chassis hard-off",
                    ))
            else:
                overcurrent_s = 0.0

            # --- Airflow & sled temperatures ------------------------------
            cfm = C("fan_cfm") * alive_fans * (rpm / 100.0)
            m_dot = max(cfm, 1.0) * C("cfm_to_m3s") * C("air_density")
            m_slot = m_dot / SLED_COUNT

            for i, sled in enumerate(sleds):
                if sled.kind == "compute":
                    air = env.inlet_c + sled_w[i] / (m_slot * cp)
                    # Junction rise from per-socket CPU power alone.
                    tdp = float(sled.cpu_tdp_w)
                    idle = C("cpu_idle_fraction") * tdp
                    cpu_per_socket = (
                        idle + (tdp - idle) * (loads[i].cpu_pct / 100.0) ** C("cpu_util_exponent")
                    ) * clamps[i] * chassis_clamp
                    t_ss = air + cpu_per_socket * C("sled_r_th")
                    tau = C("sled_tau")
                elif sled.kind == "storage":
                    air = env.inlet_c + sled_w[i] / (m_slot * cp)
                    t_ss = air + C("storage_rise_c")
                    tau = C("storage_tau")
                else:
                    t_ss = env.inlet_c
                    tau = C("sled_tau")
                t_sled[i] += (t_ss - t_sled[i]) * DT / tau

            exhaust = env.inlet_c + dc / (m_dot * cp)

            # --- Shared fan controller ------------------------------------
            occupied = [i for i, s in enumerate(sleds) if s.kind != "empty"]
            if occupied:
                hottest = max(occupied, key=lambda i: t_sled[i])
                err = t_sled[hottest] - C("sled_target_c")
            else:
                hottest = -1
                err = -100.0
            rpm = max(floor, min(100.0, rpm + C("fan_kp") * err))

            # --- Per-sled protective throttling ----------------------------
            for i, sled in enumerate(sleds):
                if sled.kind != "compute":
                    continue
                if t_sled[i] > C("sled_throttle_c"):
                    if clamps[i] >= 1.0:
                        log.append(LogEntry(
                            t=t, severity="warning",
                            message=f"Sled {i + 1} throttling engaged",
                        ))
                    clamps[i] = max(0.1, clamps[i] - 0.10)
                elif clamps[i] < 1.0 and t_sled[i] < C("sled_throttle_c") - 4:
                    clamps[i] = min(1.0, clamps[i] + 0.05)
                    if clamps[i] >= 1.0:
                        log.append(LogEntry(t=t, severity="info",
                                            message=f"Sled {i + 1} throttling released"))

            hot_max = max((t_sled[i] for i in occupied), default=env.inlet_c)
            if hot_max >= C("sled_shutdown_c"):
                overtemp_s += DT
                if overtemp_s >= C("shutdown_sustain_seconds"):
                    powered_on = False
                    shutdown_reason = "critical sled overtemperature"
                    log.append(LogEntry(
                        t=t, severity="critical",
                        message="Critical sled overtemp — emergency chassis power-off",
                    ))
            else:
                overtemp_s = 0.0
            if env.inlet_c >= C("inlet_shutdown_c") and powered_on:
                powered_on = False
                shutdown_reason = "inlet air over limit"
                log.append(LogEntry(
                    t=t, severity="critical",
                    message="Inlet air over limit — emergency chassis power-off",
                ))
        else:
            sled_w = [0.0] * SLED_COUNT
            fabric_w = mgmt_w = fan_w = 0.0
            dc = ac = 0.0
            eff = 0.0
            load_frac = 0.0
            cfm = 0.0
            exhaust = env.inlet_c
            hottest = -1
            rpm = 0.0
            for i in range(SLED_COUNT):
                t_sled[i] += (env.inlet_c - t_sled[i]) * DT / C("sled_tau")

        throttling = [clamps[i] < 1.0 and sleds[i].kind == "compute"
                      for i in range(SLED_COUNT)]
        if any(throttling) or chassis_clamp < 1.0:
            throttle_seconds += 1
        peak_dc = max(peak_dc, dc)
        peak_ac = max(peak_ac, ac)

        # Region temperatures for the chassis coloring (ids from anatomy.py).
        region_temps: dict[str, float] = {}
        for i in range(SLED_COUNT):
            region_temps[f"sled-{i + 1}"] = round(
                t_sled[i] if sleds[i].kind != "empty" else env.inlet_c, 1
            )
        fan_air = env.inlet_c + 1.0 if powered_on else env.inlet_c
        for i in range(fan_count):
            region_temps[f"fan-{i}"] = round(
                env.inlet_c if i in dead_fans else fan_air, 1
            )
        for i in range(6):
            up = (
                powered_on and i < cfg.psu_count
                and i not in dead_psus and feed_up[psu_feed(i, cfg)]
            )
            region_temps[f"psu-{i}"] = round(exhaust if up else env.inlet_c, 1)
        region_temps["mgmt-a"] = round(env.inlet_c + 6 if powered_on else env.inlet_c, 1)
        region_temps["mgmt-b"] = round(env.inlet_c + 6 if powered_on else env.inlet_c, 1)
        region_temps["fabric-a"] = round(env.inlet_c + 14 if powered_on else env.inlet_c, 1)
        region_temps["fabric-b"] = round(env.inlet_c + 14 if powered_on else env.inlet_c, 1)

        trace.append(SimState(
            t=t,
            powered_on=powered_on,
            sled_power_w=[round(w, 1) for w in sled_w],
            sled_temp_c=[round(x, 2) for x in t_sled],
            sled_throttling=throttling,
            hottest_slot=(hottest + 1) if powered_on and hottest >= 0 else 0,
            fabric_power_w=round(fabric_w, 1),
            mgmt_power_w=round(mgmt_w, 1),
            fan_power_w=round(fan_w, 1),
            dc_power_w=round(dc, 1),
            ac_power_w=round(ac, 1),
            psu_efficiency=round(eff, 4),
            psu_load_pct=round(100 * load_frac, 1),
            alive_psus=alive_psus if powered_on else 0,
            feed_a_up=feed_up["A"],
            feed_b_up=feed_up["B"],
            fan_rpm_pct=round(rpm, 1),
            alive_fans=alive_fans,
            airflow_cfm=round(cfm, 1),
            inlet_c=round(env.inlet_c, 2),
            exhaust_c=round(exhaust, 2),
            delta_t_c=round(exhaust - env.inlet_c, 2),
            chassis_capped=chassis_clamp < 1.0,
            region_temps=region_temps,
        ))

    last = trace[-1]
    summary = Summary(
        peak_dc_w=round(peak_dc, 1),
        peak_ac_w=round(peak_ac, 1),
        steady_dc_w=last.dc_power_w,
        steady_fan_w=last.fan_power_w,
        hottest_sled_c=max(last.sled_temp_c),
        throttle_seconds=throttle_seconds,
        shutdown=not last.powered_on,
        shutdown_reason=shutdown_reason,
    )
    return trace, log, summary
