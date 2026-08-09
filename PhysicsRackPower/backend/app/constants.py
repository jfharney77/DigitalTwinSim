"""Every model constant in one place, each with units and a source — the
suite's editable data file, moved to backend data so the tests can
validate the table itself and the frontend receives it over the wire.

``source`` is honest per the repo's no-invented-specs rule: values with a
public citation carry it; everything else says ``estimate`` and the UI
badges readouts that derive from estimates. Dell's current rack-power
accessories are resold APC NetShelter PDUs (dell.com listings, checked
2026-08: 208 V single-phase and 400/415 V three-phase switched/metered
models), which anchors the phase/voltage classes modeled here; the exact
electrical constants below remain estimates.
"""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- Distribution ------------------------------------------------------
    "phase_voltage_v": Constant(
        value=230, unit="V line-to-neutral",
        source="230 V L-N branch of a 400 V three-phase feed — the class "
               "Dell's resold APC NetShelter 400/415 V PDUs distribute "
               "(dell.com listing); 208 V North American variants exist",
        estimated=False,
        blurb="Voltage each phase feed delivers to its outlets.",
    ),
    "power_factor": Constant(
        value=0.98, unit="—",
        source="estimate — modern server PSUs with active PFC run 0.95–0.99",
        estimated=True,
        blurb="Load power factor: amps = watts ÷ (volts × PF).",
    ),
    "breaker_continuous_fraction": Constant(
        value=0.80, unit="fraction of rating",
        source="NEC 80% continuous-load rule (210.19/210.20) — a breaker "
               "carries at most 80% of its rating for 3+ hours",
        estimated=False,
        blurb="The planning limit: above this the validation panel warns.",
    ),
    "breaker_i2t_threshold": Constant(
        value=60, unit="(overload²−1)·s",
        source="estimate — simplified thermal-magnetic I²t curve; real "
               "curves are published per breaker family", estimated=True,
        blurb="Accumulated thermal overload that trips the breaker: at 110% "
              "load it takes minutes, at 200% seconds.",
    ),
    "breaker_magnetic_multiple": Constant(
        value=5, unit="× rating",
        source="estimate — C-curve breakers trip magnetically at 5–10× "
               "rated current", estimated=True,
        blurb="Instantaneous trip threshold — no thermal delay above this.",
    ),
    # --- UPS conversion -----------------------------------------------------
    "inverter_efficiency": Constant(
        value=0.93, unit="fraction",
        source="estimate — spec file 10 §6 names ~0.93 for the inverter "
               "path", estimated=True,
        blurb="Battery-to-load conversion efficiency while on battery.",
    ),
    "ups_pass_efficiency": Constant(
        value=0.98, unit="fraction",
        source="estimate — line-interactive pass-through loses ~2%",
        estimated=True,
        blurb="Utility-to-load efficiency while mains is present.",
    ),
    "charge_power_w": Constant(
        value=200, unit="W",
        source="estimate — rack UPS chargers recharge in hours, not "
               "minutes", estimated=True,
        blurb="Wall power drawn to recharge the battery after a discharge.",
    ),
    "charge_efficiency": Constant(
        value=0.90, unit="fraction",
        source="estimate — charge conversion plus battery acceptance loss",
        estimated=True,
        blurb="Fraction of charger watts that lands in the battery as Wh.",
    ),
    # --- Battery aging ------------------------------------------------------
    "vrla_fade_per_year": Constant(
        value=0.06, unit="capacity fraction / equivalent year",
        source="estimate — VRLA service life 3–5 years to 80% capacity at "
               "25 °C (industry rule of thumb)", estimated=True,
        blurb="Capacity a VRLA battery loses per year at 25 °C.",
    ),
    "lithium_fade_per_year": Constant(
        value=0.02, unit="capacity fraction / equivalent year",
        source="estimate — Li-ion rack batteries are typically warranted "
               "8–10 years", estimated=True,
        blurb="Capacity a lithium battery loses per year at 25 °C.",
    ),
    "vrla_temp_doubling_c": Constant(
        value=10, unit="°C per doubling of aging rate",
        source="VRLA aging roughly doubles per +10 °C above 25 °C — "
               "IEEE 535 / battery-vendor rule of thumb (labeled estimate: "
               "applied here as an exact doubling)", estimated=True,
        blurb="Every +10 °C of room temperature ages a VRLA battery "
              "twice as fast.",
    ),
    "lithium_temp_doubling_c": Constant(
        value=20, unit="°C per doubling of aging rate",
        source="estimate — lithium chemistries are markedly less "
               "temperature-sensitive than VRLA", estimated=True,
        blurb="Temperature sensitivity of lithium aging (much gentler).",
    ),
    "battery_capacity_floor": Constant(
        value=0.10, unit="fraction of nameplate",
        source="estimate — model floor; a battery this far gone would "
               "fail its self-test outright", estimated=True,
        blurb="The fade model never goes below this fraction.",
    ),
    "reference_temp_c": Constant(
        value=25, unit="°C",
        source="battery ratings are quoted at 25 °C — industry standard",
        estimated=False,
        blurb="Room temperature at which battery aging runs at 1×.",
    ),
    # --- Self-test ----------------------------------------------------------
    "self_test_seconds": Constant(
        value=10, unit="s",
        source="estimate — periodic UPS self-tests briefly transfer to "
               "battery", estimated=True,
        blurb="Length of the brief battery transfer a self-test performs.",
    ),
}


def value(name: str) -> float:
    """Shorthand the engine uses; keeps call sites terse."""
    return CONSTANTS[name].value
