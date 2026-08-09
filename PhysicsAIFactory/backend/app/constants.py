"""Every model constant in one place, each with units and a source.

House honesty rule: values traceable to a published figure cite it;
everything else says ``estimate`` and the UI badges readouts derived from
estimates. Several constants here are *arithmetic on public reporting*
(Colossus install rate, Llama-3 failure cadence) — the source field shows
the sum so a reader can check it. None of this is cycle-accurate; the
point is coupling and orders of magnitude.
"""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- Compute ----------------------------------------------------------
    "gpu_idle_fraction": Constant(
        value=0.12, unit="fraction of peak W",
        source="estimate — accelerator idle draw, consistent with the GPU twin",
        estimated=True,
        blurb="GPU power at zero utilization, as a fraction of peak.",
    ),
    "rack_overhead_kw": Constant(
        value=12.0, unit="kW/rack",
        source="estimate — NVSwitch trays, CPUs, NICs, power shelves of an "
               "NVL72-class rack beyond the GPUs (rack ≈ 120 kW total vs "
               "72 × 1.2 kW GPUs ≈ 86 kW; the gap split with cooling)",
        estimated=True,
        blurb="Per-rack IT power that is not GPU silicon.",
    ),
    # --- Fabric -----------------------------------------------------------
    "fabric_eff_ib": Constant(
        value=0.96, unit="fraction",
        source="estimate — non-blocking InfiniBand with in-network "
               "collectives (SHARP) keeps effective collective bandwidth "
               "in the mid-90s; vendor claims, not our measurement",
        estimated=True,
        blurb="Training-step efficiency multiplier on a 1:1 Quantum fabric.",
    ),
    "fabric_eff_ethernet": Constant(
        value=0.95, unit="fraction",
        source="estimate — NVIDIA's Spectrum-X claim is ~95% effective "
               "bandwidth under load vs ~60% for untuned Ethernet",
        estimated=True,
        blurb="Training-step efficiency multiplier on a 1:1 Spectrum-X fabric.",
    ),
    "oversub_penalty": Constant(
        value=0.10, unit="fraction per 1:1 of oversubscription",
        source="estimate — collectives are gated by the thinnest layer; "
               "2:1 oversubscription costs roughly one step-time tenth",
        estimated=True,
        blurb="Fabric efficiency lost per unit of oversubscription above 1:1.",
    ),
    "fabric_kw_per_gpu": Constant(
        value=0.05, unit="kW/GPU",
        source="estimate — one 800G NIC per GPU plus its share of "
               "leaf/spine switch power",
        estimated=True,
        blurb="Fabric power per GPU: NIC + switch share.",
    ),
    # --- Data platform ------------------------------------------------------
    "storage_w_per_gbps": Constant(
        value=10.0, unit="W per GB/s",
        source="estimate — a ~6 TB/s Exascale-class rack drawing tens of kW "
               "gives order-10 W per GB/s of aggregate throughput",
        estimated=True,
        blurb="Data-platform power per unit of aggregate throughput.",
    ),
    # --- Facility ------------------------------------------------------------
    "pue_liquid": Constant(
        value=1.15, unit="PUE",
        source="estimate — direct-liquid-cooled AI halls report PUE "
               "≈1.1–1.2; the IR7000 twin's territory",
        estimated=True,
        blurb="Power usage effectiveness with direct liquid cooling.",
    ),
    "pue_air": Constant(
        value=1.45, unit="PUE",
        source="estimate — conventional air-cooled data-hall PUE",
        estimated=True,
        blurb="Power usage effectiveness with air cooling.",
    ),
    "other_it_fraction": Constant(
        value=0.05, unit="fraction of IT",
        source="estimate — management, ops infrastructure, everything "
               "not compute/fabric/storage",
        estimated=True,
        blurb="Overhead IT power as a fraction of the accounted subsystems.",
    ),
    # --- Timeline -------------------------------------------------------------
    "procure_h": Constant(
        value=72, unit="h",
        source="estimate — compressed for the sim; real procurement is "
               "months and would flatten every chart",
        estimated=True,
        blurb="Hours from decision to first rack on the dock (compressed).",
    ),
    "install_h_per_rack": Constant(
        value=2.0, unit="h/rack",
        source="arithmetic on public reporting — xAI Colossus stood up "
               "~1,500 racks in 122 days: 122 × 24 / 1500 ≈ 1.95 h per rack",
        estimated=True,
        blurb="Install/integration hours per rack (factory-integrated pace).",
    ),
    "bringup_h": Constant(
        value=24, unit="h",
        source="estimate — burn-in, fabric bring-up, storage mount for a "
               "cluster-scale system",
        estimated=True,
        blurb="Hours of cluster bring-up after the last rack lands.",
    ),
    "ramp_floor": Constant(
        value=0.3, unit="fraction",
        source="estimate — early training steps run while parallelism and "
               "dataloaders are still being tuned",
        estimated=True,
        blurb="Utilization at the first training hour, before the ramp.",
    ),
    # --- Resilience (defaults sourced in the scenario, math constants here) ---
    "mtbf_reference": Constant(
        value=50000, unit="h per GPU",
        source="arithmetic on Meta's Llama-3 405B report — 419 unplanned "
               "interruptions in 54 days on 16,384 GPUs: 16384 × 54 × 24 / "
               "419 ≈ 50,700 h between failures per GPU",
        estimated=True,
        blurb="Reference per-GPU MTBF for the checkpoint arithmetic.",
    ),
    "tokens_reference": Constant(
        value=200, unit="tokens/s per GPU",
        source="arithmetic on Meta's Llama-3 405B report — ~15T tokens over "
               "54 days on 16,384 GPUs ≈ 196 tokens/s per GPU",
        estimated=True,
        blurb="Reference per-GPU training throughput for a frontier model.",
    ),
}


def value(name: str) -> float:
    """Shorthand the engine uses; keeps call sites terse."""
    return CONSTANTS[name].value
