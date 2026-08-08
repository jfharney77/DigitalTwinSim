"""Every model constant with units and a source — fleet-operations
edition. Admin-hour figures are the load-bearing estimates here; the
lesson is the order-of-magnitude gap, not the absolute hours."""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- Faults & drift -----------------------------------------------------
    "fault_node_days": Constant(
        value=3000, unit="node-days per fault",
        source="estimate — spec 04's ~1 fault per 100 node-months, made deterministic",
        estimated=True,
        blurb="A hardware fault arrives every N node-days, rotating around the fleet.",
    ),
    "drift_per_node_day": Constant(
        value=0.05, unit="drift points/node/day",
        source="estimate — unmanaged config entropy", estimated=True,
        blurb="Config drift accumulated per manually-managed node per day.",
    ),
    # --- Admin-hours: the teaching table (spec 04 ops model) ---------------
    "deploy_site_manual_h": Constant(
        value=8, unit="h/site",
        source="estimate — spec 04: site visit ≈ 8 admin-hours + travel", estimated=True,
        blurb="Deploying one site by hand (travel folded in).",
    ),
    "deploy_site_zerotouch_h": Constant(
        value=0.5, unit="h/site",
        source="estimate — claim a device, assign a blueprint", estimated=True,
        blurb="Deploying one site zero-touch.",
    ),
    "patch_node_manual_h": Constant(
        value=2.0, unit="h/node",
        source="estimate — ESXi + firmware + drivers, per node, by hand",
        estimated=True,
        blurb="Patching one node manually (compatibility matrix included).",
    ),
    "patch_node_auto_h": Constant(
        value=0.2, unit="h/node",
        source="estimate — one-click rolling update, attended lightly",
        estimated=True,
        blurb="Patching one node via orchestrated lifecycle management.",
    ),
    "remediate_manual_h": Constant(
        value=6, unit="h/fault",
        source="estimate — diagnose, dispatch, rebuild", estimated=True,
        blurb="Remediating a fault by hand.",
    ),
    "remediate_auto_h": Constant(
        value=1, unit="h/fault",
        source="estimate — automated remediation, human approves", estimated=True,
        blurb="Remediating a fault with central automation.",
    ),
    "truck_roll_h": Constant(
        value=8, unit="h/visit",
        source="estimate — drive to the site, fix, drive back", estimated=True,
        blurb="Extra hours when a remote site needs a physical visit.",
    ),
    "drift_fix_h": Constant(
        value=0.5, unit="h/drift point", source="estimate", estimated=True,
        blurb="Reconciling one accumulated drift point by hand.",
    ),
    "catalog_deploy_h": Constant(
        value=0.25, unit="h/workload",
        source="estimate — spec 04: catalog deploy = minutes", estimated=True,
        blurb="Deploying a workload from the self-service catalog.",
    ),
    "artisanal_deploy_h": Constant(
        value=16, unit="h/workload",
        source="estimate — spec 04: manual stack install = days", estimated=True,
        blurb="Standing the same workload up by hand.",
    ),
    "admin_capacity_h_day": Constant(
        value=16, unit="h/day",
        source="estimate — a two-person platform team's realistic ops budget",
        estimated=True,
        blurb="Admin-hours available per day; work beyond it backlogs (and versions age).",
    ),
    # --- HA & availability ---------------------------------------------------
    "ha_failover_minutes": Constant(
        value=2, unit="min",
        source="estimate — VM restart on a surviving node", estimated=True,
        blurb="Downtime when a fault lands and N+1 headroom exists.",
    ),
    "no_headroom_outage_minutes": Constant(
        value=240, unit="min",
        source="estimate — wait for repair before workloads return", estimated=True,
        blurb="Downtime when a fault lands with nowhere to restart.",
    ),
    "edge_truck_outage_minutes": Constant(
        value=1440, unit="min",
        source="estimate — single-node remote site waits a day for a visit",
        estimated=True,
        blurb="Downtime for a non-HA edge-site fault (the truck-roll day).",
    ),
    "bad_change_outage_minutes": Constant(
        value=240, unit="min",
        source="estimate — the Friday-night change, ungated", estimated=True,
        blurb="Outage when a bad change reaches production without a test gate.",
    ),
    "update_days": Constant(
        value=30, unit="days", source="spec 04 — updates are released monthly",
        estimated=False,
        blurb="Days between software updates arriving.",
    ),
    # --- APEX economics (spec 04: the lesson is the shape, not the price) ----
    "asvc_base_per_vm_month": Constant(
        value=30, unit="$/VM/month committed",
        source="estimate — the lesson is the shape, not the price", estimated=True,
        blurb="As-a-service committed rate per VM-month.",
    ),
    "asvc_overage_per_vm_month": Constant(
        value=45, unit="$/VM/month above base",
        source="estimate — overage premium ~1.5×", estimated=True,
        blurb="Rate for usage above the committed base.",
    ),
    "capex_per_vm_month": Constant(
        value=24, unit="$/VM/month of installed capacity",
        source="estimate — purchase amortized over 4 years", estimated=True,
        blurb="Owned-capacity cost per VM-month of capacity; ownership must buy the peak, idle or not.",
    ),
    "seasonal_amplitude": Constant(
        value=0.4, unit="fraction", source="estimate", estimated=True,
        blurb="Seasonal demand swing (±40% around the mean, 90-day period).",
    ),
    "spiky_amplitude": Constant(
        value=1.5, unit="× mean during spikes", source="estimate", estimated=True,
        blurb="Spike height; spikes run 10 days in 60.",
    ),
}


def value(name: str) -> float:
    return CONSTANTS[name].value
