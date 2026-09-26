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


_FAN_RULE_SOURCE = (
    "Dell R760 thermal restriction matrix — GPU configurations support only "
    "HPR Gold fans. The 300 W CPU line is this model's simplification: Dell "
    "also offers an HPR Silver tier and sets the fan by drive configuration"
)


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

    # Rule 1 — heatsink requirement (spec §3.1 / §6.1). Dell's thermal
    # restriction matrix rates the standard heatsink to 165 W; the spec's
    # original 250 W line was corrected against it.
    if cfg.cpu_tdp_w > 165 and cfg.heatsink != "high-performance":
        out.append(Validation(
            rule_id="heatsink",
            level="error",
            message=(
                f"{cfg.cpu_tdp_w} W CPUs require the high-performance "
                "heatsink; Dell rates the standard heatsink for "
                "processors up to 165 W."
            ),
            source="Dell R760 thermal restriction matrix — standard heatsink up to 165 W, HPR heatsink above",
        ))
    else:
        out.append(Validation(
            rule_id="heatsink", level="ok",
            message="Heatsink selection supports the chosen CPU TDP.",
            source="Dell R760 thermal restriction matrix — standard heatsink up to 165 W, HPR heatsink above",
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
            source=_FAN_RULE_SOURCE,
        ))
    else:
        out.append(Validation(
            rule_id="fan-kit", level="ok",
            message="Fan kit matches the build's thermal demand.",
            source=_FAN_RULE_SOURCE,
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
            source=(
                "estimate — Dell's thermal restriction matrix limits some "
                "350 W builds to 30 °C ambient; the 300 W / 27 °C trigger "
                "here is this model's simplification"
            ),
        ))

    # Rule 3b — inlet above the ASHRAE A2 allowable limit, whether set on
    # the slider or reached by a timed event. Warn, don't block: running
    # past the limit is exactly what some scenarios exist to demonstrate.
    peak_inlet = max(
        [float(env.inlet_c)]
        + [float(e.value) for e in scenario.events
           if e.action == "set-inlet" and e.value is not None]
    )
    if peak_inlet > C("ashrae_a2_allowable_c"):
        via = "" if peak_inlet == env.inlet_c else " (reached by a timed event)"
        out.append(Validation(
            rule_id="inlet-allowable", level="warning",
            message=(
                f"Inlet reaches {peak_inlet:g} °C{via}, above the ASHRAE A2 "
                f"allowable limit of {C('ashrae_a2_allowable_c'):g} °C. A "
                "real hall only sees this during a cooling failure; the run "
                "shows what the server does about it."
            ),
            source="Dell R760 environmental specifications — ASHRAE A2 allowable range",
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
            source="Dell R760 environmental specifications — ASHRAE A2: 1 °C per 300 m above 900 m",
        ))

    return out
