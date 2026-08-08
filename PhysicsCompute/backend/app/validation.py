"""Validation rules — spec 01's per-product restriction matrix, plus the
IR7000 section's headline: at rack scale, the validation rules ARE the
product (power, coolant, and weight budgets bind before space does).
Pure module.
"""

from __future__ import annotations

from .constants import value as C
from .engine import gpu_count, max_dc_w
from .models import Scenario, Validation


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    env = scenario.environment
    out: list[Validation] = []

    if cfg.product == "xe7745":
        # GPU count × TDP vs PSU capacity (warn, then simulate the trip).
        max_dc = max_dc_w(cfg)
        budget = 4 * cfg.psu_capacity_w
        if max_dc > budget:
            out.append(Validation(
                rule_id="psu", level="warning",
                message=(
                    f"Worst-case draw ≈ {max_dc / 1000:.1f} kW exceeds the "
                    f"{budget / 1000:.1f} kW PSU bank. The simulator will "
                    "let you try it — and trip the supplies if the "
                    "overload sustains."
                ),
                source="spec 01 §1 — GPU count × TDP vs PSU capacity, verify against XE7745 spec sheet",
            ))
        else:
            out.append(Validation(
                rule_id="psu", level="ok",
                message=f"Worst-case draw ≈ {max_dc / 1000:.1f} kW fits the PSU bank.",
                source="spec 01 §1",
            ))
        # GPU tier vs supported ambient (restriction-matrix style).
        if cfg.pcie_gpu_tdp_w >= 600 and env.inlet_c > 25:
            out.append(Validation(
                rule_id="ambient", level="warning",
                message=(
                    "600 W-class GPUs above 25 °C inlet: supported ambient "
                    "is reduced for the top GPU tier. Expect the worst "
                    "riser position to throttle first."
                ),
                source="estimate — restriction-matrix style, verify against Dell's XE7745 thermal guide",
            ))
    elif cfg.product == "xe9680":
        max_dc = max_dc_w(cfg)
        budget = 6 * cfg.psu_capacity_w
        level = "warning" if max_dc > budget else "ok"
        out.append(Validation(
            rule_id="psu", level=level,
            message=(
                f"Worst-case draw ≈ {max_dc / 1000:.1f} kW against a "
                f"{budget / 1000:.1f} kW PSU bank."
                + (" Oversubscribed — the trip is simulatable." if level == "warning" else "")
            ),
            source="spec 01 §2",
        ))
        if cfg.sxm_gpu_tdp_w >= 1000 and env.inlet_c > 25:
            out.append(Validation(
                rule_id="ambient", level="warning",
                message=(
                    "B200-class boards above 25 °C inlet: the air-cooled "
                    "ceiling is close. This machine is the argument the "
                    "XE9712 answers with liquid."
                ),
                source="estimate — verify against Dell's XE9680 thermal restrictions",
            ))
    else:
        # IR7000: the budgets are the product.
        tray_kw = (
            4 * C("tray_gpu_w") + 2 * C("tray_cpu_w") + C("tray_base_w")
        ) / 1000.0
        total_kw = cfg.trays * tray_kw + (
            C("nvswitch_trays") * C("nvswitch_tray_w") + C("pump_w_max")
        ) / 1000.0
        if total_kw > cfg.shelf_capacity_kw:
            out.append(Validation(
                rule_id="shelf", level="error",
                message=(
                    f"{cfg.trays} trays need ≈ {total_kw:.0f} kW but the "
                    f"power shelves supply {cfg.shelf_capacity_kw} kW. "
                    "At rack scale the power budget binds before the "
                    "space does — remove trays or add shelf capacity."
                ),
                source="spec 01 §4 — tray power sum vs shelf capacity, verify against IR7000 documentation",
            ))
        else:
            out.append(Validation(
                rule_id="shelf", level="ok",
                message=(
                    f"≈ {total_kw:.0f} kW of tray demand fits the "
                    f"{cfg.shelf_capacity_kw} kW shelves."
                ),
                source="spec 01 §4",
            ))
        demand_lpm = cfg.trays * C("tray_coolant_lpm")
        if demand_lpm > cfg.manifold_capacity_lpm:
            out.append(Validation(
                rule_id="manifold", level="error",
                message=(
                    f"Tray coolant demand ≈ {demand_lpm:.0f} L/min exceeds "
                    f"the manifold's {cfg.manifold_capacity_lpm} L/min."
                ),
                source="spec 01 §4 — coolant demand vs manifold capacity",
            ))
        else:
            out.append(Validation(
                rule_id="manifold", level="ok",
                message=(
                    f"Coolant demand ≈ {demand_lpm:.0f} L/min fits the "
                    "manifolds."
                ),
                source="spec 01 §4",
            ))
        weight = cfg.trays * C("tray_weight_kg") + 400  # rack + shelves + CDU
        if weight > C("rack_weight_limit_kg"):
            out.append(Validation(
                rule_id="weight", level="warning",
                message=(
                    f"≈ {weight:.0f} kg loaded weight — review floor "
                    "loading before this rack rolls in (advisory)."
                ),
                source="estimate — spec 01 §4 floor-loading advisory",
            ))
        if cfg.coolant_supply_c > 40:
            out.append(Validation(
                rule_id="warm-water", level="warning",
                message=(
                    f"{cfg.coolant_supply_c:g} °C supply water: legal for "
                    "warm-water economization, but the margin to the "
                    "65 °C return throttle shrinks with every degree."
                ),
                source="estimate — W32/W40/W45 warm-water classes",
            ))

    if cfg.product != "xe9712" and gpu_count(cfg) == 0:
        out.append(Validation(
            rule_id="no-gpu", level="warning",
            message="No GPUs configured — this simulator is about the GPUs.",
            source="spec 01",
        ))
    return out
