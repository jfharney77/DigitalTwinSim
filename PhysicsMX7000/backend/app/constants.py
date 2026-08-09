"""Every model constant in one place, each with units and a source.

``source`` is honest per the repo's no-invented-specs rule: chassis facts
confirmed against Dell's MX7000 documentation cite it; everything else
says ``estimate`` and the UI badges readouts that derive from estimates.
Changing a value here changes behavior without touching engine code.
"""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- Chassis facts (verified against Dell documentation) --------------
    "sled_bays": Constant(
        value=8, unit="bays",
        source="Dell MX7000 spec sheet — eight single-width sled bays",
        estimated=False,
        blurb="Front bays for single-width compute or storage sleds.",
    ),
    "fan_count": Constant(
        value=9, unit="fans",
        source="Dell MX7000 spec sheet — 4 front + 5 rear hot-swap fans",
        estimated=False,
        blurb="Chassis-level fan population. There are no per-sled fans — sharing is the architecture.",
    ),
    "psu_capacity_w": Constant(
        value=3000, unit="W",
        source="Dell MX7000 spec sheet — up to six 3000 W PSUs",
        estimated=False,
        blurb="Per-PSU capacity; up to six share one pooled budget.",
    ),
    # --- Compute sled ------------------------------------------------------
    "sled_sockets": Constant(
        value=2, unit="sockets",
        source="Dell MX750c compute sled — dual-socket", estimated=False,
        blurb="CPU sockets per single-width compute sled.",
    ),
    "cpu_idle_fraction": Constant(
        value=0.15, unit="fraction of TDP",
        source="estimate — same idle floor the R760Thermal engine uses",
        estimated=True,
        blurb="CPU package power at 0% utilization, as a fraction of TDP.",
    ),
    "cpu_util_exponent": Constant(
        value=1.4, unit="—",
        source="estimate — realistic superlinear power curve", estimated=True,
        blurb="Nonlinearity of power vs utilization: P = idle + (TDP−idle)·util^k.",
    ),
    "sled_base_w": Constant(
        value=45, unit="W",
        source="estimate — sled board, NICs, mezzanines, VRs", estimated=True,
        blurb="Fixed per-sled platform power for an occupied compute bay.",
    ),
    "dimm_idle_w": Constant(
        value=1.5, unit="W", source="estimate", estimated=True,
        blurb="Per-DIMM power at idle.",
    ),
    "dimm_active_w": Constant(
        value=4.0, unit="W", source="estimate", estimated=True,
        blurb="Per-DIMM power at full memory bandwidth.",
    ),
    "local_drive_idle_w": Constant(
        value=2.0, unit="W", source="estimate — 2.5-inch SSD", estimated=True,
        blurb="Per-drive idle power, compute sled local bay.",
    ),
    "local_drive_active_w": Constant(
        value=4.0, unit="W", source="estimate — 2.5-inch SSD", estimated=True,
        blurb="Per-drive active power, compute sled local bay.",
    ),
    # --- Storage sled --------------------------------------------------------
    "storage_sled_drives": Constant(
        value=16, unit="drives",
        source="Dell MX5016s storage sled — 16 hot-pluggable SAS drives",
        estimated=False,
        blurb="Drive count in one MX5016s-class storage sled.",
    ),
    "storage_sled_base_w": Constant(
        value=30, unit="W", source="estimate — expanders, board", estimated=True,
        blurb="Fixed power of an occupied storage sled before drive activity.",
    ),
    "sas_drive_idle_w": Constant(
        value=6.0, unit="W", source="estimate — 2.5-inch SAS", estimated=True,
        blurb="Per-drive idle power in the storage sled.",
    ),
    "sas_drive_active_w": Constant(
        value=10.0, unit="W", source="estimate — 2.5-inch SAS", estimated=True,
        blurb="Per-drive active power in the storage sled.",
    ),
    # --- Shared infrastructure ---------------------------------------------
    "fabric_iom_w": Constant(
        value=110, unit="W",
        source="estimate — MX9116n-class fabric I/O module", estimated=True,
        blurb="Per-module power of the redundant fabric switch pair.",
    ),
    "mgmt_module_w": Constant(
        value=25, unit="W",
        source="estimate — MX9002m management module", estimated=True,
        blurb="Per-module power of the redundant management pair.",
    ),
    "fan_pmax_w": Constant(
        value=45, unit="W", source="estimate — 80 mm chassis fan class",
        estimated=True,
        blurb="Per-fan power at 100% rpm. Cubic in speed below that.",
    ),
    "fan_cfm": Constant(
        value=65, unit="CFM/fan", source="estimate", estimated=True,
        blurb="Per-fan airflow at 100% rpm.",
    ),
    "fan_floor_pct": Constant(
        value=20, unit="% rpm", source="estimate", estimated=True,
        blurb="Idle fan floor — a 7U chassis never runs silent.",
    ),
    "fan_kp": Constant(
        value=0.8, unit="%rpm per K per tick", source="estimate", estimated=True,
        blurb="Proportional gain of the shared fan controller.",
    ),
    "sled_target_c": Constant(
        value=78, unit="°C", source="estimate — controller target", estimated=True,
        blurb="The fan controller holds the HOTTEST sled to this — which is the shared-fan tax in one number.",
    ),
    "sled_throttle_c": Constant(
        value=95, unit="°C", source="estimate — Tjmax proxy", estimated=True,
        blurb="Per-sled CPU throttle threshold.",
    ),
    "sled_shutdown_c": Constant(
        value=102, unit="°C", source="estimate", estimated=True,
        blurb="Sustained sled temperature that forces chassis power-off.",
    ),
    "sled_r_th": Constant(
        value=0.15, unit="K/W", source="estimate — sled heatsink class",
        estimated=True,
        blurb="CPU junction-to-air thermal resistance inside a sled.",
    ),
    "sled_tau": Constant(
        value=25, unit="s", source="estimate", estimated=True,
        blurb="First-order thermal time constant, compute sled.",
    ),
    "storage_tau": Constant(
        value=180, unit="s", source="estimate", estimated=True,
        blurb="First-order thermal time constant, storage sled (drive mass).",
    ),
    "storage_rise_c": Constant(
        value=8, unit="°C", source="estimate", estimated=True,
        blurb="Drive-body rise above the storage sled's local air.",
    ),
    # --- Air ------------------------------------------------------------------
    "air_cp": Constant(
        value=1005, unit="J/(kg·K)",
        source="specific heat of air — physical constant", estimated=False,
        blurb="Specific heat capacity of air at constant pressure.",
    ),
    "air_density": Constant(
        value=1.2, unit="kg/m³",
        source="air density at sea level, ~20 °C — physical constant",
        estimated=False,
        blurb="Air density used for mass-flow conversion.",
    ),
    "cfm_to_m3s": Constant(
        value=0.000472, unit="(m³/s)/CFM",
        source="unit conversion — exact", estimated=False,
        blurb="Cubic feet per minute to cubic metres per second.",
    ),
    "inlet_shutdown_c": Constant(
        value=50, unit="°C", source="estimate", estimated=True,
        blurb="Inlet temperature that forces emergency power-off.",
    ),
    "ashrae_a2_recommended_c": Constant(
        value=27, unit="°C",
        source="ASHRAE A2 recommended envelope upper bound", estimated=False,
        blurb="Upper bound of the ASHRAE-recommended inlet band.",
    ),
    # --- PSU pool ---------------------------------------------------------------
    "psu_overcurrent_trip_fraction": Constant(
        value=1.05, unit="× capacity", source="estimate", estimated=True,
        blurb="Sustained load fraction of the surviving pool that trips the chassis.",
    ),
    "psu_overcurrent_trip_seconds": Constant(
        value=30, unit="s", source="estimate", estimated=True,
        blurb="How long overcurrent must persist before the trip.",
    ),
    "shutdown_sustain_seconds": Constant(
        value=5, unit="s", source="estimate", estimated=True,
        blurb="How long critical sled overtemp must persist before power-off.",
    ),
}

# PSU efficiency curve: (load fraction of alive capacity, efficiency).
# Titanium-class approximation; linear interpolation, flat beyond the ends.
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
