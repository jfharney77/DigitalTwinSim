"""Every model constant in one place, each with units and a source — the
spec's editable data file (§2), moved to backend data so the tests can
validate the table itself and the frontend receives it over the wire.

``source`` is honest per the repo's no-invented-specs rule: values taken
from Dell's published documentation cite it; everything else says
``estimate`` and the UI badges readouts that derive from estimates. Refine
against the Dell R760 Technical Guide over time — changing a value here
changes behavior without touching engine code (spec §9.5).
"""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- CPU -------------------------------------------------------------
    "cpu_idle_fraction": Constant(
        value=0.15, unit="fraction of TDP",
        source="estimate — spec §3.1 gives 12–18%", estimated=True,
        blurb="CPU package power at 0% utilization, as a fraction of TDP.",
    ),
    "cpu_util_exponent": Constant(
        value=1.4, unit="—",
        source="estimate — spec §4 realistic power curve", estimated=True,
        blurb="Nonlinearity of power vs utilization: P = idle + (TDP−idle)·util^k.",
    ),
    "cpu_boost_multiplier": Constant(
        value=1.15, unit="× TDP",
        source="estimate — spec §3.1 turbo excursion", estimated=True,
        blurb="Short-excursion boost above TDP at 100% utilization.",
    ),
    "cpu_boost_seconds": Constant(
        value=60, unit="s",
        source="estimate — spec §3.1", estimated=True,
        blurb="How long boost holds before settling to TDP.",
    ),
    "cpu_r_th_hp": Constant(
        value=0.145, unit="K/W",
        source="estimate — high-performance heatsink", estimated=True,
        blurb="CPU junction-to-air thermal resistance, HP heatsink.",
    ),
    "cpu_r_th_std": Constant(
        value=0.22, unit="K/W",
        source="estimate — standard heatsink", estimated=True,
        blurb="CPU junction-to-air thermal resistance, standard heatsink.",
    ),
    "cpu_tau": Constant(
        value=20, unit="s",
        source="estimate — spec §5.2", estimated=True,
        blurb="First-order thermal time constant, CPU silicon + heatsink.",
    ),
    "cpu_target_c": Constant(
        value=85, unit="°C",
        source="estimate — spec §5.3 controller target", estimated=True,
        blurb="Fan controller's CPU temperature target.",
    ),
    "cpu_throttle_c": Constant(
        value=98, unit="°C",
        source="estimate — spec §5.5 Tjmax proxy", estimated=True,
        blurb="CPU throttle threshold (proxy for Tjmax minus margin).",
    ),
    "cpu_shutdown_c": Constant(
        value=105, unit="°C",
        source="estimate — spec §5.5", estimated=True,
        blurb="Sustained CPU temperature that forces emergency power-off.",
    ),
    # --- Memory ----------------------------------------------------------
    "dimm_idle_w": Constant(
        value=1.5, unit="W", source="estimate — spec §3.2", estimated=True,
        blurb="Per-DIMM power at idle.",
    ),
    "dimm_active_w": Constant(
        value=4.0, unit="W", source="estimate — spec §3.2", estimated=True,
        blurb="Per-DIMM power at full memory-bandwidth utilization.",
    ),
    "dimm_airflow_penalty": Constant(
        value=0.05, unit="fraction", source="estimate — spec §3.2", estimated=True,
        blurb="Airflow penalty when all 32 DIMM slots are populated.",
    ),
    # --- Storage ---------------------------------------------------------
    "hdd_active_w": Constant(value=8.0, unit="W", source="estimate — spec §3.3", estimated=True, blurb="3.5-inch HDD active power."),
    "hdd_idle_w": Constant(value=5.0, unit="W", source="estimate — spec §3.3", estimated=True, blurb="3.5-inch HDD idle power."),
    "ssd_active_w": Constant(value=4.0, unit="W", source="estimate — spec §3.3", estimated=True, blurb="2.5-inch SATA/SAS SSD active power."),
    "ssd_idle_w": Constant(value=2.0, unit="W", source="estimate — spec §3.3", estimated=True, blurb="2.5-inch SSD idle power."),
    "nvme_active_w": Constant(value=12.0, unit="W", source="estimate — spec §3.3", estimated=True, blurb="NVMe drive active power."),
    "nvme_idle_w": Constant(value=5.0, unit="W", source="estimate — spec §3.3", estimated=True, blurb="NVMe drive idle power."),
    "drive_airflow_penalty": Constant(
        value=0.005, unit="fraction/drive", source="estimate — spec §3.3", estimated=True,
        blurb="Airflow penalty per populated front-bay drive (capped at 15%).",
    ),
    "drive_tau": Constant(
        value=300, unit="s", source="estimate — spec §5.2", estimated=True,
        blurb="First-order thermal time constant, drive group.",
    ),
    # --- GPU -------------------------------------------------------------
    "gpu_dw_tdp": Constant(
        value=300, unit="W",
        source="Dell R760 supports 300 W-class double-wide GPUs (Technical Guide)",
        estimated=False,
        blurb="Double-wide GPU TDP class modeled.",
    ),
    "gpu_sw_tdp": Constant(
        value=75, unit="W",
        source="75 W single-wide accelerator class (no aux power)", estimated=False,
        blurb="Single-wide accelerator TDP class modeled.",
    ),
    "gpu_idle_fraction": Constant(
        value=0.10, unit="fraction of TDP", source="estimate", estimated=True,
        blurb="GPU power at 0% utilization, as a fraction of TDP.",
    ),
    "gpu_r_th": Constant(
        value=0.12, unit="K/W", source="estimate", estimated=True,
        blurb="GPU junction-to-air thermal resistance.",
    ),
    "gpu_tau": Constant(
        value=20, unit="s", source="estimate — spec §5.2", estimated=True,
        blurb="First-order thermal time constant, GPU silicon + heatsink.",
    ),
    "gpu_target_c": Constant(
        value=80, unit="°C", source="estimate", estimated=True,
        blurb="Fan controller's GPU temperature target.",
    ),
    "gpu_throttle_c": Constant(
        value=92, unit="°C", source="estimate", estimated=True,
        blurb="GPU throttle threshold.",
    ),
    # --- Platform --------------------------------------------------------
    "platform_base_w": Constant(
        value=60, unit="W", source="estimate — board, iDRAC, VRs, misc", estimated=True,
        blurb="Fixed platform power: motherboard, BMC, voltage regulation.",
    ),
    # --- Fans ------------------------------------------------------------
    "fan_count": Constant(
        value=6, unit="fans",
        source="Dell R760 Technical Guide — 6 hot-swap fan modules", estimated=False,
        blurb="Fan-wall population in the standard chassis.",
    ),
    "fan_pmax_gold_w": Constant(
        value=25, unit="W", source="estimate — spec §5.3", estimated=True,
        blurb="Per-fan power at 100% rpm, high-performance (Gold) kit.",
    ),
    "fan_pmax_std_w": Constant(
        value=15, unit="W", source="estimate — spec §5.3", estimated=True,
        blurb="Per-fan power at 100% rpm, standard kit.",
    ),
    "fan_cfm_gold": Constant(
        value=30, unit="CFM/fan", source="estimate", estimated=True,
        blurb="Per-fan airflow at 100% rpm, Gold kit.",
    ),
    "fan_cfm_std": Constant(
        value=22, unit="CFM/fan", source="estimate", estimated=True,
        blurb="Per-fan airflow at 100% rpm, standard kit.",
    ),
    "fan_floor_pct": Constant(
        value=15, unit="% rpm", source="estimate — spec §5.3", estimated=True,
        blurb="Idle fan floor.",
    ),
    "fan_floor_gpu_pct": Constant(
        value=30, unit="% rpm", source="estimate — spec §5.3", estimated=True,
        blurb="Fan floor when any double-wide GPU is present.",
    ),
    "fan_kp": Constant(
        value=0.8, unit="%rpm per K per tick", source="estimate", estimated=True,
        blurb="Proportional gain of the fan controller.",
    ),
    "lane_a_share": Constant(
        value=0.6, unit="fraction", source="estimate — spec §5.1 lane split", estimated=True,
        blurb="Share of total airflow through the CPU/DIMM lane (rest is PCIe/GPU lane).",
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
    "inlet_shutdown_c": Constant(
        value=55, unit="°C", source="estimate — spec §5.5", estimated=True,
        blurb="Effective inlet temperature that forces emergency power-off.",
    ),
    "ashrae_a2_recommended_c": Constant(
        value=27, unit="°C",
        source="ASHRAE A2 recommended envelope upper bound", estimated=False,
        blurb="Upper bound of the ASHRAE-recommended inlet band (annotated on the slider).",
    ),
    "ashrae_a2_allowable_c": Constant(
        value=35, unit="°C",
        source="ASHRAE A2 allowable envelope upper bound", estimated=False,
        blurb="Upper bound of the ASHRAE A2 allowable inlet band.",
    ),
    "derate_start_m": Constant(
        value=950, unit="m",
        source="Dell derating note — supported ambient decreases ~1 °C per 300 m above 950 m",
        estimated=False,
        blurb="Altitude above which supported ambient derates.",
    ),
    # --- PSU -------------------------------------------------------------
    "psu_overcurrent_trip_fraction": Constant(
        value=1.05, unit="× capacity", source="estimate — spec §3.5", estimated=True,
        blurb="Sustained load fraction that trips a PSU.",
    ),
    "psu_overcurrent_trip_seconds": Constant(
        value=30, unit="s", source="estimate — spec §3.5", estimated=True,
        blurb="How long overcurrent must persist before the trip.",
    ),
    "shutdown_sustain_seconds": Constant(
        value=5, unit="s", source="estimate", estimated=True,
        blurb="How long critical CPU overtemp must persist before power-off.",
    ),
}

# PSU efficiency curve: (load fraction of active capacity, efficiency).
# Titanium-class approximation per spec §3.5; linear interpolation between
# points, flat beyond the ends.
PSU_EFFICIENCY_CURVE: list[tuple[float, float]] = [
    (0.0, 0.85),
    (0.10, 0.90),
    (0.20, 0.94),
    (0.50, 0.96),
    (1.00, 0.94),
]

PSU_CURVE_SOURCE = "estimate — Titanium-class approximation, spec §3.5"


def value(name: str) -> float:
    """Shorthand the engine uses; keeps call sites terse."""
    return CONSTANTS[name].value
