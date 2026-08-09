"""The validation-rules engine: evaluated on every config change, each
rule yielding ok | warning | error with a human-readable explanation and a
source citation. The panel reads like a miniature of Dell's thermal
restriction matrix — plus the rugged-site rules a data-hall server never
needs: the rated envelope, the extended-config restrictions, and the
HDD-under-vibration warning.

Pure module: no FastAPI, no IO — rules are data in, findings out, so the
tests exercise them directly.
"""

from __future__ import annotations

from .constants import value as C
from .engine import _accel_power, _cpu_power, _drive_power
from .models import PLATFORM_TDP_TIERS, Scenario, ServerConfig, Validation


def _max_theoretical_dc(cfg: ServerConfig) -> float:
    """Worst-case DC draw: everything at 100%, boost active, fans at max."""
    return (
        _cpu_power(cfg, 1.0, True, 1.0)
        + _accel_power(cfg, 1.0, 1.0)
        + cfg.dimms * C("dimm_active_w")
        + _drive_power(cfg, 1.0)
        + cfg.io_card_w
        + C("platform_base_w")
        + C("fan_count") * C("fan_pmax_w")
    )


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    env = scenario.environment
    out: list[Validation] = []

    # Rule 1 — the CPU tier must exist on the platform.
    tiers = PLATFORM_TDP_TIERS[cfg.platform]
    if cfg.cpu_tdp_w not in tiers:
        out.append(Validation(
            rule_id="cpu-tier",
            level="error",
            message=(
                f"{cfg.cpu_tdp_w} W is not a CPU tier the "
                f"{cfg.platform.upper()} takes — this platform's tiers are "
                f"{', '.join(str(t) for t in tiers)} W. The XR8000's sleds "
                "carry single-socket Xeon Scalable; the XR4000's nodes "
                "carry Xeon D."
            ),
            source="Dell XR8000/XR4000 technical guides (modeled tiers)",
        ))
    else:
        out.append(Validation(
            rule_id="cpu-tier", level="ok",
            message="CPU tier is available on this platform.",
            source="Dell XR8000/XR4000 technical guides (modeled tiers)",
        ))

    # Rule 2 — the extended envelope is select configs only.
    if cfg.thermal_config == "extended":
        problems = []
        if cfg.platform != "xr8000":
            problems.append("only the XR8000 offers it")
        if cfg.cpu_tdp_w > C("extended_max_tdp_w"):
            problems.append(
                f"CPU tiers above {C('extended_max_tdp_w'):.0f} W are excluded"
            )
        if cfg.drive_type == "hdd":
            problems.append("spinning drives are not rated for it")
        if problems:
            out.append(Validation(
                rule_id="extended-envelope", level="error",
                message=(
                    "The −20…65 °C extended envelope is a select-config "
                    "rating, and this build breaks it: "
                    + "; ".join(problems) + "."
                ),
                source="Dell XR8000 Technical Guide — extended range on "
                       "select configurations (exclusions modeled, estimate)",
            ))
        else:
            out.append(Validation(
                rule_id="extended-envelope", level="ok",
                message="This build qualifies for the −20…65 °C extended envelope.",
                source="Dell XR8000 Technical Guide",
            ))

    # Rule 3 — ambient vs the rated envelope (warn; the sim shows why).
    if cfg.thermal_config == "extended":
        lo, hi = C("xr_extended_min_c"), C("xr_extended_max_c")
        envelope = "extended (−20…65 °C)"
    else:
        lo, hi = C("xr_standard_min_c"), C("xr_standard_max_c")
        envelope = "standard (−5…55 °C)"
    if env.inlet_c < lo or env.inlet_c > hi:
        out.append(Validation(
            rule_id="envelope", level="warning",
            message=(
                f"{env.inlet_c:g} °C ambient is outside the {envelope} "
                "rating. The simulator will run it — that is what it is "
                "for — but this is exactly the territory the rating exists "
                "to fence off."
            ),
            source="Dell PowerEdge XR spec sheet — rated envelopes",
        ))
    else:
        out.append(Validation(
            rule_id="envelope", level="ok",
            message=f"Ambient sits inside the {envelope} rating.",
            source="Dell PowerEdge XR spec sheet — rated envelopes",
        ))

    # Rule 4 — spinning drives at a vibrating site.
    if cfg.drive_type == "hdd" and cfg.drives > 0 and env.vibration != "none":
        lost = (
            C("vib_hdd_vehicle_pct") if env.vibration == "vehicle"
            else C("vib_hdd_roadside_pct")
        )
        out.append(Validation(
            rule_id="vibration", level="warning",
            message=(
                f"Spinning drives under {env.vibration} vibration: expect "
                f"~{lost:.0f}% of their throughput lost to head "
                "repositioning, and shortened life. Rugged sites spec SSDs "
                "for exactly this reason."
            ),
            source="estimate — vibration derate class; the steer to SSDs "
                   "is standard rugged-deployment guidance",
        ))

    # Rule 5 — a filter overdue for service.
    if env.dust == "heavy" and env.filter_months >= 6:
        out.append(Validation(
            rule_id="filter", level="warning",
            message=(
                f"{env.filter_months:g} months of heavy dust: the filter "
                "is carrying a real airflow penalty. The next hot day, the "
                "fans will pay for it — or fail to."
            ),
            source="estimate — fouling model; service intervals are the fix",
        ))

    # Rule 6 — PSU capacity vs worst-case draw (warn, don't block).
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
                "and will trip the PSU if the overload sustains."
            ),
            source="warn, don't block; simulate the consequence",
        ))
    else:
        out.append(Validation(
            rule_id="psu", level="ok",
            message=f"Worst-case draw ≈ {max_dc:.0f} W fits the PSU budget of {budget} W.",
            source="modeled worst-case draw",
        ))

    # Rule 7 — altitude derating advisory.
    if env.altitude_m >= C("derate_start_m"):
        above = env.altitude_m - C("derate_start_m")
        out.append(Validation(
            rule_id="altitude", level="warning",
            message=(
                f"At {env.altitude_m} m, supported ambient decreases about "
                f"{above / 300:.1f} °C (≈1 °C per 300 m above "
                f"{C('derate_start_m'):.0f} m), and thinner air moves less "
                "heat per CFM. Mountain cell sites stack this on top of "
                "everything else."
            ),
            source="Dell altitude derating note",
        ))

    return out
