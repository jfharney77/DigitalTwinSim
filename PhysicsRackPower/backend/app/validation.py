"""The validation-rules engine: evaluated on every config change, each
rule yielding ok | warning | error with a human-readable explanation and
a source citation. The panel is meant to read like the checklist a
facilities engineer runs before energizing a rack.

Pure module: no FastAPI, no IO — rules are data in, findings out, so the
tests exercise them directly.
"""

from __future__ import annotations

from .constants import value as C
from .engine import PHASES, battery_capacity_fraction
from .models import Scenario, Validation


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    env = scenario.environment
    out: list[Validation] = []

    volts = C("phase_voltage_v")
    pf = C("power_factor")
    rating = float(cfg.breaker_amps)
    continuous = C("breaker_continuous_fraction")

    phase_w = {
        p: sum(ld.power_w for ld in cfg.loads if ld.phase == p) for p in PHASES
    }

    # Rule 1 — the 80% continuous-load rule, per phase.
    hot = {
        p: w for p, w in phase_w.items()
        if w / (volts * pf) > continuous * rating
    }
    over = {p: w for p, w in phase_w.items() if w / (volts * pf) > rating}
    if over:
        names = ", ".join(sorted(over))
        out.append(Validation(
            rule_id="breaker", level="warning",
            message=(
                f"Phase {names} exceeds the breaker rating outright "
                f"({rating:g} A). The simulator will let you energize it — "
                "and will trip the breaker once the thermal curve says so, "
                "taking every load on the phase down with it."
            ),
            source="thermal-magnetic trip curve (simplified I²t) — "
                   "warn, don't block; simulate the consequence",
        ))
    elif hot:
        names = ", ".join(sorted(hot))
        out.append(Validation(
            rule_id="breaker", level="warning",
            message=(
                f"Phase {names} is above {100 * continuous:.0f}% of its "
                f"{rating:g} A breaker. Legal for a moment, not for a "
                "shift: continuous loads must leave 20% headroom."
            ),
            source="NEC 80% continuous-load rule (210.19/210.20)",
        ))
    else:
        out.append(Validation(
            rule_id="breaker", level="ok",
            message=(
                f"Every phase sits at or under {100 * continuous:.0f}% of "
                f"its {rating:g} A breaker — the continuous-load rule holds."
            ),
            source="NEC 80% continuous-load rule (210.19/210.20)",
        ))

    # Rule 2 — phase imbalance.
    total = sum(phase_w.values())
    if total > 0:
        avg = total / 3.0
        imbalance = 100.0 * max(abs(w - avg) for w in phase_w.values()) / avg
        if imbalance > 30:
            out.append(Validation(
                rule_id="imbalance", level="warning",
                message=(
                    f"Phase imbalance is {imbalance:.0f}%. The heaviest "
                    "feed hits its breaker limit while the others idle — "
                    "you bought three phases and are using one."
                ),
                source="estimate — utilities and PDU vendors recommend "
                       "keeping imbalance in the low tens of percent",
            ))
        else:
            out.append(Validation(
                rule_id="imbalance", level="ok",
                message=f"Phase imbalance is {imbalance:.0f}% — acceptably even.",
                source="estimate — utilities and PDU vendors recommend "
                       "keeping imbalance in the low tens of percent",
            ))

    # Rule 3 — battery age vs chemistry.
    frac = battery_capacity_fraction(cfg, env.room_temp_c)
    if frac < 0.8:
        out.append(Validation(
            rule_id="battery-age", level="warning",
            message=(
                f"The fade model puts this battery at {100 * frac:.0f}% of "
                f"nameplate ({cfg.ups_chemistry.upper()}, "
                f"{cfg.ups_age_years:g} years, {env.room_temp_c:g} °C room). "
                "80% is the usual end-of-life line. The front panel will "
                "not know until a self-test runs."
            ),
            source="estimate — 80% capacity is the conventional battery "
                   "end-of-life threshold (IEEE 1188 practice)",
        ))
    else:
        out.append(Validation(
            rule_id="battery-age", level="ok",
            message=(
                f"Battery holds {100 * frac:.0f}% of nameplate under the "
                "fade model — above the 80% end-of-life line."
            ),
            source="estimate — 80% capacity is the conventional battery "
                   "end-of-life threshold (IEEE 1188 practice)",
        ))

    # Rule 4 — hot room advisory for VRLA.
    if cfg.ups_chemistry == "vrla" and env.room_temp_c > C("reference_temp_c") + 5:
        out.append(Validation(
            rule_id="room-temp", level="warning",
            message=(
                f"VRLA at {env.room_temp_c:g} °C: aging roughly doubles per "
                f"+{C('vrla_temp_doubling_c'):g} °C above "
                f"{C('reference_temp_c'):g} °C. A five-year battery in this "
                "room is not a five-year battery."
            ),
            source="VRLA temperature-aging rule of thumb (IEEE 535 / "
                   "vendor guidance; applied as an exact doubling — estimate)",
        ))

    return out
