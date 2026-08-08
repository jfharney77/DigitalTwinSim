"""Pure engine for the storage-platforms simulator (physics_specs/02).

One tick = one sim-hour. The shared Archetype-B physics:

* **The knee** — service latency (media × cache mix) multiplied by the
  M/M/1-style 1/(1−ρ) queue factor. Every storage lesson in this app is
  somewhere on that curve.
* **Capacity arithmetic** — raw → usable (protection overhead) →
  effective (data reduction), filled over sim-days by the ingest rate,
  inflated by snapshots, alerted at 80/90/95%.
* **Rebuild dynamics** — rebuild time = data ÷ rebuild bandwidth, where
  the bandwidth is a controller's fixed budget (PowerStore/PowerMax) or
  scales with surviving nodes (PowerScale, and dramatically PowerFlex).
  The exposure flag marks the window where one more failure loses data.

Product personalities are parameterizations, not separate engines —
which is the spec's argument for building them in one app.
"""

from __future__ import annotations

from .constants import (
    PROTECTION_OVERHEAD,
    PROTECTION_SURVIVES,
    value as C,
)
from .models import (
    LogEntry,
    Scenario,
    SimState,
    StorageConfig,
    Summary,
    Workload,
)

DT_H = 1.0

# Exascale: how the AI demand splits across the partitioned pools.
POOL_SHARE = {"lightning": 0.60, "file": 0.20, "object": 0.15, "block": 0.05}


def media_latency_ms(cfg: StorageConfig) -> float:
    return {
        "nvme": C("lat_nvme_ms"),
        "ssd": C("lat_ssd_ms"),
        "hdd": C("lat_hdd_ms"),
    }[cfg.drive_class]


def scaleout_tax(nodes: int) -> float:
    return min(
        C("coordination_tax_cap"),
        C("coordination_tax_per_node") * max(0, nodes - 10),
    )


def network_cap_iops_k(cfg: StorageConfig, nodes: int, block_kb: int) -> float:
    """PowerFlex: aggregate front-end IOPS the node NICs can carry
    (half the wire is spent on mirror writes)."""
    usable_gbs = nodes * cfg.nic_gbps / 8.0 * 0.5
    return usable_gbs * 1e6 / (block_kb * 1.024) / 1000.0


def iops_capacity_k(cfg: StorageConfig, units: int, block_kb: int) -> float:
    p = cfg.product
    if p == "powerstore":
        return units * C("iops_per_unit_powerstore_k")
    if p == "powermax":
        return units * C("iops_per_unit_powermax_k")
    if p in ("powerscale", "objectscale"):
        per = C("iops_per_node_scaleout_k") * (1.0 - scaleout_tax(units))
        cap = units * per
        if p == "objectscale" and cfg.small_objects:
            cap *= 1.0 - C("small_object_tax")
        return cap
    if p == "powerflex":
        node_cap = units * C("iops_per_node_powerflex_k")
        return min(node_cap, network_cap_iops_k(cfg, units, block_kb))
    # Exascale: the sum of its partitioned pools.
    return sum(pool_capacities_k(cfg).values())


