"""Pure flow-level fabric engine (physics_specs/03). No packets — per-
link utilization is computed from routed flow demand, and the two core
lessons are first-class mechanics:

1. **Oversubscription**: downlink ÷ uplink capacity per leaf; congestion
   appears exactly where the ratio predicts.
2. **Congestion → latency/loss**: past ~90% utilization the queue-delay
   curve rises on the same 1/(1−ρ) shape as the storage engine; past
   100% demand the three personalities diverge — Ethernet drops,
   lossless Ethernet pauses (and spreads), InfiniBand stalls senders by
   credit and *cannot* drop.

The gray-failure toggle is the adversarial bit: a link silently loses
0.1%, goodput collapses on affected flows, and every status light stays
green — the argument for fleet telemetry, run as code.
"""

from __future__ import annotations

from .constants import value as C
from .models import (
    FabricConfig,
    LogEntry,
    Scenario,
    SimState,
    Summary,
    Workload,
)

DT = 1.0


def oversub_ratio(cfg: FabricConfig) -> float:
    down = cfg.endpoints_per_leaf * cfg.downlink_gbps
    up = cfg.spines * cfg.uplink_gbps
    return down / up if up else 99.0


def poe_demand_w(cfg: FabricConfig) -> float:
    return (
        cfg.poe_aps * C("poe_ap_w")
        + cfg.poe_cameras * C("poe_camera_w")
        + cfg.poe_phones * C("poe_phone_w")
    )


def switch_power_w(cfg: FabricConfig, spines_alive: int) -> tuple[float, float, float]:
    """(total, optics, asic) fabric power."""
    if cfg.product == "e3200":
        base = (cfg.leaves + 1) * C("campus_switch_base_w")
        return base, 0.0, base
    switches = spines_alive + cfg.leaves
    ports = (
        spines_alive * cfg.leaves          # spine-side leaf links
        + cfg.leaves * spines_alive        # leaf uplinks
        + cfg.leaves * cfg.endpoints_per_leaf
    )
    optic_w = C("optic_cpo_w") if cfg.cpo_optics else C("optic_pluggable_w")
    optics = ports * optic_w
    asic = switches * C("asic_base_w")
    return optics + asic, optics, asic


