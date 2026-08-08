"""Validation rules for the client-device simulator — evaluated on every
config change, each yielding ok | warning | error with a source. House
rule from the R760 thermal twin: warn about consequences the simulator
can demonstrate rather than blocking them (the undersized charger is a
scenario, not an error). Pure module: no FastAPI, no IO.
"""

from __future__ import annotations

from .constants import value as C
from .engine import thermal_budget_w
from .models import Environment, Scenario, Validation


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    env = scenario.environment
    laptop = cfg.form_factor == "laptop"
    out: list[Validation] = []

    # Rule 1 — the Pro Max Plus is a mobile workstation; there is no tower.
    if cfg.product == "promax" and cfg.form_factor != "laptop":
        out.append(Validation(
            rule_id="form-factor", level="error",
            message="The Pro Max Plus is a mobile workstation — laptop only.",
            source="Dell Pro Max Plus product line (physics_specs/07)",
        ))
    else:
        out.append(Validation(
            rule_id="form-factor", level="ok",
            message="Form factor is valid for the selected product.",
            source="physics_specs/07",
        ))

    # Rule 2 — the discrete NPU is a Pro Max Plus option.
    if cfg.npu and cfg.product != "promax":
        out.append(Validation(
            rule_id="npu", level="error",
            message=(
                "The discrete NPU card is a Pro Max Plus option — the "
                "Alienware machines do not offer it."
            ),
            source="Dell Pro Max Plus product brief (physics_specs/07)",
        ))
    else:
        out.append(Validation(
            rule_id="npu", level="ok",
            message="Accelerator options match the selected product.",
            source="physics_specs/07",
        ))

    # Rule 3 — undersized charger: warn, then let the sim demonstrate it.
    if laptop:
        full_draw = (
            cfg.cpu_pl1_w
            + cfg.gpu_tgp_w
            + (C("npu_max_w") if cfg.npu else 0)
            + C("base_laptop_w")
            + C("ram_w_per_16gb") * cfg.ram_gb / 16
            + C("nvme_w_each") * cfg.nvme_count
            + C("fan_count_laptop") * C("fan_pmax_laptop_w")
        )
        if full_draw > cfg.charger_w:
            out.append(Validation(
                rule_id="charger", level="warning",
                message=(
                    f"Sustained full load ≈ {full_draw:.0f} W exceeds the "
                    f"{cfg.charger_w} W charger. The machine will run — "
                    "and the battery will drain while plugged in. Try it."
                ),
                source="estimate — spec 07's undersized-charger scenario",
            ))
        else:
            out.append(Validation(
                rule_id="charger", level="ok",
                message=(
                    f"The {cfg.charger_w} W charger covers sustained full "
                    f"load (≈ {full_draw:.0f} W)."
                ),
                source="estimate — spec 07",
            ))

    # Rule 4 — demand vs the shared thermal budget (laptop only).
    if laptop:
        budget = thermal_budget_w(cfg, Environment(perf_mode="balanced"))
        demand = cfg.cpu_pl1_w + cfg.gpu_tgp_w + (C("npu_max_w") if cfg.npu else 0)
        if demand > budget:
            out.append(Validation(
                rule_id="budget", level="warning",
                message=(
                    f"Combined sustained demand ≈ {demand:.0f} W exceeds "
                    f"the chassis' ≈ {budget:.0f} W dissipation budget: "
                    "max CPU and max GPU at once is not a thing this "
                    "chassis can do. The allocator will favor the GPU "
                    "and clip the CPU — watch the two bars fight."
                ),
                source="estimate — shared heat-pipe budget, spec 07",
            ))
        else:
            out.append(Validation(
                rule_id="budget", level="ok",
                message="Sustained component demand fits the thermal budget.",
                source="estimate — spec 07",
            ))

    # Rule 5 — desktop PSU capacity (warn, then simulate the trip).
    if not laptop:
        full_draw = (
            cfg.cpu_pl1_w * C("pl2_multiplier")
            + cfg.gpu_tgp_w * C("gpu_boost_multiplier")
            + C("base_desktop_w")
            + C("ram_w_per_16gb") * cfg.ram_gb / 16
            + C("nvme_w_each") * cfg.nvme_count
            + C("fan_count_desktop") * C("fan_pmax_desktop_w")
        )
        if full_draw > cfg.psu_capacity_w:
            out.append(Validation(
                rule_id="psu", level="warning",
                message=(
                    f"Worst-case draw ≈ {full_draw:.0f} W exceeds the "
                    f"{cfg.psu_capacity_w} W PSU. The simulator will let "
                    "you try it — and trip the supply if the overload "
                    f"sustains ({C('psu_trip_seconds'):g} s)."
                ),
                source="estimate — warn, don't block; simulate the consequence",
            ))
        else:
            out.append(Validation(
                rule_id="psu", level="ok",
                message=(
                    f"Worst-case draw ≈ {full_draw:.0f} W fits the "
                    f"{cfg.psu_capacity_w} W PSU."
                ),
                source="estimate",
            ))

    # Rule 6 — worn battery advisory.
    if laptop and cfg.battery_health_pct < 90:
        out.append(Validation(
            rule_id="battery-health", level="warning",
            message=(
                f"Battery at {cfg.battery_health_pct}% health: capacity "
                "is reduced and internal resistance adds heat under "
                "discharge — runtime and thermals both suffer."
            ),
            source="estimate — Li-ion wear model, spec 07",
        ))

    # Rule 7 — on-lap + performance mode is a fight with physics.
    if laptop and env.on_lap and env.perf_mode == "performance":
        out.append(Validation(
            rule_id="on-lap", level="warning",
            message=(
                "Performance mode with the bottom intake blocked: the "
                "raised budget cannot be dissipated and the skin cap "
                "will claw it back. Expect skin-limited within minutes."
            ),
            source="estimate — spec 07's on-lap scenario",
        ))

    return out