def pool_capacities_k(cfg: StorageConfig) -> dict[str, float]:
    return {
        "lightning": cfg.lightning_units * C("iops_per_node_lightning_k"),
        "file": cfg.file_units * C("iops_per_node_scaleout_k")
        * (1.0 - scaleout_tax(cfg.file_units)),
        "object": cfg.object_units * C("iops_per_node_scaleout_k"),
        "block": cfg.block_units * C("iops_per_node_powerflex_k"),
    }


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    wl: Workload = scenario.workload.model_copy()
    events = sorted(scenario.events, key=lambda e: e.at_h)
    p = cfg.product
    controller_array = p in ("powerstore", "powermax")
    survives = PROTECTION_SURVIVES[cfg.protection]

    units = cfg.units
    frontend_factor = 1.0        # PowerStore controller loss halves it
    blip_ms = 0.0                # PowerMax failover blip, decays
    used_data_tb = 0.0           # physical, post-reduction
    snapshot_tb = 0.0
    rebuild_gb_left = 0.0
    rebuild_gb_total = 0.0
    failures_in_window = 0
    async_backlog_gb = 0.0
    rebalance_until_h = -1.0
    burst_until_h = -1.0
    burst_mult = 1.0
    data_survived = True
    online = True

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    peak_lat = 0.0
    min_ratio = 1.0
    hours_saturated = 0
    rebuild_hours = 0.0
    alerted: set[str] = set()

    steps = int(scenario.duration_h / DT_H)
    for step in range(steps + 1):
        t = int(step * DT_H)

        while ei < len(events) and events[ei].at_h <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                wl = ev.workload.model_copy()
                log.append(LogEntry(t_h=t, severity="info", message="Workload changed"))
            elif ev.action == "fail-drive":
                rebuild_gb_total = cfg.drive_tb * 1000.0
                rebuild_gb_left = rebuild_gb_total
                failures_in_window += 1
                log.append(LogEntry(
                    t_h=t, severity="warning",
                    message=f"Drive failed ({cfg.drive_tb:g} TB) — rebuild started",
                ))
                if failures_in_window > survives:
                    data_survived = False
                    online = False
                    log.append(LogEntry(
                        t_h=t, severity="critical",
                        message="Failures exceeded the protection level — data loss",
                    ))
            elif ev.action == "fail-controller":
                if p == "powerstore":
                    frontend_factor = 0.5
                    log.append(LogEntry(
                        t_h=t, severity="warning",
                        message="Controller failed — surviving node carries all front-end I/O",
                    ))
                elif p == "powermax":
                    blip_ms += C("blip_ms")
                    log.append(LogEntry(
                        t_h=t, severity="warning",
                        message="Director failed — latency blip, service continues",
                    ))
            elif ev.action == "fail-node":
                if not controller_array and units > 1:
                    units -= 1
                    rebuild_gb_total = cfg.drives_per_unit * cfg.drive_tb * 1000.0
                    rebuild_gb_left = rebuild_gb_total
                    failures_in_window += 1
                    log.append(LogEntry(
                        t_h=t, severity="warning",
                        message="Node lost — cluster-wide rebuild of its slice began",
                    ))
            elif ev.action == "add-nodes" and ev.value is not None:
                units += int(ev.value)
                rebalance_until_h = t + 2
                log.append(LogEntry(
                    t_h=t, severity="info",
                    message=f"{int(ev.value)} nodes joined — rebalancing",
                ))
            elif ev.action == "attempt-delete":
                if cfg.immutable:
                    log.append(LogEntry(
                        t_h=t, severity="warning",
                        message="DELETE rejected — object lock (WORM) holds the data",
                    ))
                else:
                    used_data_tb *= 0.95
                    log.append(LogEntry(t_h=t, severity="info",
                                        message="Objects deleted — 5% of used capacity freed"))
            elif ev.action == "write-burst" and ev.value is not None:
                burst_mult = ev.value
                burst_until_h = t + 6
                log.append(LogEntry(
                    t_h=t, severity="warning",
                    message=f"Write burst — write demand ×{ev.value:g} for 6 h",
                ))

        # --- Demand this hour ---------------------------------------------
        write_frac = 1.0 - wl.read_pct / 100.0
        mult = burst_mult if t <= burst_until_h else 1.0
        # Exascale runs training: automatic checkpoint stampedes.
        if p == "exascale" and t > 0 and t % int(C("checkpoint_period_h")) == 0:
            mult = max(mult, C("checkpoint_burst_multiplier"))
        demand_k = wl.iops_demand_k * (
            wl.read_pct / 100.0 + write_frac * mult
        )

        if online:
            cap_k = iops_capacity_k(cfg, units, wl.block_kb) * frontend_factor
            rho = demand_k / cap_k if cap_k > 0 else 2.0
            rho_c = min(rho, C("rho_clamp"))
            hit = wl.working_set_fit_pct / 100.0
            service = hit * C("cache_hit_lat_ms") + (1 - hit) * media_latency_ms(cfg)
            if p == "objectscale":
                service += 2.0  # object stack: ms-class floor, and that's fine
            lat = service / (1.0 - rho_c)
            if rebuild_gb_left > 0 or t <= rebalance_until_h:
                lat *= C("rebuild_latency_penalty")
            srdf_ms = 0.0
            if p == "powermax" and cfg.srdf == "sync":
                srdf_ms = cfg.distance_km * C("srdf_ms_per_km") * 2.0 * write_frac
                lat += srdf_ms
            lat += blip_ms
            blip_ms *= pow(0.5, DT_H / C("blip_decay_h"))
            delivered_k = min(demand_k, cap_k)
            saturated = demand_k > cap_k
            throughput = delivered_k * C("gbps_per_iopsk_8k") * (wl.block_kb / 8.0)

            # Async RPO.
            rpo_s = 0.0
            if p == "powermax" and cfg.srdf == "async":
                write_gbs = throughput * write_frac
                async_backlog_gb += max(0.0, write_gbs - C("async_link_gbs")) * 3600.0 * DT_H
                async_backlog_gb = max(
                    0.0,
                    async_backlog_gb
                    - max(0.0, C("async_link_gbs") - write_gbs) * 3600.0 * DT_H,
                )
                rpo_s = async_backlog_gb / C("async_link_gbs")

            # Rebuild progress.
            if rebuild_gb_left > 0:
                if controller_array:
                    rate = C("rebuild_gbps_controller")
                elif p == "powerflex" or (p == "exascale" and cfg.block_units):
                    rate = C("rebuild_gbps_per_node_powerflex") * max(units - 1, 1)
                else:
                    rate = C("rebuild_gbps_per_node") * max(units - 1, 1)
                rebuild_gb_left = max(0.0, rebuild_gb_left - rate * 3600.0 * DT_H)
                rebuild_hours += DT_H
                if rebuild_gb_left == 0:
                    failures_in_window = max(0, failures_in_window - 1)
                    log.append(LogEntry(
                        t_h=t, severity="info",
                        message="Rebuild complete — protection restored",
                    ))

            # Capacity fill.
            used_data_tb += wl.ingest_tb_day / 24.0 / wl.reduction_ratio * DT_H
            snapshot_tb += (
                used_data_tb
                * (C("snapshot_ovh_per_snap_pct") / 100.0)
                * wl.snapshots_per_day / 24.0 * DT_H
            )
        else:
            cap_k = 0.0
            rho = 0.0
            hit = 0.0
            lat = 0.0
            srdf_ms = 0.0
            rpo_s = 0.0
            delivered_k = 0.0
            saturated = False
            throughput = 0.0

        raw = cfg.units * cfg.drives_per_unit * cfg.drive_tb
        ovh = C(PROTECTION_OVERHEAD[cfg.protection])
        usable = raw * (1.0 - ovh)
        effective = usable * wl.reduction_ratio
        used = min(used_data_tb + snapshot_tb, usable)
        used_pct = 100.0 * used / usable if usable else 0.0
        alert = "none"
        for th in ("95", "90", "80"):
            if used_pct >= int(th):
                alert = th
                break
        if alert != "none" and alert not in alerted:
            alerted.add(alert)
            log.append(LogEntry(
                t_h=t, severity="critical" if alert == "95" else "warning",
                message=f"Capacity {alert}% full — expansion or reclamation needed",
            ))

        # Exascale pool view + the GPU-starvation link.
        pool_util: dict[str, float] = {}
        gpu_idle = 0.0
        if p == "exascale":
            caps = pool_capacities_k(cfg)
            for name, share in POOL_SHARE.items():
                pool_demand = demand_k * share
                pool_cap = caps[name]
                pool_util[name] = round(
                    min(100.0 * pool_demand / pool_cap, 200.0) if pool_cap else 200.0, 1
                )
            read_k = demand_k * wl.read_pct / 100.0
            read_delivered = min(read_k, sum(
                min(demand_k * s, caps[n]) for n, s in POOL_SHARE.items()
            ) * wl.read_pct / 100.0)
            gpu_idle = (
                100.0 * (1.0 - read_delivered / read_k) if read_k > 0 else 0.0
            )
        elif online and demand_k > 0:
            gpu_idle = 100.0 * (1.0 - delivered_k / demand_k)

        util_pct = min(100.0 * rho, 200.0)
        rebuilding = rebuild_gb_left > 0
        exposure = rebuilding and failures_in_window >= survives

        # Map coloring (0–100 load) per product.
        if p == "powerstore":
            region_load = {
                "ctrl-a": round(util_pct, 1),
                "ctrl-b": round(0.0 if frontend_factor < 1.0 else util_pct, 1),
                "cache": round(100 * hit, 1),
                "media": round(used_pct, 1),
                "clients": round(min(100.0, util_pct), 1),
            }
        elif p == "powermax":
            region_load = {
                "directors": round(util_pct, 1),
                "gmem": round(100 * hit, 1),
                "media": round(used_pct, 1),
                "srdf": round(100.0 if cfg.srdf != "off" else 0.0, 1),
                "clients": round(min(100.0, util_pct), 1),
            }
        elif p in ("powerscale", "objectscale"):
            region_load = {
                "nodes": round(util_pct, 1),
                "media": round(used_pct, 1),
                "namespace": round(min(100.0, util_pct), 1),
                "network": round(min(100.0, util_pct * 0.7), 1),
                "clients": round(min(100.0, util_pct), 1),
            }
        elif p == "powerflex":
            net_k = network_cap_iops_k(cfg, units, wl.block_kb)
            region_load = {
                "nodes": round(util_pct, 1),
                "network": round(min(200.0, 100.0 * demand_k / net_k) if net_k else 0.0, 1),
                "media": round(used_pct, 1),
                "clients": round(min(100.0, util_pct), 1),
            }
        else:
            region_load = {
                "pool-lightning": pool_util.get("lightning", 0.0),
                "pool-file": pool_util.get("file", 0.0),
                "pool-object": pool_util.get("object", 0.0),
                "pool-block": pool_util.get("block", 0.0),
                "network": round(min(100.0, util_pct * 0.8), 1),
                "clients": round(min(100.0, gpu_idle), 1),
            }

        state = SimState(
            t_h=t,
            online=online,
            raw_tb=round(raw, 1),
            usable_tb=round(usable, 1),
            effective_tb=round(effective, 1),
            used_tb=round(used, 2),
            snapshot_tb=round(snapshot_tb, 2),
            used_pct=round(used_pct, 2),
            reduction_ratio=wl.reduction_ratio,
            capacity_alert=alert,  # type: ignore[arg-type]
            iops_capacity_k=round(cap_k, 1),
            iops_delivered_k=round(delivered_k, 1),
            iops_demand_k=round(demand_k, 1),
            throughput_gbs=round(throughput, 2),
            latency_ms=round(lat, 3),
            p99_ms=round(lat * C("p99_multiplier"), 3),
            utilization_pct=round(util_pct, 1),
            cache_hit_pct=round(100 * hit, 1),
            saturated=saturated,
            units_online=units,
            rebuilding=rebuilding,
            rebuild_pct=round(
                100.0 * (1 - rebuild_gb_left / rebuild_gb_total), 1
            ) if rebuild_gb_total and rebuilding else (100.0 if rebuild_gb_total else 0.0),
            rebuild_hours_left=round(
                rebuild_gb_left / (C("rebuild_gbps_controller") * 3600), 2
            ) if (rebuilding and controller_array) else round(
                rebuild_gb_left / (C("rebuild_gbps_per_node") * max(units - 1, 1) * 3600), 2
            ) if rebuilding else 0.0,
            exposure=exposure,
            srdf_latency_ms=round(srdf_ms, 3),
            rpo_seconds=round(rpo_s, 1),
            pool_util_pct=pool_util,
            gpu_idle_due_to_data_pct=round(gpu_idle, 1),
            region_load=region_load,
        )
        trace.append(state)

        peak_lat = max(peak_lat, lat)
        if online and demand_k > 0:
            min_ratio = min(min_ratio, delivered_k / demand_k)
        if saturated:
            hours_saturated += 1

    last = trace[-1]
    summary = Summary(
        peak_latency_ms=round(peak_lat, 3),
        steady_latency_ms=last.latency_ms,
        min_delivered_ratio=round(min_ratio, 3),
        hours_saturated=hours_saturated,
        rebuild_hours=round(rebuild_hours, 1),
        final_used_pct=last.used_pct,
        data_survived=data_survived,
    )
    return trace, log, summary