def _imbalance(pattern: str) -> float:
    return {
        "uniform": C("imbalance_uniform"),
        "incast": C("imbalance_uniform"),
        "alltoall": C("imbalance_alltoall"),
        "elephant": C("imbalance_elephant"),
    }[pattern]


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    wl: Workload = scenario.workload.model_copy()
    events = sorted(scenario.events, key=lambda e: e.at_s)
    p = cfg.product
    ib = p == "x800"
    lossless = ib or (p == "sn6000" and cfg.lossless_roce)

    spines_alive = cfg.spines
    adaptive = cfg.adaptive_routing
    sharp_on = cfg.sharp
    gray = False
    uplink_dead_until = -1.0
    dead_uplinks = 0
    psu_alive = 2 if cfg.psu_redundant else 1
    devices_total = cfg.poe_aps + cfg.poe_cameras + cfg.poe_phones

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    peak_worst = 0.0
    total_drops = 0.0
    min_ratio = 1.0
    seconds_congested = 0
    peak_lat = 0.0

    steps = int(scenario.duration_s / DT)
    for step in range(steps + 1):
        t = int(step * DT)

        while ei < len(events) and events[ei].at_s <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                wl = ev.workload.model_copy()
                log.append(LogEntry(t=t, severity="info", message="Traffic changed"))
            elif ev.action == "kill-spine":
                if spines_alive > 1:
                    spines_alive -= 1
                    log.append(LogEntry(
                        t=t, severity="warning",
                        message="Spine lost — flows rerouted over survivors",
                    ))
            elif ev.action == "restore-spine":
                if spines_alive < cfg.spines:
                    spines_alive += 1
                    log.append(LogEntry(t=t, severity="info",
                                        message="Spine restored"))
            elif ev.action == "kill-uplink":
                dead_uplinks = min(dead_uplinks + 1, 1)
                uplink_dead_until = t + C("stp_failover_s")
                log.append(LogEntry(
                    t=t, severity="warning",
                    message="Access uplink down — STP reconverging, then one wire carries the floor",
                ))
            elif ev.action == "gray-failure":
                gray = True
                log.append(LogEntry(
                    t=t, severity="info",
                    message="(nothing logged by the fabric — a link began silently losing 0.1%)",
                ))
            elif ev.action == "clear-gray":
                gray = False
                log.append(LogEntry(t=t, severity="info",
                                    message="Gray link replaced"))
            elif ev.action == "toggle-adaptive":
                adaptive = not adaptive
                log.append(LogEntry(
                    t=t, severity="info",
                    message=f"Adaptive routing {'ON' if adaptive else 'OFF'}",
                ))
            elif ev.action == "toggle-sharp":
                sharp_on = not sharp_on
                log.append(LogEntry(
                    t=t, severity="info",
                    message=f"SHARP in-network collectives {'ON' if sharp_on else 'OFF'}",
                ))
            elif ev.action == "kill-psu":
                if psu_alive > 0:
                    psu_alive -= 1
                    log.append(LogEntry(
                        t=t, severity="warning",
                        message="PSU lost — PoE budget halved; low-priority devices shed",
                    ))

        demand = float(wl.demand_gbps)

        # --- Link math ----------------------------------------------------
        if p == "e3200":
            # Campus tree: leaves = access switches, a LAG uplink pair
            # each. Losing one wire halves the pair's capacity — the
            # survivor's utilization doubles.
            uplinks = max(2 - dead_uplinks, 1)
            per_access = demand / max(cfg.leaves, 1)
            worst_util = (
                per_access / (uplinks * cfg.uplink_gbps)
                if cfg.uplink_gbps else 9.9
            )
            mean_util = per_access / (2 * cfg.uplink_gbps) if cfg.uplink_gbps else 9.9
            in_stp_outage = dead_uplinks > 0 and t < uplink_dead_until
        else:
            fair = demand / max(cfg.leaves, 1) / max(spines_alive, 1)
            imb = _imbalance(wl.pattern)
            if adaptive:
                imb *= C("adaptive_residual")
            # SHARP keeps a share of collective bytes off the links.
            link_demand_scale = 1.0
            if ib and sharp_on and wl.collective_pct:
                link_demand_scale = 1.0 - (
                    wl.collective_pct / 100.0
                ) * C("sharp_link_relief")
            worst_link_gbps = fair * (1.0 + imb) * link_demand_scale
            if wl.pattern == "incast":
                hot = demand * link_demand_scale / max(cfg.leaves, 1) \
                    * C("incast_concentration")
                worst_link_gbps = max(
                    worst_link_gbps,
                    hot / max(spines_alive, 1),
                )
            worst_util = worst_link_gbps / cfg.uplink_gbps
            mean_util = fair * link_demand_scale / cfg.uplink_gbps
            in_stp_outage = False

        rho = min(worst_util, C("rho_clamp"))
        congested = worst_util > C("queue_onset")

        # --- Delivery / loss per personality ------------------------------
        drops_gbps = 0.0
        pauses = 0.0
        stall_us = 0.0
        if in_stp_outage:
            delivered = 0.0
            lost = demand
        elif worst_util <= 1.0:
            delivered = demand
            lost = 0.0
        else:
            excess_fraction = (worst_util - 1.0) / worst_util
            if ib:
                # Credit-based: the violation is unexpressible. Senders
                # stall; the excess waits at the source.
                delivered = demand * (1.0 - excess_fraction)
                lost = 0.0
                stall_us = excess_fraction * 1e6
            elif lossless:
                # PFC: no drops, but pauses spread congestion upstream.
                delivered = demand * (1.0 - excess_fraction)
                lost = 0.0
                pauses = excess_fraction * 1000.0 * C("pause_spread_factor")
            else:
                delivered = demand * (1.0 - excess_fraction)
                lost = demand - delivered
                drops_gbps = lost

        # Gray failure: goodput penalty on the affected share, and the
        # counters stay clean — that is the point.
        goodput_penalty = 0.0
        if gray and delivered > 0:
            affected_share = 1.0 / max(cfg.leaves, 1)
            goodput_penalty = affected_share * C("gray_goodput_penalty")
            delivered *= 1.0 - goodput_penalty / 100.0

        # --- Latency & FCT -------------------------------------------------
        hops = 2 if p != "e3200" else 3
        queue_mult = 1.0 / (1.0 - rho) if congested else 1.0 + rho * 0.2
        latency = hops * C("base_hop_us") * queue_mult
        if pauses:
            latency *= C("pause_spread_factor")
        eff_rate_gbps = max(delivered / max(demand, 1e-9), 0.01) * cfg.uplink_gbps
        fct = (C("fct_flow_mb") * 8.0 / 1000.0) / max(eff_rate_gbps, 0.01) \
            * queue_mult * 1000.0
        if gray:
            fct *= 1.0 + C("gray_goodput_penalty") / 25.0

        # --- Collectives ---------------------------------------------------
        coll_share = wl.collective_pct / 100.0
        allreduce = delivered * coll_share
        if ib and sharp_on and coll_share:
            allreduce *= C("sharp_speedup")

        # --- PoE (E3200) ---------------------------------------------------
        budget = cfg.poe_budget_w * (1.0 if psu_alive >= 1 else 0.0)
        if cfg.product == "e3200" and psu_alive == 1 and cfg.psu_redundant:
            budget = cfg.poe_budget_w / 2.0
        demand_w = poe_demand_w(cfg)
        powered = devices_total
        if cfg.product == "e3200" and demand_w > budget:
            # Shed lowest priority first: phones, then cameras, then APs.
            deficit = demand_w - budget
            shed_phones = min(cfg.poe_phones, int(deficit / C("poe_phone_w")) + 1)
            deficit -= shed_phones * C("poe_phone_w")
            shed_cams = 0
            if deficit > 0:
                shed_cams = min(cfg.poe_cameras, int(deficit / C("poe_camera_w")) + 1)
                deficit -= shed_cams * C("poe_camera_w")
            shed_aps = 0
            if deficit > 0:
                shed_aps = min(cfg.poe_aps, int(deficit / C("poe_ap_w")) + 1)
            powered = devices_total - shed_phones - shed_cams - shed_aps

        total_w, optics_w, asic_w = switch_power_w(cfg, spines_alive)
        if cfg.product == "e3200":
            total_w += min(demand_w, budget)

        status_green = not in_stp_outage and spines_alive == cfg.spines \
            and psu_alive >= 1
        # The gray link does NOT flip the status — that's the lesson.

        # --- Map coloring --------------------------------------------------
        wl_pct = min(200.0, worst_util * 100.0)
        ml_pct = min(100.0, mean_util * 100.0)
        if p == "e3200":
            region_load = {
                "core": round(ml_pct, 1),
                "distribution": round(ml_pct, 1),
                "access": round(wl_pct, 1),
                "devices": round(100.0 * powered / devices_total if devices_total else 0.0, 1),
                "poe": round(100.0 * min(demand_w, budget) / budget if budget else 0.0, 1),
            }
        elif p == "sn6000":
            region_load = {
                "spines": round(ml_pct, 1),
                "worst-link": round(wl_pct, 1),
                "leaves": round(ml_pct, 1),
                "endpoints": round(min(100.0, demand / max(
                    cfg.leaves * cfg.endpoints_per_leaf * cfg.downlink_gbps, 1
                ) * 100.0), 1),
                "optics": round(100.0 * optics_w / max(total_w, 1), 1),
                "telemetry": round(goodput_penalty * 2, 1),
            }
        else:
            region_load = {
                "spines": round(ml_pct, 1),
                "worst-link": round(wl_pct, 1),
                "leaves": round(ml_pct, 1),
                "endpoints": round(min(100.0, stall_us / 1e4), 1),
                "manager": round(5.0, 1),
                "sharp": round(100.0 * coll_share if sharp_on else 0.0, 1),
            }

        state = SimState(
            t=t,
            demanded_gbps=round(demand, 1),
            delivered_gbps=round(delivered, 1),
            lost_gbps=round(lost, 2),
            dropped_pps=round(drops_gbps * C("pps_per_gbps"), 0),
            pause_events_s=round(pauses, 1),
            stall_us_per_s=round(stall_us, 0),
            worst_link_pct=round(wl_pct, 1),
            mean_link_pct=round(ml_pct, 1),
            oversub_ratio=round(oversub_ratio(cfg), 2),
            latency_us=round(latency, 2),
            fct_ms=round(fct, 2),
            allreduce_gbps=round(allreduce, 1),
            spines_alive=spines_alive,
            fabric_power_w=round(total_w, 0),
            optics_power_w=round(optics_w, 0),
            asic_power_w=round(asic_w, 0),
            status_all_green=status_green,
            goodput_penalty_pct=round(goodput_penalty, 1),
            poe_budget_w=round(budget, 0),
            poe_demand_w=round(demand_w, 0),
            devices_powered=powered,
            devices_total=devices_total,
            region_load=region_load,
        )
        trace.append(state)

        peak_worst = max(peak_worst, wl_pct)
        total_drops += drops_gbps * DT
        if demand > 0:
            min_ratio = min(min_ratio, delivered / demand)
        if congested:
            seconds_congested += 1
        peak_lat = max(peak_lat, latency)

    last = trace[-1]
    summary = Summary(
        peak_worst_link_pct=round(peak_worst, 1),
        total_drops=round(total_drops, 2),
        min_delivered_ratio=round(min_ratio, 3),
        seconds_congested=seconds_congested,
        peak_latency_us=round(peak_lat, 1),
        fabric_power_w=last.fabric_power_w,
    )
    return trace, log, summary
