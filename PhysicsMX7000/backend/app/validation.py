"""The validation-rules engine: evaluated on every config change, each
rule yielding ok | warning | error with a human-readable explanation and a
source citation — a miniature of the chassis planning guide, which for a
modular chassis is mostly *pool arithmetic*.

Pure module: no FastAPI, no IO — rules are data in, findings out.
"""

from __future__ import annotations

from .constants import value as C
from .engine import compute_sled_power, psu_feed, storage_sled_power
from .models import ChassisConfig, Scenario, SledLoad, Validation

FULL = SledLoad(cpu_pct=100, mem_pct=100, storage_pct=100)


def _max_theoretical_dc(cfg: ChassisConfig) -> float:
    """Worst-case DC draw: every occupied sled flat out, fans at max."""
    total = 0.0
    for sled in cfg.sleds:
        if sled.kind == "compute":
            total += compute_sled_power(sled, FULL, 1.0)
        elif sled.kind == "storage":
            total += storage_sled_power(100.0)
    total += 2 * C("fabric_iom_w") + 2 * C("mgmt_module_w")
    total += C("fan_count") * C("fan_pmax_w")
    return total


def _surviving_capacity(cfg: ChassisConfig) -> tuple[float, str]:
    """The pool that must carry the chassis after the covered failure —
    which failure is covered depends on the policy."""
    cap = C("psu_capacity_w")
    if cfg.redundancy == "grid":
        # Survive a whole-feed loss: the smaller feed's PSUs must carry it.
        a = sum(1 for i in range(cfg.psu_count) if psu_feed(i, cfg) == "A")
        b = cfg.psu_count - a
        return min(a, b) * cap, "the surviving feed's PSUs"
    if cfg.redundancy == "n+1":
        return (cfg.psu_count - 1) * cap, "N−1 PSUs"
    return cfg.psu_count * cap, "the whole pool (no failure covered)"


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    env = scenario.environment
    out: list[Validation] = []

    # Rule 1 — grid redundancy needs an even split across the two feeds.
    if cfg.redundancy == "grid" and cfg.psu_count % 2 != 0:
        out.append(Validation(
            rule_id="grid-split", level="error",
            message=(
                f"Grid redundancy splits PSUs across two AC feeds, and "
                f"{cfg.psu_count} does not split evenly — one feed would "
                "carry more than half the pool. Use 2, 4, or 6 PSUs."
            ),
            source="Dell MX7000 power configuration guidance (grid redundancy)",
        ))
    else:
        out.append(Validation(
            rule_id="grid-split", level="ok",
            message="PSU count is legal for the chosen redundancy policy.",
            source="Dell MX7000 power configuration guidance (grid redundancy)",
        ))

    # Rule 2 — worst-case draw vs the pool that survives the covered failure.
    max_dc = _max_theoretical_dc(cfg)
    budget, who = _surviving_capacity(cfg)
    if max_dc > budget:
        out.append(Validation(
            rule_id="psu-budget", level="warning",
            message=(
                f"Worst-case draw ≈ {max_dc:.0f} W exceeds the {budget:.0f} W "
                f"that {who} could carry after the failure your policy is "
                "supposed to cover. The simulator will let you try it — and "
                "will trip the pool if the overload sustains "
                f"({C('psu_overcurrent_trip_seconds'):g} s at "
                f"{100 * (C('psu_overcurrent_trip_fraction') - 1):.0f}% over)."
            ),
            source="pool arithmetic — warn, don't block; simulate the consequence",
        ))
    else:
        out.append(Validation(
            rule_id="psu-budget", level="ok",
            message=(
                f"Worst-case draw ≈ {max_dc:.0f} W fits the {budget:.0f} W "
                f"that {who} would still supply."
            ),
            source="pool arithmetic",
        ))

    # Rule 3 — every storage sled must be owned by a compute sled.
    bad = []
    for i, sled in enumerate(cfg.sleds):
        if sled.kind != "storage":
            continue
        owner = sled.owner_slot
        ok = (
            owner is not None and 1 <= owner <= len(cfg.sleds)
            and cfg.sleds[owner - 1].kind == "compute"
        )
        if not ok:
            bad.append(i + 1)
    if bad:
        out.append(Validation(
            rule_id="storage-owner", level="error",
            message=(
                f"Storage sled(s) {', '.join(map(str, bad))} are not mapped "
                "to a compute sled. A storage sled has no workload of its "
                "own — assign it an owner (that mapping is the composability "
                "feature, and it can be changed mid-run)."
            ),
            source="Dell MX5016s storage sled — drives map to compute sleds",
        ))
    else:
        out.append(Validation(
            rule_id="storage-owner", level="ok",
            message="Every storage sled is mapped to a compute sled.",
            source="Dell MX5016s storage sled — drives map to compute sleds",
        ))

    # Rule 4 — a single AC feed is a single point of failure.
    if cfg.redundancy != "grid":
        out.append(Validation(
            rule_id="feed", level="warning",
            message=(
                "All PSUs share one AC feed under this policy. N+1 survives "
                "a PSU failing; it does not survive the feed failing — grid "
                "redundancy is what splits the pool across two feeds."
            ),
            source="Dell MX7000 power configuration guidance (grid vs N+1)",
        ))
    else:
        out.append(Validation(
            rule_id="feed", level="ok",
            message="Grid redundancy: the pool is split across two AC feeds.",
            source="Dell MX7000 power configuration guidance (grid vs N+1)",
        ))

    # Rule 5 — top-TDP sleds in a warm room.
    if env.inlet_c > C("ashrae_a2_recommended_c") and any(
        s.kind == "compute" and s.cpu_tdp_w >= 350 for s in cfg.sleds
    ):
        out.append(Validation(
            rule_id="ambient", level="warning",
            message=(
                f"350 W-class sleds above {C('ashrae_a2_recommended_c'):g} °C "
                "inlet: the shared fans will spend real watts holding the "
                "hottest sled to target, and every bay pays for it."
            ),
            source="estimate — refine against Dell's MX thermal restrictions",
        ))

    return out
