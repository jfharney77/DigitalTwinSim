"""Validation rules for the fabric simulator. Pure module."""

from __future__ import annotations

from .constants import value as C
from .engine import oversub_ratio, poe_demand_w
from .models import Scenario, Validation


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    wl = scenario.workload
    p = cfg.product
    out: list[Validation] = []

    # Rule 1 — oversubscription ratio, stated up front (spec 03's first
    # core lesson: displayed prominently).
    ratio = oversub_ratio(cfg)
    if p != "e3200":
        if ratio > 3.0:
            level = "warning"
            msg = (
                f"Oversubscription {ratio:.1f}:1 — congestion will appear "
                "exactly where this ratio predicts. AI fabrics are built "
                "1:1 for a reason."
            )
        elif ratio > 1.0:
            level = "ok"
            msg = f"Oversubscription {ratio:.1f}:1 — modest, survivable for mixed traffic."
        else:
            level = "ok"
            msg = f"Non-blocking ({ratio:.1f}:1) — the fabric can carry every endpoint flat out."
        out.append(Validation(
            rule_id="oversub", level=level, message=msg,
            source="spec 03 — downlink ÷ uplink per leaf",
        ))

    # Rule 2 — demand vs bisection.
    if p != "e3200":
        bisection = cfg.leaves * cfg.spines * cfg.uplink_gbps
        if wl.demand_gbps > bisection:
            out.append(Validation(
                rule_id="bisection", level="warning",
                message=(
                    f"Demand {wl.demand_gbps} Gb/s exceeds the "
                    f"{bisection} Gb/s bisection — the fabric cannot carry "
                    "it even perfectly balanced. Watch the personality "
                    "decide what happens to the excess."
                ),
                source="spec 03 — bisection bandwidth",
            ))
        else:
            out.append(Validation(
                rule_id="bisection", level="ok",
                message=f"Demand fits the {bisection} Gb/s bisection.",
                source="spec 03",
            ))

    # Rule 3 — the PoE budget binds first (spec 03: E3200's headline rule).
    if p == "e3200":
        demand_w = poe_demand_w(cfg)
        if demand_w > cfg.poe_budget_w:
            out.append(Validation(
                rule_id="poe", level="error",
                message=(
                    f"PoE demand ≈ {demand_w:.0f} W exceeds the "
                    f"{cfg.poe_budget_w} W budget — devices will shed by "
                    "priority (phones, cameras, then APs). The budget "
                    "runs out before the ports do."
                ),
                source="spec 03 — PoE budget vs device sum; per-device draws are estimates",
            ))
        elif demand_w > 0.8 * cfg.poe_budget_w:
            out.append(Validation(
                rule_id="poe", level="warning",
                message=(
                    f"PoE at {100 * demand_w / cfg.poe_budget_w:.0f}% of "
                    "budget — one PSU loss halves it and sheds devices."
                ),
                source="spec 03",
            ))
        else:
            out.append(Validation(
                rule_id="poe", level="ok",
                message=f"PoE demand ≈ {demand_w:.0f} W fits the {cfg.poe_budget_w} W budget.",
                source="spec 03",
            ))

    # Rule 4 — product-feature sanity.
    if cfg.sharp and p != "x800":
        out.append(Validation(
            rule_id="sharp", level="error",
            message="SHARP in-network collectives are the InfiniBand personality's feature.",
            source="spec 03 — X800 personality",
        ))
    if (cfg.adaptive_routing or cfg.lossless_roce or cfg.cpo_optics) and p == "e3200":
        out.append(Validation(
            rule_id="features", level="error",
            message="Adaptive routing / RoCE / CPO are datacenter-fabric features, not campus ones.",
            source="spec 03",
        ))

    # Rule 5 — elephant flows without adaptive routing.
    if p == "sn6000" and wl.pattern == "elephant" and not cfg.adaptive_routing:
        out.append(Validation(
            rule_id="elephants", level="warning",
            message=(
                "Elephant flows on static ECMP: expect the worst link at "
                f"~{(1 + C('imbalance_elephant')) * 100:.0f}% of fair share "
                "while its neighbors idle. Adaptive routing exists for "
                "exactly this."
            ),
            source="spec 03 — hash-collision lesson",
        ))

    return out
