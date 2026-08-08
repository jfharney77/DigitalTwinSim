"""Pure fleet-operations engine (physics_specs/04). Tick = one sim-day.

The teaching core is the **admin-hours ledger**: every action — deploy
a site, patch a node, remediate a fault, reconcile drift — costs hours,
and the automation mode changes the cost by an order of magnitude.
Around it: deterministic MTBF faults (one per N node-days, rotating),
N+1 headroom math deciding whether a fault is a 2-minute failover or an
outage, monthly updates that manual fleets fall behind on (bounded by
the team's daily hour budget), drift that accumulates on unmanaged
nodes, and the APEX cost model (committed base + overage vs amortized
ownership) running as Archetype F on top.
"""

from __future__ import annotations

import math

from .constants import value as C
from .models import (
    FleetConfig,
    LogEntry,
    Scenario,
    SimState,
    Summary,
    Workload,
)

DT_D = 1.0


def demand_multiplier(curve: str, day: int) -> float:
    if curve == "seasonal":
        return 1.0 + C("seasonal_amplitude") * math.sin(2 * math.pi * day / 90.0)
    if curve == "spiky":
        return C("spiky_amplitude") if (day % 60) < 10 else 0.85
    return 1.0


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    wl: Workload = scenario.workload
    events = sorted(scenario.events, key=lambda e: e.at_d)
    p = cfg.product
    automated = cfg.ops_mode == "automated"
    edge = p == "nativeedge"

    sites = cfg.sites
    nodes_per = cfg.nodes_per_site
    nodes_down = 0                     # faulted, awaiting remediation
    node_day_acc = 0.0
    faults = 0
    truck_rolls = 0
    drift = 0.0
    outage_min = 0.0
    version_current = 1.0              # fraction of fleet on latest software
    backlog_h = 0.0                    # ops work waiting for hours
    hours_cum = 0.0
    hours_window: list[float] = []
    updating_until = -1
    wan_down_until = -1
    demand_spike_until = -1
    spike_mult = 1.0
    vms_demand = float(wl.vms_per_site * sites)
    bill_cum = 0.0
    asvc_cost_acc = 0.0
    capex_cost_acc = 0.0
    vm_hours_acc = 0.0

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0

    steps = int(scenario.duration_d / DT_D)
    for step in range(steps + 1):
        t = int(step * DT_D)
        hours_today = 0.0

        # --- Events -------------------------------------------------------
        while ei < len(events) and events[ei].at_d <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "deploy-sites" and ev.value is not None:
                n = int(ev.value)
                per_site = (
                    C("deploy_site_zerotouch_h") if (automated and edge)
                    else C("deploy_site_manual_h")
                )
                sites += n
                vms_demand += wl.vms_per_site * n
                backlog_h += n * per_site
                log.append(LogEntry(
                    t_d=t, severity="info",
                    message=(
                        f"{n} sites deployed — "
                        f"{n * per_site:.0f} admin-hours "
                        f"({'zero-touch' if automated and edge else 'site visits'})"
                    ),
                ))
            elif ev.action == "node-fault":
                faults += 1
                nodes_down += 1
                log.append(LogEntry(t_d=t, severity="warning",
                                    message="Node fault (injected)"))
            elif ev.action == "cluster-update":
                updating_until = t + (2 if automated else 7)
                log.append(LogEntry(
                    t_d=t, severity="info",
                    message="Cluster update started"
                    + (" — rolling, one click" if automated
                       else " — manual, node by node"),
                ))
            elif ev.action == "bad-change":
                if p == "automationstudio" and cfg.test_gate:
                    log.append(LogEntry(
                        t_d=t, severity="warning",
                        message="Bad change CAUGHT IN TEST — the gate held; production never saw it",
                    ))
                    backlog_h += 2.0
                else:
                    outage_min += C("bad_change_outage_minutes")
                    backlog_h += 8.0
                    log.append(LogEntry(
                        t_d=t, severity="critical",
                        message="Bad change reached production — outage while it was rolled back",
                    ))
            elif ev.action == "wan-outage" and ev.value is not None:
                wan_down_until = t + int(ev.value)
                log.append(LogEntry(
                    t_d=t, severity="warning",
                    message=f"WAN down for {ev.value:g} days — sites running autonomously",
                ))
            elif ev.action == "demand-spike" and ev.value is not None:
                spike_mult = ev.value
                demand_spike_until = t + 30
                log.append(LogEntry(t_d=t, severity="info",
                                    message=f"Demand spike ×{ev.value:g} for 30 days"))

        # --- Growth & demand ----------------------------------------------
        vms_demand *= 1.0 + wl.growth_pct_month / 100.0 / 30.0
        mult = demand_multiplier(cfg.demand_curve, t) if p == "apex" else 1.0
        if t <= demand_spike_until:
            mult *= spike_mult
        demand_now = vms_demand * mult

        # --- Deterministic MTBF faults ------------------------------------
        nodes_total = sites * nodes_per
        node_day_acc += nodes_total * DT_D
        while node_day_acc >= C("fault_node_days"):
            node_day_acc -= C("fault_node_days")
            faults += 1
            nodes_down += 1
            log.append(LogEntry(t_d=t, severity="warning",
                                message="Node fault (wear schedule)"))

        # --- HA math: does the fleet absorb what's down? -------------------
        nodes_healthy = nodes_total - nodes_down
        capacity = nodes_healthy * wl.vm_size_capacity
        tolerated = cfg.ftt if p == "vxrail" else 1
        if nodes_down > 0:
            per_site_down = nodes_down  # worst case: same cluster
            if edge and not cfg.two_node_ha:
                outage_min += C("edge_truck_outage_minutes") / max(sites, 1) \
                    * nodes_down
                truck_rolls += nodes_down
            elif nodes_per - per_site_down >= 1 and capacity >= demand_now \
                    and per_site_down <= tolerated:
                outage_min += C("ha_failover_minutes") * nodes_down
            else:
                outage_min += C("no_headroom_outage_minutes")
        exposure = (
            p == "vxrail" and nodes_down >= tolerated and nodes_down > 0
        ) or (nodes_per - nodes_down < 1 + tolerated and nodes_down > 0)

        # Remediation consumes hours; remote sites may need a truck.
        if nodes_down > 0:
            per_fault = C("remediate_auto_h") if automated else C("remediate_manual_h")
            if edge and not automated:
                per_fault += C("truck_roll_h")
                truck_rolls += nodes_down
            backlog_h += per_fault * nodes_down
            nodes_down = 0  # remediation queued; hardware recovers

        # --- Monthly update wave ------------------------------------------
        if t > 0 and t % int(C("update_days")) == 0:
            per_node = C("patch_node_auto_h") if automated else C("patch_node_manual_h")
            backlog_h += nodes_total * per_node
            version_current = 0.0
            updating_until = max(updating_until, t + (2 if automated else 14))
            log.append(LogEntry(
                t_d=t, severity="info",
                message=f"Update released — {nodes_total * per_node:.0f} h of patching queued",
            ))

        # --- Drift ---------------------------------------------------------
        wan_down = t <= wan_down_until
        if not automated or wan_down:
            drift += nodes_total * C("drift_per_node_day") * DT_D
        elif drift > 0:
            reconciled = min(drift, nodes_total * 0.2)
            drift -= reconciled
            if drift < 0.5:
                drift = 0.0

        # --- Spend the day's admin hours -----------------------------------
        available = C("admin_capacity_h_day")
        spend = min(backlog_h, available)
        backlog_h -= spend
        hours_today += spend
        # Patch progress: version currency recovers as its hours are worked.
        per_node = C("patch_node_auto_h") if automated else C("patch_node_manual_h")
        fleet_patch_hours = nodes_total * per_node
        if version_current < 1.0 and fleet_patch_hours > 0:
            version_current = min(1.0, version_current + spend / fleet_patch_hours)
        # Manual drift-fixing eats hours too (automated reconciles free).
        if not automated and drift > 0 and available - spend > 0:
            fix = min(drift, (available - spend) / C("drift_fix_h"))
            drift -= fix
            hours_today += fix * C("drift_fix_h")

        hours_cum += hours_today
        hours_window.append(hours_today)
        if len(hours_window) > 30:
            hours_window.pop(0)

        # --- Serve demand --------------------------------------------------
        vms_running = min(demand_now, capacity)
        if demand_now > capacity and t % 7 == 0:
            log.append(LogEntry(
                t_d=t, severity="critical",
                message="Capacity outage — demand above installed capacity",
            ))
            outage_min += 120.0
        headroom = 100.0 * (capacity - demand_now) / capacity if capacity else 0.0

        # --- APEX economics -------------------------------------------------
        base = cfg.committed_vms
        buffer_cap = base * (1.0 + cfg.buffer_pct / 100.0)
        served_asvc = min(demand_now, buffer_cap)
        overage = max(0.0, served_asvc - base)
        bill_day = (
            base * C("asvc_base_per_vm_month")
            + overage * C("asvc_overage_per_vm_month")
        ) / 30.0
        bill_cum += bill_day
        # Ownership must buy the demand curve's peak, idle or not.
        peak_factor = {
            "steady": 1.0,
            "seasonal": 1.0 + C("seasonal_amplitude"),
            "spiky": C("spiky_amplitude"),
        }[cfg.demand_curve]
        capex_capacity = base * peak_factor
        capex_day = capex_capacity * C("capex_per_vm_month") / 30.0
        asvc_cost_acc += bill_day
        capex_cost_acc += capex_day
        vm_hours_acc += served_asvc * 24.0
        util = 100.0 * served_asvc / base if base else 0.0
        if p == "apex" and demand_now > buffer_cap:
            outage_min += 60.0
            if t % 7 == 0:
                log.append(LogEntry(
                    t_d=t, severity="critical",
                    message="Demand above base+buffer — capacity outage (the too-small buffer)",
                ))

        total_min = (t + 1) * 24 * 60 * max(sites, 1)
        availability = 100.0 * (1.0 - outage_min / total_min)

        month_rate = sum(hours_window) / len(hours_window) * 30.0

        region_load = {
            "controlplane": round(100.0 if automated else 20.0, 1),
            "sites": round(min(100.0, 100.0 * sites / max(cfg.sites, 1) - 0.0), 1),
            "nodes": round(100.0 * (nodes_total - nodes_down) / max(nodes_total, 1), 1),
            "workloads": round(min(100.0, 100.0 * vms_running / max(capacity, 1)), 1),
            "ops": round(min(100.0, month_rate / 5.0), 1),
            "economics": round(min(100.0, util), 1),
            "pipeline": round(100.0 if (p == "automationstudio" and cfg.test_gate) else 0.0, 1),
            "catalog": round(100.0 if cfg.catalog else 0.0, 1),
            "wan": round(0.0 if wan_down else 100.0, 1),
        }

        trace.append(SimState(
            t_d=t,
            admin_hours_today=round(hours_today, 2),
            admin_hours_cum=round(hours_cum, 1),
            admin_hours_per_month=round(month_rate, 1),
            sites_deployed=sites,
            nodes_total=nodes_total,
            nodes_healthy=nodes_total - nodes_down,
            vms_running=int(vms_running),
            vms_demand=int(demand_now),
            capacity_vms=int(capacity),
            headroom_pct=round(headroom, 1),
            exposure=exposure,
            version_current_pct=round(100.0 * version_current, 1),
            drift_count=int(drift),
            outage_minutes_cum=round(outage_min, 1),
            availability_pct=round(availability, 4),
            truck_rolls=truck_rolls,
            faults_cum=faults,
            updating=t <= updating_until,
            monthly_bill=round(bill_day * 30.0, 0),
            commitment_utilization_pct=round(util, 1),
            cost_per_vm_hour_asvc=round(
                asvc_cost_acc / vm_hours_acc, 4
            ) if vm_hours_acc else 0.0,
            cost_per_vm_hour_capex=round(
                capex_cost_acc / vm_hours_acc, 4
            ) if vm_hours_acc else 0.0,
            region_load=region_load,
        ))

    last = trace[-1]
    summary = Summary(
        admin_hours_total=round(hours_cum, 1),
        availability_pct=last.availability_pct,
        outage_minutes=round(outage_min, 1),
        truck_rolls=truck_rolls,
        faults=faults,
        final_version_current_pct=last.version_current_pct,
        total_bill=round(bill_cum, 0),
        mean_cost_per_vm_hour_asvc=last.cost_per_vm_hour_asvc,
        mean_cost_per_vm_hour_capex=last.cost_per_vm_hour_capex,
    )
    return trace, log, summary
