"""The validation-rules engine (spec §6): evaluated on every config change,
each rule yielding ok | warning | error with a human-readable explanation
and a source citation. The panel is meant to read like a miniature of
Dell's thermal restriction documentation — that is the pedagogical intent.

Pure module: no FastAPI, no IO — rules are data in, findings out, so the
tests exercise them directly.
"""

from __future__ import annotations

from .constants import value as C
from .engine import _cpu_power, _drive_power, _gpu_power
from .models import Scenario, ServerConfig, Validation


def _max_theoretical_dc(cfg: ServerConfig) -> float:
    """Worst-case DC draw: everything at 100%, boost active, fans at max."""
    fan_pmax = C("fan_pmax_gold_w") if cfg.fan_kit == "gold" else C("fan_pmax_std_w")
    return (
        _cpu_power(cfg, 1.0, True, 1.0)
        + _gpu_power(cfg, 1.0, 1.0)
        + cfg.dimms * C("dimm_active_w")
        + _drive_power(cfg, 1.0)
        + cfg.io_card_w
        + C("platform_base_w")
        + C("fan_count") * fan_pmax
    )


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    env = scenario.environment
    out: list[Validation] = []

    # Rule 1 — heatsink requirement (spec §3.1 / §6.1).
    if cfg.cpu_tdp_w >= 250 and cfg.heatsink != "high-performance":
        out.append(Validation(
            rule_id="heatsink",
            level="error",
            message=(
                f"{cfg.cpu_tdp_w} W CPUs require the high-performance "
                "heatsink; the standard sink cannot hold them at "
                "temperature."
            ),
            source="Dell R760 thermal restrictions (encoded from spec §3.1)",
        ))
    else:
        out.append(Validation(
            rule_id="heatsink", level="ok",
            message="Heatsink selection supports the chosen CPU TDP.",
            source="Dell R760 thermal restrictions (encoded from spec §3.1)",
        ))

    # Rule 2 — Gold fan kit (spec §6.2).
    needs_gold = cfg.cpu_tdp_w >= 300 or cfg.gpus_double_wide > 0
    if needs_gold and cfg.fan_kit != "gold":
        why = (
            "a double-wide GPU" if cfg.gpus_double_wide else
            f"{cfg.cpu_tdp_w} W CPUs"
        )
        out.append(Validation(
            rule_id="fan-kit", level="error",
            message=(
                f"This build carries {why}, which requires the "
                "high-performance (Gold) fan kit."
            ),
            source="Dell R760 thermal restrictions (encoded from spec §3.4)",
        ))
    else:
        out.append(Validation(
            rule_id="fan-kit", level="ok",
            message="Fan kit matches the build's thermal demand.",
            source="Dell R760 thermal restrictions (encoded from spec §3.4)",
        ))

    # Rule 3 — high TDP × high inlet (spec §6.3).
    if cfg.cpu_tdp_w >= 300 and env.inlet_c > C("ashrae_a2_recommended_c"):
        out.append(Validation(
            rule_id="ambient", level="warning",
            message=(
                f"{cfg.cpu_tdp_w} W CPUs above "
                f"{C('ashrae_a2_recommended_c'):g} °C inlet: maximum "
                "supported ambient is reduced for max-TDP configurations. "
                "Expect the fans to work hard and throttle margin to shrink."
            ),
            source="estimate — refine against Dell's thermal restriction matrix",
        ))

    # Rule 4 — PSU capacity vs worst-case draw (spec §3.5 / §6.4).
    max_dc = _max_theoretical_dc(cfg)
    budget = (
        cfg.psu_capacity_w if cfg.redundancy == "1+1"
        else cfg.psu_count * cfg.psu_capacity_w
    )
    if max_dc > budget:
        out.append(Validation(
            rule_id="psu", level="warning",
            message=(
                f"Worst-case draw ≈ {max_dc:.0f} W exceeds the "
                f"{'single-PSU (1+1)' if cfg.redundancy == '1+1' else 'total PSU'} "
                f"budget of {budget} W. The simulator will let you try it — "
                "and will trip the PSU if the overload sustains "
                f"({C('psu_overcurrent_trip_seconds'):g} s at "
                f"{100 * (C('psu_overcurrent_trip_fraction') - 1):.0f}% over)."
            ),
            source="spec §3.5 — warn, don't block; simulate the consequence",
        ))
    else:
        out.append(Validation(
            rule_id="psu", level="ok",
            message=f"Worst-case draw ≈ {max_dc:.0f} W fits the PSU budget of {budget} W.",
            source="spec §3.5",
        ))

    # Rule 5 — altitude derating advisory (spec §6.5).
    if env.altitude_m >= C("derate_start_m"):
        above = env.altitude_m - C("derate_start_m")
        out.append(Validation(
            rule_id="altitude", level="warning",
            message=(
                f"At {env.altitude_m} m, supported ambient decreases about "
                f"{above / 300:.1f} °C (≈1 °C per 300 m above "
                f"{C('derate_start_m'):.0f} m), and thinner air moves less "
                "heat per CFM."
            ),
            source="Dell altitude derating note (spec §5.4)",
        ))

    return out
