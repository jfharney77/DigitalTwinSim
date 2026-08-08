"""Every model constant in one place, each with units and a source — the
suite's honesty rule (physics_specs/BUILD_PLAN.md): values from published
documentation cite it; everything else says ``estimate`` and the UI badges
readouts that derive from estimates. Changing a value here changes
behavior without touching engine code.
"""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- CPU power limits (the core laptop lesson, spec 07) ---------------
    "cpu_idle_fraction": Constant(
        value=0.08, unit="fraction of PL1",
        source="estimate — mobile silicon idles lower than server parts",
        estimated=True,
        blurb="CPU package power at 0% utilization, as a fraction of PL1.",
    ),
    "cpu_util_exponent": Constant(
        value=1.4, unit="—",
        source="estimate — same DVFS-shaped curve as the R760 thermal twin",
        estimated=True,
        blurb="Nonlinearity of power vs utilization.",
    ),
    "pl2_multiplier": Constant(
        value=1.6, unit="× PL1",
        source="estimate — mobile PL2 commonly 1.5–2× PL1", estimated=True,
        blurb="Burst power limit as a multiple of the sustained limit.",
    ),
    "pl2_tau_s": Constant(
        value=28, unit="s",
        source="estimate — spec 07 names τ ≈ 28 s (Intel's default tau)",
        estimated=True,
        blurb="How long PL2 boost holds after a load step before PL1 binds.",
    ),
    "cpu_r_th": Constant(
        value=0.35, unit="K/W",
        source="estimate — laptop heat pipe + fin stack", estimated=True,
        blurb="CPU junction-to-air thermal resistance, laptop.",
    ),
    "cpu_r_th_desktop": Constant(
        value=0.22, unit="K/W",
        source="estimate — tower cooler", estimated=True,
        blurb="CPU junction-to-air thermal resistance, desktop tower cooler.",
    ),
    "cpu_tau": Constant(
        value=15, unit="s", source="estimate — thin silicon, small sink",
        estimated=True,
        blurb="First-order thermal time constant, CPU.",
    ),
    "cpu_target_c": Constant(
        value=85, unit="°C", source="estimate", estimated=True,
        blurb="Fan controller's CPU temperature target.",
    ),
    "cpu_throttle_c": Constant(
        value=100, unit="°C", source="estimate — mobile Tjmax proxy",
        estimated=True,
        blurb="CPU throttle threshold.",
    ),
    # --- GPU --------------------------------------------------------------
    "gpu_idle_fraction": Constant(
        value=0.06, unit="fraction of TGP", source="estimate", estimated=True,
        blurb="GPU power at 0% utilization, as a fraction of TGP.",
    ),
    "gpu_r_th": Constant(
        value=0.28, unit="K/W", source="estimate — shared heat-pipe assembly",
        estimated=True,
        blurb="GPU junction-to-air thermal resistance, laptop.",
    ),
    "gpu_r_th_desktop": Constant(
        value=0.13, unit="K/W",
        source="estimate — triple-fan desktop card cooler", estimated=True,
        blurb="GPU junction-to-air thermal resistance, desktop card.",
    ),
    "gpu_boost_multiplier": Constant(
        value=1.15, unit="× TGP",
        source="estimate — Dynamic-Boost-style excursion above TGP", estimated=True,
        blurb="Short GPU power excursion above TGP during the boost window.",
    ),
    "gpu_tau": Constant(
        value=15, unit="s", source="estimate", estimated=True,
        blurb="First-order thermal time constant, GPU.",
    ),
    "gpu_target_c": Constant(
        value=80, unit="°C", source="estimate", estimated=True,
        blurb="Fan controller's GPU temperature target.",
    ),
    "gpu_throttle_c": Constant(
        value=87, unit="°C", source="estimate — mobile GPU throttle point",
        estimated=True,
        blurb="GPU throttle threshold.",
    ),
    # --- Shared thermal budget (the laptop personality, spec 07) ----------
    "budget_laptop_base_w": Constant(
        value=140, unit="W",
        source="estimate — combined heat-pipe dissipation, 16-class chassis",
        estimated=True,
        blurb="Sustained CPU+GPU+NPU heat a laptop chassis can dissipate in balanced mode.",
    ),
    "budget_per_gpu_tier_w": Constant(
        value=0.55, unit="W per TGP watt",
        source="estimate — bigger GPU ships with a bigger fin stack",
        estimated=True,
        blurb="Extra sustained budget per watt of configured GPU TGP.",
    ),
    "budget_quiet_factor": Constant(
        value=0.62, unit="fraction", source="estimate", estimated=True,
        blurb="Quiet mode's share of the balanced thermal budget (fans capped).",
    ),
    "budget_perf_factor": Constant(
        value=1.18, unit="fraction", source="estimate", estimated=True,
        blurb="Performance mode's multiple of the balanced budget (louder, hotter skin allowed).",
    ),
    "on_lap_budget_factor": Constant(
        value=0.70, unit="fraction",
        source="estimate — blocked bottom intake", estimated=True,
        blurb="Thermal-budget derate when the bottom intake is blocked (on-lap).",
    ),
    # --- Skin temperature (absent from servers — spec 07) -----------------
    "skin_cap_c": Constant(
        value=46, unit="°C",
        source="estimate — spec 07 names 45–48 °C as the human-contact cap",
        estimated=True,
        blurb="Skin-temperature hard cap; overrides fan logic and cuts power limits.",
    ),
    "skin_tau": Constant(
        value=120, unit="s", source="estimate — chassis metal is slow",
        estimated=True,
        blurb="First-order time constant of the skin/chassis zone.",
    ),
    "skin_r_th": Constant(
        value=0.10, unit="K/W", source="estimate", estimated=True,
        blurb="Skin rise above ambient per watt of sustained internal heat, laptop.",
    ),
    "skin_r_th_desktop": Constant(
        value=0.02, unit="K/W", source="estimate — big case, side panel",
        estimated=True,
        blurb="Panel rise per watt, desktop — never binding, drawn for contrast.",
    ),
    # --- Battery (spec 07 shared client extension) ------------------------
    "discharge_efficiency": Constant(
        value=0.92, unit="fraction",
        source="estimate — spec 07 names ~0.92", estimated=True,
        blurb="Fraction of stored Wh delivered to the system on discharge.",
    ),
    "charge_heat_fraction": Constant(
        value=0.10, unit="fraction of charge W",
        source="estimate — spec 07 names ~10%", estimated=True,
        blurb="Charging inefficiency that becomes heat inside the chassis.",
    ),
    "charge_rate_max_w": Constant(
        value=90, unit="W", source="estimate — ExpressCharge-class ceiling",
        estimated=True,
        blurb="Maximum power the charger may push into the pack.",
    ),
    "charge_taper_pct": Constant(
        value=80, unit="%", source="estimate — Li-ion CV taper", estimated=True,
        blurb="Charge level above which the charge rate tapers linearly to zero.",
    ),
    "battery_health_r_heat_w": Constant(
        value=2.0, unit="W at full discharge",
        source="estimate — worn pack, higher internal resistance", estimated=True,
        blurb="Extra internal-resistance heat at 80% health under full discharge.",
    ),
    "charger_efficiency": Constant(
        value=0.90, unit="fraction",
        source="estimate — GaN/brick adapter class", estimated=True,
        blurb="Wall-to-DC conversion efficiency of the laptop power adapter.",
    ),
    # --- Fans & acoustics -------------------------------------------------
    "fan_count_laptop": Constant(
        value=2, unit="fans", source="dual-fan layout, m16/18-class chassis",
        estimated=False,
        blurb="Blower pair in the laptop chassis.",
    ),
    "fan_count_desktop": Constant(
        value=4, unit="fans", source="estimate — tower intake/exhaust/CPU/GPU",
        estimated=True,
        blurb="Case + cooler fans modeled in the tower.",
    ),
    "fan_pmax_laptop_w": Constant(
        value=5, unit="W", source="estimate — high-static-pressure blower",
        estimated=True,
        blurb="Per-fan power at 100% rpm, laptop blower.",
    ),
    "fan_pmax_desktop_w": Constant(
        value=6, unit="W", source="estimate", estimated=True,
        blurb="Per-fan power at 100% rpm, tower fan.",
    ),
    "fan_floor_pct": Constant(
        value=20, unit="% rpm", source="estimate", estimated=True,
        blurb="Idle fan floor while powered on.",
    ),
    "fan_kp": Constant(
        value=1.2, unit="%rpm per K per tick", source="estimate", estimated=True,
        blurb="Proportional gain of the fan controller.",
    ),
    "noise_floor_dba": Constant(
        value=24, unit="dB(A)", source="estimate — idle blower at 1 m",
        estimated=True,
        blurb="Noise at the fan floor.",
    ),
    "noise_span_dba": Constant(
        value=28, unit="dB(A)", source="estimate — ~52 dB(A) at full blower",
        estimated=True,
        blurb="Noise added between fan floor and 100% rpm (quadratic in rpm).",
    ),
    "quiet_fan_cap_pct": Constant(
        value=55, unit="% rpm", source="estimate", estimated=True,
        blurb="Fan ceiling in quiet mode — the cap that costs FPS.",
    ),
    # --- Base platform ----------------------------------------------------
    "base_laptop_w": Constant(
        value=12, unit="W",
        source="estimate — display, board, VRs, wireless", estimated=True,
        blurb="Fixed platform power, laptop (display dominates).",
    ),
    "base_desktop_w": Constant(
        value=25, unit="W", source="estimate — board, pumps, RGB, VRs",
        estimated=True,
        blurb="Fixed platform power, tower (no display).",
    ),
    "ram_w_per_16gb": Constant(
        value=1.5, unit="W", source="estimate", estimated=True,
        blurb="Memory power per 16 GB populated.",
    ),
    "nvme_w_each": Constant(
        value=3.0, unit="W", source="estimate — mixed idle/active", estimated=True,
        blurb="Per-NVMe average power.",
    ),
    # --- NPU (Pro Max Plus personality, spec 07) --------------------------
    "npu_max_w": Constant(
        value=40, unit="W",
        source="estimate — spec 07 says 'tens of watts', verify against Dell Pro Max Plus specs",
        estimated=True,
        blurb="Discrete NPU card (Qualcomm AI-100-based) power at full inference load.",
    ),
    "npu_idle_w": Constant(
        value=3, unit="W", source="estimate", estimated=True,
        blurb="NPU card idle power.",
    ),
    # --- Inference engines: tokens/s at full engine power (spec 07) -------
    "tokps_cpu": Constant(
        value=6, unit="tokens/s",
        source="estimate — ~13B-class local LLM on mobile CPU", estimated=True,
        blurb="Token rate with the LLM preset running on the CPU.",
    ),
    "tokps_gpu": Constant(
        value=45, unit="tokens/s", source="estimate", estimated=True,
        blurb="Token rate on the discrete GPU.",
    ),
    "tokps_npu": Constant(
        value=30, unit="tokens/s", source="estimate", estimated=True,
        blurb="Token rate on the discrete NPU — slower than the GPU, far better per joule.",
    ),
    # --- FPS proxy --------------------------------------------------------
    "fps_ref": Constant(
        value=120, unit="FPS", source="estimate — proxy scale, not a benchmark",
        estimated=True,
        blurb="FPS at 100% of configured TGP delivered; scales with delivered power^0.8.",
    ),
    "fps_exponent": Constant(
        value=0.8, unit="—", source="estimate — diminishing returns of GPU watts",
        estimated=True,
        blurb="FPS vs delivered-power nonlinearity.",
    ),
    # --- Protection -------------------------------------------------------
    "battery_shutdown_pct": Constant(
        value=2, unit="%", source="estimate — OS emergency hibernate point",
        estimated=True,
        blurb="Charge level at which the device powers off on battery.",
    ),
    "psu_trip_fraction": Constant(
        value=1.1, unit="× capacity", source="estimate", estimated=True,
        blurb="Sustained desktop-PSU load fraction that trips protection.",
    ),
    "psu_trip_seconds": Constant(
        value=20, unit="s", source="estimate", estimated=True,
        blurb="How long overcurrent must persist before the desktop PSU trips.",
    ),
}

# Desktop PSU efficiency curve (load fraction → efficiency), 80 Plus
# Gold-class approximation; linear interpolation, flat beyond the ends.
PSU_EFFICIENCY_CURVE: list[tuple[float, float]] = [
    (0.0, 0.80),
    (0.10, 0.87),
    (0.20, 0.90),
    (0.50, 0.92),
    (1.00, 0.89),
]

PSU_CURVE_SOURCE = "estimate — 80 Plus Gold-class approximation"


def value(name: str) -> float:
    """Shorthand the engine uses; keeps call sites terse."""
    return CONSTANTS[name].value
