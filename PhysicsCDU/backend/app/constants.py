"""Every model constant in one place, each with units and a source.

``source`` is honest per the repo's no-invented-specs rule. The PowerCool
CDU C7000, PowerRack, and Integrated Rack Controller were announced at
Dell Technologies World in May 2026 and ship from Q3 2026 — public detail
is press-release depth, so most physics constants here are estimates and
say so. The handful of reported figures (rated capacity class, form
factor) cite the announcement coverage. Changing a value here changes
behavior without touching engine code.
"""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- Heat exchanger ----------------------------------------------------
    "hx_rated_kw": Constant(
        value=220, unit="kW",
        source="Dell DTW 2026 announcement (via DCD / TechTarget): the "
               "C7000 supports Vera Rubin NVL72-class racks at 220+ kW",
        estimated=False,
        blurb="Nameplate heat-moving capacity class of the CDU.",
    ),
    "hx_ua_kw_per_k": Constant(
        value=7.0, unit="kW/K",
        source="estimate — chosen so the rated 220 kW class binds "
               "plausibly against chilled facility water", estimated=True,
        blurb="Overall heat-exchanger conductance (UA) at nominal flow. "
              "Approach temperature = Q ÷ (UA × flow factor).",
    ),
    "flow_ff_exponent": Constant(
        value=0.6, unit="—",
        source="estimate — heat-transfer coefficient rises sublinearly "
               "with flow (Dittus–Boelter-flavored)", estimated=True,
        blurb="Exponent of the flow factor applied to UA: "
              "ff = (flow/nominal)^0.6.",
    ),
    # --- Secondary (rack) loop ----------------------------------------------
    "flow_nominal_lpm": Constant(
        value=340, unit="L/min", source="estimate — sized for ~220 kW at "
        "a ~10 K loop rise in PG25", estimated=True,
        blurb="Nominal secondary flow the UA figure is quoted at.",
    ),
    "pump_single_flow_lpm": Constant(
        value=210, unit="L/min", source="estimate", estimated=True,
        blurb="Flow one pump alone can push through this loop at 100% "
              "speed (pump curve ∩ system curve).",
    ),
    "pump_parallel_exponent": Constant(
        value=0.65, unit="—",
        source="estimate — parallel pumps on a shared system curve add "
               "flow sublinearly", estimated=True,
        blurb="Q_max(k pumps) = Q_single × k^0.65. Two pumps give ~1.6×, "
              "not 2× — the system curve steals the difference.",
    ),
    "pump_max_kw": Constant(
        value=3.0, unit="kW", source="estimate", estimated=True,
        blurb="Electrical power of one pump at 100% speed.",
    ),
    "cp_pg25": Constant(
        value=3.8, unit="kJ/(kg·K)",
        source="typical PG25 (25% propylene glycol) property — estimate",
        estimated=True,
        blurb="Specific heat of the treated rack coolant.",
    ),
    "rho_pg25": Constant(
        value=1.04, unit="kg/L",
        source="typical PG25 property — estimate", estimated=True,
        blurb="Density of the treated rack coolant.",
    ),
    "tau_loop_s": Constant(
        value=60, unit="s", source="estimate — loop volume + HX metal "
        "thermal inertia", estimated=True,
        blurb="First-order time constant of the secondary supply "
              "temperature.",
    ),
    # --- Primary (facility) loop ---------------------------------------------
    "cp_water": Constant(
        value=4.186, unit="kJ/(kg·K)",
        source="specific heat of water — physical constant", estimated=False,
        blurb="Specific heat of the facility water.",
    ),
    "rho_water": Constant(
        value=0.998, unit="kg/L",
        source="density of water — physical constant", estimated=False,
        blurb="Density of the facility water.",
    ),
    "fac_design_dt_c": Constant(
        value=6.0, unit="K", source="estimate — common TCS design point",
        estimated=True,
        blurb="Facility-side design temperature rise; the CDU's valve "
              "modulates primary flow to hold it.",
    ),
    # --- Rack payload --------------------------------------------------------
    "group_kw": Constant(
        value=40, unit="kW", source="estimate — one bank ≈ six GB200-class "
        "compute trays at ~6.7 kW each", estimated=True,
        blurb="Liquid-cooled heat of one tray bank at 100% utilization "
              "and no cap.",
    ),
    "group_idle_fraction": Constant(
        value=0.08, unit="fraction", source="estimate", estimated=True,
        blurb="A tray bank's heat at 0% utilization, as a fraction of "
              "its full load.",
    ),
    "r_chip_k_per_kw": Constant(
        value=0.18, unit="K/kW",
        source="estimate — cold-plate + TIM thermal resistance, lumped "
               "per 40 kW bank", estimated=True,
        blurb="Hottest-silicon rise above local coolant per kW of bank "
              "heat.",
    ),
    "tau_chip_s": Constant(
        value=15, unit="s", source="estimate — silicon + cold plate mass",
        estimated=True,
        blurb="First-order time constant of the hottest-chip temperature.",
    ),
    # --- IRC policy ------------------------------------------------------------
    "chip_target_c": Constant(
        value=63, unit="°C", source="estimate — IRC holds silicon a "
        "couple of kelvin under the tray firmware's own trip",
        estimated=True,
        blurb="The coordinated policy's silicon temperature target.",
    ),
    "chip_trip_c": Constant(
        value=65, unit="°C", source="estimate — tray-level protective "
        "trip the uncoordinated mode runs into", estimated=True,
        blurb="Tray firmware's self-protection trip temperature.",
    ),
    "trip_sustain_base_s": Constant(
        value=10, unit="s", source="estimate", estimated=True,
        blurb="Seconds over the trip line before the first bank powers "
              "itself off.",
    ),
    "trip_sustain_step_s": Constant(
        value=5, unit="s", source="estimate — trays reach their limits "
        "at slightly different moments; modeled as a deterministic "
        "stagger", estimated=True,
        blurb="Additional sustain seconds per successive bank.",
    ),
    "cap_kp": Constant(
        value=0.004, unit="cap fraction per K per s", source="estimate",
        estimated=True,
        blurb="Gain of the IRC's coordinated shedding controller.",
    ),
    "cap_recover_per_s": Constant(
        value=0.004, unit="cap fraction per s", source="estimate",
        estimated=True,
        blurb="How fast caps float back up once margin returns.",
    ),
    "cap_floor": Constant(
        value=0.15, unit="fraction", source="estimate", estimated=True,
        blurb="The deepest the IRC will cap a bank before conceding "
              "the rack must idle.",
    ),
    # --- Condensation guard ------------------------------------------------------
    "dew_margin_c": Constant(
        value=2.0, unit="K",
        source="industry practice — CDUs hold supply above dew point "
               "plus margin (ASHRAE liquid-cooling guidance)",
        estimated=False,
        blurb="Minimum margin the CDU keeps between secondary supply "
              "and room dew point, via its mixing valve.",
    ),
    # --- ASHRAE water classes (annotation) -----------------------------------------
    "ashrae_w32_c": Constant(
        value=32, unit="°C",
        source="ASHRAE W32 facility-water class upper bound",
        estimated=False,
        blurb="Upper bound of the W32 facility supply envelope "
              "(annotated on the slider).",
    ),
    "ashrae_w45_c": Constant(
        value=45, unit="°C",
        source="ASHRAE W45 facility-water class upper bound",
        estimated=False,
        blurb="Upper bound of the W45 facility supply envelope.",
    ),
}


def value(name: str) -> float:
    """Shorthand the engine uses; keeps call sites terse."""
    return CONSTANTS[name].value
