"""The validation-rules engine: evaluated on every config change, each
rule yielding ok | warning | error with a human-readable explanation and
a source citation — the miniature of a liquid-cooling site-readiness
checklist.

Pure module: no FastAPI, no IO — rules are data in, findings out, so the
tests exercise them directly.
"""

from __future__ import annotations

from .constants import value as C
from .engine import bank_heat_kw, pump_flow_lpm
from .leveling import L
from .models import Scenario, Validation


def worst_case_it_kw(tray_groups: int) -> float:
    """Everything at 100% utilization with no caps."""
    return tray_groups * bank_heat_kw(1.0, 1.0)


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    env = scenario.environment
    out: list[Validation] = []

    # Rule 1 — condensation: the minimum-supply setpoint vs dew point.
    floor = env.dew_point_c + C("dew_margin_c")
    if cfg.min_supply_c < floor:
        out.append(Validation(
            rule_id="dew-point", level="error",
            message=(
                f"Minimum-supply setpoint {cfg.min_supply_c:g} °C is below "
                f"the room dew point ({env.dew_point_c:g} °C) plus the "
                f"{C('dew_margin_c'):g} K margin. Coolant that cold "
                "condenses room moisture onto cold plates and manifolds — "
                "water, dripping inside a live rack. The CDU's mixing "
                "valve will refuse the setpoint and hold "
                f"{floor:g} °C."
            ),
            source="ASHRAE liquid-cooling guidance — supply above dew "
                   "point plus margin",
        ))
    elif cfg.min_supply_c < env.dew_point_c + 5:
        out.append(Validation(
            rule_id="dew-point", level="warning",
            message=(
                f"Minimum-supply setpoint {cfg.min_supply_c:g} °C sits "
                f"within 5 K of the dew point ({env.dew_point_c:g} °C). "
                "Legal, but a humid afternoon erases the margin — the "
                "floor will chase the dew point up and your supply "
                "temperature is no longer yours to choose."
            ),
            source="ASHRAE liquid-cooling guidance",
        ))
    else:
        out.append(Validation(
            rule_id="dew-point", level="ok",
            message="Supply setpoint clears the dew point with margin.",
            source="ASHRAE liquid-cooling guidance",
        ))

    # Rule 2 — pump redundancy.
    if cfg.pumps < 3:
        out.append(Validation(
            rule_id="pump-redundancy", level="warning",
            message=(
                "Two pumps is N, not N+1: both are needed to hold the "
                "flow setpoint, so the first failure derates the loop. "
                "The simulator will let you try it — fail a pump and "
                "watch capacity bind."
            ),
            source="estimate — CDU redundancy practice; warn, don't block",
        ))
    else:
        out.append(Validation(
            rule_id="pump-redundancy", level="ok",
            message="N+1 pumps: one failure leaves the flow setpoint "
                    "reachable.",
            source="estimate — CDU redundancy practice",
        ))

    # Rule 3 — heat vs the CDU's rated class.
    worst = worst_case_it_kw(cfg.tray_groups)
    rated = C("hx_rated_kw")
    if worst > rated:
        out.append(Validation(
            rule_id="hx-sizing", level="warning",
            message=L(
                standard=(
                    f"Worst-case rack heat ≈ {worst:.0f} kW exceeds the "
                    f"CDU's {rated:.0f} kW class. Nothing explodes — the "
                    "coolant supply temperature floats up until the IRC "
                    "(Integrated Rack Controller) sheds load, or, "
                    "uncoordinated, until tray banks trip. Watch the "
                    "IRC cap readout."
                ),
                novice=(
                    f"At full speed this rack makes about {worst:.0f} kW "
                    f"of heat, more than the {rated:.0f} kW the cooling "
                    "box is built to move. Nothing breaks. The coolant "
                    "runs warmer until the rack controller (the "
                    "Integrated Rack Controller, IRC) slows the "
                    "computers a little. With the controller off, banks "
                    "of computers shut themselves down instead. Watch "
                    "the 'speed limit' readout: 100% means no slowdown."
                ),
                expert=(
                    f"Worst case ≈ {worst:.0f} kW > {rated:.0f} kW class: "
                    "supply floats until the IRC caps (or banks trip, "
                    "uncoordinated)."
                ),
            ),
            source="Dell DTW 2026 announcement — C7000 220 kW class; "
                   "warn, don't block",
        ))
    else:
        out.append(Validation(
            rule_id="hx-sizing", level="ok",
            message=f"Worst-case rack heat ≈ {worst:.0f} kW fits the "
                    f"CDU's {rated:.0f} kW class.",
            source="Dell DTW 2026 announcement — C7000 220 kW class",
        ))

    # Rule 4 — facility water class.
    if env.facility_supply_c > C("ashrae_w45_c"):
        out.append(Validation(
            rule_id="facility-class", level="warning",
            message=(
                f"Facility supply {env.facility_supply_c:g} °C is beyond "
                "even the W45 envelope — every kelvin lands directly on "
                "the silicon."
            ),
            source="ASHRAE W-class envelopes",
        ))
    elif env.facility_supply_c > C("c7000_max_facility_c"):
        out.append(Validation(
            rule_id="facility-class", level="warning",
            message=(
                f"Facility supply {env.facility_supply_c:g} °C is above "
                f"the {C('c7000_max_facility_c'):g} °C facility-water "
                "inlet Dell states the C7000 supports. The simulator "
                "will run it; the product is not rated for it."
            ),
            source="Dell PowerRack blog, May 2026 — C7000 facility water "
                   "up to 40 °C (vendor claim); warn, don't block",
        ))
    elif env.facility_supply_c > C("ashrae_w32_c"):
        out.append(Validation(
            rule_id="facility-class", level="warning",
            message=(
                f"Facility supply {env.facility_supply_c:g} °C is a "
                "W40-class warm-water design: efficient (no chillers), "
                "but the approach temperature comes straight off your "
                "silicon margin. This model's approach is about 30 K at "
                "rated load where a real plate exchanger runs 2–5 K, so "
                "a full rack will not ride water this warm here; a real "
                "C7000's tighter exchanger is what Dell's 40 °C figure "
                "rests on."
            ),
            source="ASHRAE W-class envelopes",
        ))

    # Rule 5 — flow setpoint reachable with the installed pumps.
    reachable, _ = pump_flow_lpm(cfg.pumps, cfg.flow_setpoint_lpm)
    if reachable < cfg.flow_setpoint_lpm - 0.5:
        out.append(Validation(
            rule_id="flow-setpoint", level="warning",
            message=(
                f"The {cfg.flow_setpoint_lpm} L/min setpoint is beyond "
                f"what {cfg.pumps} pumps can push through this loop "
                f"(≈{reachable:.0f} L/min at 100%). The pumps will pin "
                "and the loop runs flow-short."
            ),
            source="estimate — pump curve ∩ system curve",
        ))

    # Rule 6 — the policy itself.
    if cfg.policy == "uncoordinated":
        out.append(Validation(
            rule_id="policy", level="warning",
            message=L(
                standard=(
                    "Uncoordinated mode: no rack-level policy, so the "
                    "IRC cap reads 'off' and each tray bank self-protects "
                    "on its own firmware trip. On a warm-water day this "
                    "becomes a staggered cascade of trips instead of a "
                    "graceful shed. The model's trays are trip-only: "
                    "real trays throttle their own clocks before a hard "
                    "trip, so read this mode as the worst case. Run both."
                ),
                novice=(
                    "The rack controller is switched off, so nothing "
                    "slows the computers down together and the speed "
                    "limit reads 'off'. Each bank of computers looks "
                    "after only itself: when its chips get too hot it "
                    "shuts off completely. On a warm-water day the banks "
                    "shut off one after another instead of all slowing a "
                    "little. In this model a bank is either at full "
                    "speed or off. Real computers also slow themselves "
                    "first, so this is the worst case. Run both modes "
                    "and compare."
                ),
                expert=(
                    "Uncoordinated: cap off, per-bank firmware trip only "
                    "(no local throttling modeled — worst case). Warm "
                    "water → staggered trip cascade, not a shed."
                ),
            ),
            source="estimate — the IRC's coordinated-response claim, "
                   "inverted",
        ))

    return out
