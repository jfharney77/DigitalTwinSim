"""Every model constant in one place, each with units and a source.

``source`` is honest per the repo's no-invented-specs rule: values taken
from Dell's published documentation cite it; everything else says
``estimate`` and the UI badges readouts that derive from estimates. The
XR-specific facts that are *documented* — the −5…55 °C standard envelope,
the −20…65 °C extended envelope on select XR8000 configurations, NEBS
Level 3 — are cited to the Dell XR spec sheet and XR8000 technical guide
verified at build time (2026-08). Fouling rates, vibration derates, and
the brownout electrical limits are estimates and say so.
"""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- CPU -------------------------------------------------------------
    "cpu_idle_fraction": Constant(
        value=0.15, unit="fraction of TDP",
        source="estimate — typical server-CPU idle floor", estimated=True,
        blurb="CPU package power at 0% utilization, as a fraction of TDP.",
    ),
    "cpu_util_exponent": Constant(
        value=1.4, unit="—",
        source="estimate — realistic power-vs-utilization curve", estimated=True,
        blurb="Nonlinearity of power vs utilization: P = idle + (TDP−idle)·util^k.",
    ),
    "cpu_boost_multiplier": Constant(
        value=1.15, unit="× TDP",
        source="estimate — turbo excursion class", estimated=True,
        blurb="Short-excursion boost above TDP at 100% utilization.",
    ),
    "cpu_boost_seconds": Constant(
        value=60, unit="s",
        source="estimate", estimated=True,
        blurb="How long boost holds before settling to TDP.",
    ),
    "cpu_r_th": Constant(
        value=0.16, unit="K/W",
        source="estimate — short-depth rugged heatsink", estimated=True,
        blurb="CPU junction-to-air thermal resistance (single rugged sink; "
              "XR sleds do not offer a heatsink menu).",
    ),
    "cpu_tau": Constant(
        value=20, unit="s",
        source="estimate — silicon + heatsink mass", estimated=True,
        blurb="First-order thermal time constant, CPU silicon + heatsink.",
    ),
    "cpu_target_c": Constant(
        value=85, unit="°C",
        source="estimate — fan controller target", estimated=True,
        blurb="Fan controller's CPU temperature target.",
    ),
    "cpu_throttle_c": Constant(
        value=98, unit="°C",
        source="estimate — Tjmax proxy", estimated=True,
        blurb="CPU throttle threshold (proxy for Tjmax minus margin).",
    ),
    "cpu_shutdown_c": Constant(
        value=105, unit="°C",
        source="estimate", estimated=True,
        blurb="Sustained CPU temperature that forces emergency power-off.",
    ),
    # --- Memory ----------------------------------------------------------
    "dimm_idle_w": Constant(
        value=1.5, unit="W", source="estimate", estimated=True,
        blurb="Per-DIMM power at idle.",
    ),
    "dimm_active_w": Constant(
        value=4.0, unit="W", source="estimate", estimated=True,
        blurb="Per-DIMM power at full memory-bandwidth utilization.",
    ),
    # --- Storage ---------------------------------------------------------
    "hdd_active_w": Constant(value=8.0, unit="W", source="estimate", estimated=True, blurb="2.5-inch HDD active power."),
    "hdd_idle_w": Constant(value=5.0, unit="W", source="estimate", estimated=True, blurb="2.5-inch HDD idle power."),
    "ssd_active_w": Constant(value=4.0, unit="W", source="estimate", estimated=True, blurb="2.5-inch/E3.S SSD active power."),
    "ssd_idle_w": Constant(value=2.0, unit="W", source="estimate", estimated=True, blurb="2.5-inch/E3.S SSD idle power."),
    "drive_airflow_penalty": Constant(
        value=0.005, unit="fraction/drive", source="estimate", estimated=True,
        blurb="Airflow penalty per populated front-bay drive (capped at 5%).",
    ),
    "drive_tau": Constant(
        value=300, unit="s", source="estimate", estimated=True,
        blurb="First-order thermal time constant, drive group.",
    ),
    # --- Vibration (the HDD-vs-SSD lesson) --------------------------------
    "vib_hdd_roadside_pct": Constant(
        value=15, unit="% throughput lost",
        source="estimate — roadside-cabinet vibration class", estimated=True,
        blurb="Spinning-drive throughput lost to head repositioning under "
              "roadside vibration (traffic, wind, HVAC). SSDs lose nothing.",
    ),
    "vib_hdd_vehicle_pct": Constant(
        value=40, unit="% throughput lost",
        source="estimate — in-vehicle vibration class", estimated=True,
        blurb="Spinning-drive throughput lost under vehicle vibration. "
              "The reason rugged sites spec SSDs.",
    ),
    # --- Accelerators ------------------------------------------------------
    "accel_sw_tdp": Constant(
        value=75, unit="W",
        source="75 W single-wide accelerator class (no aux power)", estimated=False,
        blurb="Single-wide edge-inference accelerator TDP class modeled.",
    ),
    "accel_idle_fraction": Constant(
        value=0.10, unit="fraction of TDP", source="estimate", estimated=True,
        blurb="Accelerator power at 0% utilization, as a fraction of TDP.",
    ),
    "accel_r_th": Constant(
        value=0.30, unit="K/W", source="estimate", estimated=True,
        blurb="Accelerator junction-to-air thermal resistance.",
    ),
    "accel_tau": Constant(
        value=20, unit="s", source="estimate", estimated=True,
        blurb="First-order thermal time constant, accelerator.",
    ),
    "accel_target_c": Constant(
        value=80, unit="°C", source="estimate", estimated=True,
        blurb="Fan controller's accelerator temperature target.",
    ),
    "accel_throttle_c": Constant(
        value=92, unit="°C", source="estimate", estimated=True,
        blurb="Accelerator throttle threshold.",
    ),
    # --- Platform --------------------------------------------------------
    "platform_base_w": Constant(
        value=45, unit="W", source="estimate — board, BMC, VRs, misc", estimated=True,
        blurb="Fixed platform power: motherboard, BMC, voltage regulation "
              "(smaller than the R760's — a short-depth sled carries less board).",
    ),
    # --- Fans ------------------------------------------------------------
    "fan_count": Constant(
        value=4, unit="fans",
        source="estimate — short-depth sled fan wall", estimated=True,
        blurb="Fan-wall population modeled for the sled.",
    ),
    "fan_pmax_w": Constant(
        value=18, unit="W", source="estimate", estimated=True,
        blurb="Per-fan power at 100% rpm.",
    ),
    "fan_cfm": Constant(
        value=16, unit="CFM/fan", source="estimate", estimated=True,
        blurb="Per-fan airflow at 100% rpm through a clean filter — a "
              "short-depth sled's fan wall, not the R760's.",
    ),
    "fan_floor_pct": Constant(
        value=15, unit="% rpm", source="estimate", estimated=True,
        blurb="Idle fan floor.",
    ),
    "fan_floor_accel_pct": Constant(
        value=25, unit="% rpm", source="estimate", estimated=True,
        blurb="Fan floor when accelerators are present.",
    ),
    "fan_kp": Constant(
        value=0.8, unit="%rpm per K per tick", source="estimate", estimated=True,
        blurb="Proportional gain of the fan controller.",
    ),
    "lane_a_share": Constant(
        value=0.65, unit="fraction", source="estimate — lane split", estimated=True,
        blurb="Share of total airflow through the CPU/DIMM lane (rest is "
              "the accelerator/I-O lane).",
    ),
    # --- Filter fouling (the personality) ---------------------------------
    "fouling_rate_clean": Constant(
        value=0.01, unit="resistance fraction/month",
        source="estimate — filtered indoor air", estimated=True,
        blurb="Airflow-resistance gain per sim-month in a clean environment.",
    ),
    "fouling_rate_moderate": Constant(
        value=0.025, unit="resistance fraction/month",
        source="estimate — typical roadside cabinet", estimated=True,
        blurb="Airflow-resistance gain per sim-month in moderate dust.",
    ),
    "fouling_rate_heavy": Constant(
        value=0.07, unit="resistance fraction/month",
        source="estimate — desert rooftop / factory floor", estimated=True,
        blurb="Airflow-resistance gain per sim-month in heavy dust.",
    ),
    "fouling_cap": Constant(
        value=0.5, unit="fraction", source="estimate", estimated=True,
        blurb="Worst-case airflow lost to a never-changed filter.",
    ),
    # --- Air & environment ----------------------------------------------
    "air_cp": Constant(
        value=1005, unit="J/(kg·K)",
        source="specific heat of air — physical constant", estimated=False,
        blurb="Specific heat capacity of air at constant pressure.",
    ),
    "air_density_sl": Constant(
        value=1.2, unit="kg/m³",
        source="air density at sea level, ~20 °C — physical constant", estimated=False,
        blurb="Air density at sea level.",
    ),
    "altitude_density_per_km": Constant(
        value=0.09, unit="fraction/1000 m",
        source="≈9% density loss per 1000 m — standard atmosphere approx.",
        estimated=False,
        blurb="Air-density derate per 1000 m of altitude.",
    ),
    "cfm_to_m3s": Constant(
        value=0.000472, unit="(m³/s)/CFM",
        source="unit conversion — exact", estimated=False,
        blurb="Cubic feet per minute to cubic metres per second.",
    ),
    # --- Rated envelopes (the documented facts) ---------------------------
    "xr_standard_min_c": Constant(
        value=-5, unit="°C",
        source="Dell PowerEdge XR spec sheet — XR series rated −5…55 °C",
        estimated=False,
        blurb="Lower bound of the standard rugged operating envelope.",
    ),
    "xr_standard_max_c": Constant(
        value=55, unit="°C",
        source="Dell PowerEdge XR spec sheet — XR series rated −5…55 °C",
        estimated=False,
        blurb="Upper bound of the standard rugged operating envelope "
              "(a data-hall server's A2 envelope tops out at 35 °C).",
    ),
    "xr_extended_min_c": Constant(
        value=-20, unit="°C",
        source="Dell XR8000 Technical Guide — −20…65 °C on select configs",
        estimated=False,
        blurb="Lower bound of the extended envelope, select XR8000 configs.",
    ),
    "xr_extended_max_c": Constant(
        value=65, unit="°C",
        source="Dell XR8000 Technical Guide — −20…65 °C on select configs",
        estimated=False,
        blurb="Upper bound of the extended envelope, select XR8000 configs.",
    ),
    "extended_max_tdp_w": Constant(
        value=225, unit="W",
        source="estimate — extended envelope is select (reduced) configs; "
               "the exact matrix is Dell's thermal restriction table",
        estimated=True,
        blurb="Largest CPU tier this model allows in the extended envelope.",
    ),
    "inlet_shutdown_c": Constant(
        value=70, unit="°C", source="estimate — beyond even the extended class",
        estimated=True,
        blurb="Effective inlet temperature that forces emergency power-off.",
    ),
    "derate_start_m": Constant(
        value=950, unit="m",
        source="Dell derating note — supported ambient decreases ~1 °C per 300 m above 950 m",
        estimated=False,
        blurb="Altitude above which supported ambient derates.",
    ),
    # --- PSU & the feed ----------------------------------------------------
    "psu_input_nominal_v": Constant(
        value=120, unit="V",
        source="estimate — single-phase site feed modeled at 120 V nominal",
        estimated=True,
        blurb="Nominal feed voltage. Cell sites are single-phase (or −48 V DC); "
              "there is no data-hall UPS ahead of this box.",
    ),
    "psu_input_margin": Constant(
        value=1.05, unit="× rated input current",
        source="estimate — input-stage headroom over the nameplate point",
        estimated=True,
        blurb="A PSU's input current limit, as a multiple of its rated "
              "current (capacity ÷ nominal voltage). Sagging voltage at "
              "constant power means rising current — why brownouts bite "
              "at load and pass unnoticed at idle.",
    ),
    "brownout_deep_cutoff_pct": Constant(
        value=60, unit="% of nominal",
        source="estimate — below wide-input ride-through", estimated=True,
        blurb="Feed voltage below which the PSUs drop out immediately.",
    ),
    "brownout_trip_seconds": Constant(
        value=3, unit="s", source="estimate", estimated=True,
        blurb="How long input overcurrent must persist before the trip.",
    ),
    "psu_overcurrent_trip_fraction": Constant(
        value=1.05, unit="× capacity", source="estimate", estimated=True,
        blurb="Sustained DC load fraction that trips a PSU.",
    ),
    "psu_overcurrent_trip_seconds": Constant(
        value=30, unit="s", source="estimate", estimated=True,
        blurb="How long DC overcurrent must persist before the trip.",
    ),
    "shutdown_sustain_seconds": Constant(
        value=5, unit="s", source="estimate", estimated=True,
        blurb="How long critical CPU overtemp must persist before power-off.",
    ),
}

# PSU efficiency curve: (load fraction of active capacity, efficiency).
# Titanium-class approximation; linear interpolation between points, flat
# beyond the ends.
PSU_EFFICIENCY_CURVE: list[tuple[float, float]] = [
    (0.0, 0.85),
    (0.10, 0.90),
    (0.20, 0.94),
    (0.50, 0.96),
    (1.00, 0.94),
]

PSU_CURVE_SOURCE = "estimate — Titanium-class approximation"


def value(name: str) -> float:
    """Shorthand the engine uses; keeps call sites terse."""
    return CONSTANTS[name].value
