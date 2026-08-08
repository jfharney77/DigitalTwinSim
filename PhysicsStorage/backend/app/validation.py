"""Validation rules for the storage simulator. House rule: warn about
what the simulator can demonstrate, error only on configurations that
are contradictions. Pure module."""

from __future__ import annotations

from .constants import PROTECTION_SURVIVES
from .engine import iops_capacity_k, network_cap_iops_k
from .models import Scenario, Validation

MIN_UNITS = {
    "powerstore": 1, "powermax": 1, "powerscale": 3,
    "objectscale": 4, "powerflex": 4, "exascale": 8,
}
MAX_UNITS = {
    "powerstore": 4, "powermax": 8, "powerscale": 100,
    "objectscale": 100, "powerflex": 100, "exascale": 100,
}


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    wl = scenario.workload
    p = cfg.product
    out: list[Validation] = []

    # Rule 1 — cluster size limits.
    lo, hi = MIN_UNITS[p], MAX_UNITS[p]
    if not (lo <= cfg.units <= hi):
        out.append(Validation(
            rule_id="units", level="error",
            message=(
                f"{p} runs {lo}–{hi} units; {cfg.units} is outside the "
                "product's envelope."
            ),
            source="spec 02 per-product config ranges (verify against Dell spec sheets)",
        ))
    else:
        out.append(Validation(
            rule_id="units", level="ok",
            message=f"{cfg.units} units is a legal {p} cluster.",
            source="spec 02",
        ))

    # Rule 2 — demand vs capacity: warn, then let the knee demonstrate it.
    cap = iops_capacity_k(cfg, cfg.units, wl.block_kb)
    if wl.iops_demand_k > cap:
        out.append(Validation(
            rule_id="capacity", level="warning",
            message=(
                f"Demand {wl.iops_demand_k}k IOPS exceeds the configured "
                f"ceiling ≈ {cap:.0f}k. The simulator will show you the "
                "knee, then the plateau."
            ),
            source="spec 02 — the queueing lesson, not a blocker",
        ))
    elif cap > 0 and wl.iops_demand_k > 0.85 * cap:
        out.append(Validation(
            rule_id="capacity", level="warning",
            message=(
                f"Demand is {100 * wl.iops_demand_k / cap:.0f}% of the "
                "ceiling — you are living on the knee."
            ),
            source="spec 02",
        ))
    else:
        out.append(Validation(
            rule_id="capacity", level="ok",
            message=f"Demand sits at {100 * wl.iops_demand_k / cap:.0f}% of ≈ {cap:.0f}k IOPS." if cap else "No capacity configured.",
            source="spec 02",
        ))

    # Rule 3 — PowerFlex: is the network the binding constraint?
    if p == "powerflex":
        net = network_cap_iops_k(cfg, cfg.units, wl.block_kb)
        node = cfg.units * 150.0
        if net < node:
            out.append(Validation(
                rule_id="network", level="warning",
                message=(
                    f"{cfg.nic_gbps} GbE NICs cap the pool at ≈ {net:.0f}k "
                    f"IOPS — below the nodes' ≈ {node:.0f}k. The network "
                    "is the array; buy bandwidth before drives."
                ),
                source="spec 02 — PowerFlex personality",
            ))

    # Rule 4 — sync replication distance.
    if p == "powermax" and cfg.srdf == "sync" and cfg.distance_km > 200:
        out.append(Validation(
            rule_id="srdf-distance", level="warning",
            message=(
                f"{cfg.distance_km} km of sync SRDF adds "
                f"{cfg.distance_km * 0.02:.1f} ms to every write — beyond "
                "typical sync radii. Physics, not firmware: consider "
                "async past ~100–200 km."
            ),
            source="speed of light in fiber — 0.01 ms/km each way",
        ))

    # Rule 5 — HDD under a transactional load.
    if cfg.drive_class == "hdd" and wl.block_kb <= 16 and wl.iops_demand_k > 50:
        out.append(Validation(
            rule_id="hdd-oltp", level="warning",
            message=(
                "Small-block random demand on spinning disks: 8 ms media "
                "latency puts the knee three orders of magnitude below "
                "flash. Watch it happen, then buy NVMe."
            ),
            source="spec 02 media table",
        ))

    # Rule 6 — protection sanity for big clusters.
    if p in ("powerscale", "objectscale", "powerflex") and cfg.units >= 20 \
            and PROTECTION_SURVIVES[cfg.protection] < 2:
        out.append(Validation(
            rule_id="protection", level="warning",
            message=(
                f"{cfg.units} nodes protected to survive only one "
                "failure: at this scale a second failure during a "
                "rebuild window is a when, not an if."
            ),
            source="estimate — rebuild-window exposure argument, spec 02",
        ))

    # Rule 7 — Exascale partition must cover the pool.
    if p == "exascale":
        assigned = (
            cfg.lightning_units + cfg.file_units + cfg.object_units
            + cfg.block_units
        )
        if assigned != cfg.units:
            out.append(Validation(
                rule_id="partition", level="error",
                message=(
                    f"Partition assigns {assigned} of {cfg.units} nodes — "
                    "the split must use exactly the pool."
                ),
                source="spec 02 — Exascale meta-simulator",
            ))
        else:
            out.append(Validation(
                rule_id="partition", level="ok",
                message="The node pool is fully partitioned.",
                source="spec 02",
            ))

    return out
