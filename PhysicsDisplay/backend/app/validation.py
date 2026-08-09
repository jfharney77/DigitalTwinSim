"""Validation rules — small, like the app, but honest. Pure module."""

from __future__ import annotations

from .constants import value as C
from .models import Scenario, Validation


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    life = scenario.lifecycle
    out: list[Validation] = []

    # Rule 1 — local dimming on a panel that has no zones.
    if cfg.model == "edge-27" and cfg.local_dimming:
        out.append(Validation(
            rule_id="dimming", level="warning",
            message=(
                "The 27-inch class is edge-lit: there are no zones to dim, "
                "so 'local dimming' does nothing here. The simulator runs "
                "the strip at full field regardless — dark content will "
                "not save the watts you might expect."
            ),
            source="Dell U2723QE class — edge-lit backlight (no FALD)",
        ))
    else:
        out.append(Validation(
            rule_id="dimming", level="ok",
            message="Backlight architecture and dimming setting are consistent.",
            source="Dell UltraSharp class spec pages",
        ))

    # Rule 2 — hub delivery within the port's rating.
    if cfg.hub_laptop_w > C("hub_max_w"):
        out.append(Validation(
            rule_id="hub", level="error",
            message=(
                f"USB-C power delivery is capped at {C('hub_max_w'):.0f} W "
                "on this class; the laptop will negotiate down."
            ),
            source="Dell U2723QE — 90 W USB-C PD",
        ))
    else:
        out.append(Validation(
            rule_id="hub", level="ok",
            message="Hub delivery is within the port's 90 W rating.",
            source="Dell U2723QE — 90 W USB-C PD",
        ))

    # Rule 3 — HDR mastering with dimming off is a contradiction worth flagging.
    if cfg.content == "hdr" and cfg.model == "miniled-32" and not cfg.local_dimming:
        out.append(Validation(
            rule_id="hdr", level="warning",
            message=(
                "HDR content with local dimming disabled drives the whole "
                "2,000-zone array at highlight level — the worst-case power "
                "state, and worse contrast too. Real firmware would refuse."
            ),
            source="estimate — HDR requires local dimming for its contrast claim",
        ))

    # Rule 4 — implausible duty cycle advisory.
    if life.hours_per_day >= 20:
        out.append(Validation(
            rule_id="duty", level="warning",
            message=(
                f"{life.hours_per_day:.0f} h/day is signage duty, not desk "
                "duty. The carbon split will tilt hard toward use-phase — "
                "which is the point of trying it."
            ),
            source="estimate — desk monitors average far less",
        ))

    return out
