"""Every model constant with units and a source — the suite's honesty
rule. Values from published documentation cite it; everything else says
``estimate`` and the UI badges derived readouts.
"""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- Silicon power ----------------------------------------------------
    "cpu_idle_fraction": Constant(
        value=0.15, unit="fraction of TDP", source="estimate", estimated=True,
        blurb="CPU package power at 0% utilization.",
    ),
    "gpu_idle_fraction": Constant(
        value=0.10, unit="fraction of TDP", source="estimate", estimated=True,
        blurb="GPU power at 0% utilization — why an idle AI server still draws ~1 kW.",
    ),
    "util_exponent": Constant(
        value=1.3, unit="—", source="estimate — DVFS-shaped curve", estimated=True,
        blurb="Nonlinearity of power vs utilization.",
    ),
    "nic_w": Constant(
        value=30, unit="W", source="estimate — spec 01 names 25–35 W for 400G-class NICs",
        estimated=True,
        blurb="Per-NIC power, 400 Gb/s class. Eight of them matter.",
    ),
    "dimm_bank_w": Constant(
        value=100, unit="W", source="estimate — 32 DIMMs at moderate activity",
        estimated=True,
        blurb="Whole memory complex, modeled flat.",
    ),
    "base_w": Constant(
        value=150, unit="W", source="estimate — board, BMC, VRs, NVMe",
        estimated=True,
        blurb="Fixed platform power per chassis.",
    ),
    # --- XE9712 tray & rack -----------------------------------------------
    "tray_gpu_w": Constant(
        value=1400, unit="W",
        source="estimate — Blackwell-class superchip GPU share incl. HBM; verify against NVIDIA GB200 documentation",
        estimated=True,
        blurb="Per-GPU power in a compute tray (4 per tray).",
    ),
    "tray_cpu_w": Constant(
        value=300, unit="W", source="estimate — Grace-class CPU (2 per tray)",
        estimated=True,
        blurb="Per-CPU power in a compute tray.",
    ),
    "tray_base_w": Constant(
        value=200, unit="W", source="estimate", estimated=True,
        blurb="Per-tray board, DPU, and NVMe power.",
    ),
    "nvswitch_tray_w": Constant(
        value=500, unit="W", source="estimate — 9 NVLink switch trays per rack",
        estimated=True,
        blurb="Per-NVLink-switch-tray power.",
    ),
    "nvswitch_trays": Constant(
        value=9, unit="trays",
        source="NVIDIA GB200 NVL72 — 9 switch trays", estimated=False,
        blurb="NVLink switch trays in the rack.",
    ),
    "pump_w_max": Constant(
        value=1500, unit="W", source="estimate — in-rack CDU pump pair",
        estimated=True,
        blurb="Rack CDU pump power at full flow.",
    ),
    "residual_air_fraction": Constant(
        value=0.12, unit="fraction",
        source="estimate — spec 01 names 10–15%", estimated=True,
        blurb="Share of rack heat the cold plates miss; it still hits the room.",
    ),
    "water_cp": Constant(
        value=4186, unit="J/(kg·K)",
        source="specific heat of water — physical constant", estimated=False,
        blurb="Specific heat capacity of the coolant (treated as water).",
    ),
    "coolant_throttle_c": Constant(
        value=65, unit="°C", source="estimate — cold-plate return limit",
        estimated=True,
        blurb="Coolant return temperature above which trays throttle.",
    ),
    "coolant_trip_c": Constant(
        value=75, unit="°C", source="estimate", estimated=True,
        blurb="Coolant return temperature that trips the rack off.",
    ),
    "tray_weight_kg": Constant(
        value=40, unit="kg", source="estimate", estimated=True,
        blurb="Per-tray weight, for the IR7000 floor-loading advisory.",
    ),
    "rack_weight_limit_kg": Constant(
        value=1000, unit="kg",
        source="estimate — raised-floor point-load class", estimated=True,
        blurb="Advisory rack weight before floor loading needs review.",
    ),
    "tray_coolant_lpm": Constant(
        value=8, unit="L/min", source="estimate — per-tray coolant demand at full load",
        estimated=True,
        blurb="Coolant flow one tray wants at full power.",
    ),
    "coolant_tau": Constant(
        value=60, unit="s", source="estimate — loop water volume / flow",
        estimated=True,
        blurb="First-order lag of the coolant return temperature.",
    ),
    # --- Air cooling (XE7745 / XE9680) -------------------------------------
    "fan_count_7745": Constant(
        value=16, unit="fans", source="estimate — scaled-up 4U fan wall",
        estimated=True,
        blurb="Fan-wall population, XE7745.",
    ),
    "fan_count_9680": Constant(
        value=16, unit="fans", source="estimate — 6U high-static wall",
        estimated=True,
        blurb="Fan-wall population, XE9680.",
    ),
    "fan_pmax_w": Constant(
        value=30, unit="W", source="estimate — spec 01: fan overhead at full bore is hundreds of watts",
        estimated=True,
        blurb="Per-fan power at 100% rpm.",
    ),
    "fan_floor_pct": Constant(
        value=30, unit="% rpm", source="estimate — GPU boxes idle loud",
        estimated=True,
        blurb="Fan floor while powered on.",
    ),
    "fan_kp": Constant(
        value=1.0, unit="%rpm per K per tick", source="estimate", estimated=True,
        blurb="Proportional gain of the fan controller.",
    ),
    "gpu_r_th_pcie": Constant(
        value=0.09, unit="K/W", source="estimate — passive PCIe card sink in a duct",
        estimated=True,
        blurb="GPU junction-to-air thermal resistance, PCIe card (XE7745).",
    ),
    "gpu_r_th_sxm": Constant(
        value=0.05, unit="K/W", source="estimate — massive SXM heatsink, 6U duct",
        estimated=True,
        blurb="GPU junction-to-air thermal resistance, SXM module (XE9680).",
    ),
    "hgx_board_per_gpu_w": Constant(
        value=100, unit="W", source="estimate — NVSwitches + VRs on the HGX baseboard, per GPU",
        estimated=True,
        blurb="Baseboard overhead attributed to each SXM GPU.",
    ),
    "stall_power_fraction": Constant(
        value=0.65, unit="fraction",
        source="estimate — a data-starved GPU busy-waits at most of its fed power",
        estimated=True,
        blurb="Share of the demanded-minus-delivered utilization gap that still burns power.",
    ),
    "gpu_r_th_liquid": Constant(
        value=0.018, unit="K/W", source="estimate — cold plate", estimated=True,
        blurb="GPU junction-to-coolant thermal resistance.",
    ),
    "cpu_r_th": Constant(
        value=0.10, unit="K/W", source="estimate", estimated=True,
        blurb="CPU junction-to-air thermal resistance.",
    ),
    "gpu_tau": Constant(
        value=20, unit="s", source="estimate", estimated=True,
        blurb="First-order thermal time constant, GPU.",
    ),
    "cpu_tau": Constant(
        value=20, unit="s", source="estimate", estimated=True,
        blurb="First-order thermal time constant, CPU.",
    ),
    "positional_preheat_c": Constant(
        value=1.1, unit="°C per slot", source="estimate — spec 01 GPU inlet preheat",
        estimated=True,
        blurb="Extra inlet preheat per riser position, front slot to worst slot (XE7745).",
    ),
    "gpu_target_c": Constant(
        value=78, unit="°C", source="estimate", estimated=True,
        blurb="Fan controller's GPU target.",
    ),
    "gpu_throttle_c": Constant(
        value=90, unit="°C", source="estimate", estimated=True,
        blurb="GPU throttle threshold.",
    ),
    "cpu_target_c": Constant(
        value=85, unit="°C", source="estimate", estimated=True,
        blurb="Fan controller's CPU target.",
    ),
    "air_cp": Constant(
        value=1005, unit="J/(kg·K)", source="specific heat of air — physical constant",
        estimated=False,
        blurb="Specific heat capacity of air.",
    ),
    # --- Performance proxy --------------------------------------------------
    "tokens_per_gpu": Constant(
        value=120, unit="tokens/s",
        source="estimate — proxy scale, not a benchmark", estimated=True,
        blurb="Training-throughput proxy per fully-fed GPU at 100% effective utilization.",
    ),
    # --- Protection ---------------------------------------------------------
    "psu_trip_fraction": Constant(
        value=1.05, unit="× capacity", source="estimate", estimated=True,
        blurb="Sustained load fraction that trips the PSU group.",
    ),
    "psu_trip_seconds": Constant(
        value=30, unit="s", source="estimate", estimated=True,
        blurb="Overcurrent persistence before the trip.",
    ),
}

# PSU efficiency (load fraction → efficiency), Titanium-class.
PSU_EFFICIENCY_CURVE: list[tuple[float, float]] = [
    (0.0, 0.85),
    (0.10, 0.90),
    (0.20, 0.94),
    (0.50, 0.96),
    (1.00, 0.94),
]

PSU_CURVE_SOURCE = "estimate — Titanium-class approximation"


def value(name: str) -> float:
    return CONSTANTS[name].value
