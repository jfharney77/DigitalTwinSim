"""Validation rules for the telecom & sustainability simulator. Pure."""

from __future__ import annotations

from .constants import value as C
from .engine import disassembly_minutes, refurb_success
from .models import Scenario, Validation


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    out: list[Validation] = []

    if cfg.product == "telecomblocks":
        # Rule 1 — the integration bill, quoted before the run.
        if cfg.deploy_mode == "diy":
            hours = cfg.sites * C("diy_validate_h_site")
            mismatches = cfg.sites // int(C("diy_mismatch_every_n"))
            out.append(Validation(
                rule_id="integration", level="warning",
                message=(
                    f"DIY across {cfg.sites} sites ≈ {hours:.0f} validation "
                    f"hours and ≈ {mismatches} version-mismatch failures "
                    "(A×B×C combinations always find someone). The Blocks "
                    "rerun is the comparison."
                ),
                source="spec 08 — the integration-effort model",
            ))
        else:
            out.append(Validation(
                rule_id="integration", level="ok",
                message=(
                    f"Blocks across {cfg.sites} sites ≈ "
                    f"{cfg.sites * C('blocks_deploy_h_site'):.0f} hours — "
                    "one validated bundle version per site."
                ),
                source="spec 08",
            ))
        # Rule 2 — standard temp outdoors.
        if not cfg.extended_temp:
            out.append(Validation(
                rule_id="temp", level="warning",
                message=(
                    "Standard-temperature hardware at outdoor sites: the "
                    f"first {C('standard_temp_limit_c'):.0f} °C+ day takes "
                    f"~{100 * C('heatwave_site_fraction'):.0f}% of the "
                    "fleet dark. Extended-temp (XR-class) exists for "
                    "exactly this."
                ),
                source="spec 08 — site environment; XR envelope to verify",
            ))
        # Rule 3 — no spares means updates hurt.
        if not cfg.spare_capacity:
            out.append(Validation(
                rule_id="spares", level="warning",
                message=(
                    "No spare site capacity: every update is a per-site "
                    "outage instead of an N+1 roll. Five nines dies by "
                    "maintenance, not by failure."
                ),
                source="spec 08 — availability regime",
            ))
    else:
        # Circular Design rules.
        sealed = sum([
            not cfg.battery_replaceable, not cfg.ram_socketed,
            not cfg.ports_modular,
        ])
        if sealed >= 2:
            out.append(Validation(
                rule_id="sealed", level="warning",
                message=(
                    f"{sealed} of 3 serviceability choices are sealed: the "
                    "scheduled mid-life events (port, battery, RAM) each "
                    "become a whole-device replacement — the embodied "
                    "carbon, paid again."
                ),
                source="spec 08 — the replacement cascade",
            ))
        else:
            out.append(Validation(
                rule_id="sealed", level="ok",
                message=(
                    f"Disassembly ≈ {disassembly_minutes(cfg):.0f} min; "
                    f"refurb odds ≈ {100 * refurb_success(cfg):.0f}%."
                ),
                source="spec 08 — design-for-disassembly score",
            ))
        if refurb_success(cfg) < 0.5:
            out.append(Validation(
                rule_id="second-life", level="warning",
                message=(
                    f"Refurb odds {100 * refurb_success(cfg):.0f}%: at "
                    "first-owner end this design goes to the shredder, "
                    "not a second user — the carbon amortizes over "
                    "fewer years."
                ),
                source="spec 08 — second-life mechanic",
            ))
        out.append(Validation(
            rule_id="pcf", level="ok",
            message=(
                "All carbon figures are labeled estimates. Dell's "
                "per-product PCF reports are the calibration source — "
                "swapping their numbers in is the intended exercise."
            ),
            source="spec 08 — honest footnote, required",
        ))

    return out
