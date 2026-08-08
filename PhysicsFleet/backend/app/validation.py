"""Validation rules for the fleet simulator. Pure module."""

from __future__ import annotations

from .constants import value as C
from .models import Scenario, Validation


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    wl = scenario.workload
    p = cfg.product
    out: list[Validation] = []

    # Rule 1 — the 3-node trap (spec 04's VxRail scenario as a rule).
    if p == "vxrail":
        if cfg.nodes_per_site <= 3 and cfg.ftt >= 1:
            out.append(Validation(
                rule_id="three-node", level="warning",
                message=(
                    f"{cfg.nodes_per_site}-node cluster at FTT={cfg.ftt}: "
                    "one node down leaves no rebuild target — the "
                    "exposure window stays open until repair. Minimums "
                    "are arithmetic, not upsell."
                ),
                source="spec 04 — the 3-node trap",
            ))
        elif cfg.nodes_per_site >= 4:
            out.append(Validation(
                rule_id="three-node", level="ok",
                message=f"{cfg.nodes_per_site} nodes give FTT={cfg.ftt} a rebuild target.",
                source="spec 04",
            ))

    # Rule 2 — N+1 headroom vs demand.
    capacity = cfg.sites * cfg.nodes_per_site * wl.vm_size_capacity
    n1_capacity = cfg.sites * (cfg.nodes_per_site - 1) * wl.vm_size_capacity
    demand = cfg.sites * wl.vms_per_site
    if demand > capacity:
        out.append(Validation(
            rule_id="capacity", level="error",
            message=(
                f"Demand {demand} VMs exceeds installed capacity "
                f"{capacity} — this fleet is undersized before anything "
                "fails."
            ),
            source="spec 04 — placement math",
        ))
    elif demand > n1_capacity:
        out.append(Validation(
            rule_id="capacity", level="warning",
            message=(
                f"Demand {demand} VMs fits installed capacity but not "
                f"N+1 ({n1_capacity}): the first fault becomes an "
                "outage, not a failover."
            ),
            source="spec 04 — N+1 headroom math",
        ))
    else:
        out.append(Validation(
            rule_id="capacity", level="ok",
            message=f"Demand {demand} VMs fits inside N+1 headroom.",
            source="spec 04",
        ))

    # Rule 3 — manual ops at scale is a math problem.
    if cfg.ops_mode == "manual":
        nodes = cfg.sites * cfg.nodes_per_site
        patch_h = nodes * C("patch_node_manual_h")
        days = patch_h / C("admin_capacity_h_day")
        if days > C("update_days"):
            out.append(Validation(
                rule_id="ops-scale", level="warning",
                message=(
                    f"Manually patching {nodes} nodes costs ≈ "
                    f"{patch_h:.0f} h ≈ {days:.0f} team-days — longer "
                    "than the monthly release cycle. This fleet can "
                    "never be current; watch the version gauge prove it."
                ),
                source="spec 04 — the ops model's core arithmetic",
            ))

    # Rule 4 — single-node edge sites without HA.
    if p == "nativeedge" and cfg.nodes_per_site == 1 and not cfg.two_node_ha:
        out.append(Validation(
            rule_id="edge-ha", level="warning",
            message=(
                "Single-node sites, no HA: every hardware fault is a "
                "truck roll and a day of downtime for that site. The "
                "2-node option is the difference between a log line "
                "and a drive."
            ),
            source="spec 04 — 2-node HA at the edge",
        ))

    # Rule 5 — APEX buffer sanity.
    if p == "apex":
        demand_now = cfg.sites * wl.vms_per_site
        buffer_cap = cfg.committed_vms * (1 + cfg.buffer_pct / 100)
        if demand_now > buffer_cap:
            out.append(Validation(
                rule_id="buffer", level="warning",
                message=(
                    f"Mean demand {demand_now} VMs already exceeds "
                    f"base+buffer ({buffer_cap:.0f}) — capacity outages "
                    "before any spike arrives."
                ),
                source="spec 04 — the buffer decision",
            ))
        elif demand_now < cfg.committed_vms * 0.6:
            out.append(Validation(
                rule_id="buffer", level="warning",
                message=(
                    f"Mean demand {demand_now} VMs is under 60% of the "
                    f"{cfg.committed_vms}-VM commitment — paying for "
                    "air. Under-use still pays base."
                ),
                source="spec 04 — under-commitment costs too",
            ))
        else:
            out.append(Validation(
                rule_id="buffer", level="ok",
                message="Commitment and buffer bracket the mean demand sensibly.",
                source="spec 04",
            ))

    return out
