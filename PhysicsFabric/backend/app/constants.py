"""Every model constant with units and a source — fabric edition."""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- Congestion mechanics ---------------------------------------------
    "queue_onset": Constant(
        value=0.90, unit="fraction of link",
        source="estimate — spec 03: queue delay rises steeply past ~90%",
        estimated=True,
        blurb="Utilization where the queue-delay curve starts to bite.",
    ),
    "rho_clamp": Constant(
        value=0.985, unit="—", source="1/(1−ρ) divergence guard — modeling choice",
        estimated=False,
        blurb="Utilization clamp in the queue-delay multiplier.",
    ),
    "base_hop_us": Constant(
        value=1.0, unit="µs/hop", source="estimate — cut-through switch + serialization",
        estimated=True,
        blurb="Per-hop latency at an idle fabric.",
    ),
    # --- ECMP & adaptive routing -----------------------------------------
    "imbalance_uniform": Constant(
        value=0.25, unit="fraction over fair share",
        source="estimate — hash-collision skew, uniform traffic", estimated=True,
        blurb="Worst-link excess over fair ECMP share, static hashing.",
    ),
    "imbalance_alltoall": Constant(
        value=0.50, unit="fraction over fair share",
        source="estimate — many synchronized flows collide harder", estimated=True,
        blurb="Worst-link excess under all-to-all, static hashing.",
    ),
    "imbalance_elephant": Constant(
        value=0.85, unit="fraction over fair share",
        source="estimate — a few huge flows pin whole links", estimated=True,
        blurb="Worst-link excess with elephant flows, static hashing.",
    ),
    "adaptive_residual": Constant(
        value=0.15, unit="fraction of static imbalance",
        source="estimate — Spectrum-X-style adaptive routing rebalances most of the skew",
        estimated=True,
        blurb="Residual imbalance with adaptive routing on.",
    ),
    "incast_concentration": Constant(
        value=4.0, unit="× fair share",
        source="estimate — many senders, one receiver", estimated=True,
        blurb="Hot-leaf downlink concentration under the incast pattern.",
    ),
    # --- Loss / lossless ---------------------------------------------------
    "pps_per_gbps": Constant(
        value=83000, unit="packets/s per Gbps",
        source="1500 B packets — arithmetic", estimated=False,
        blurb="Packet rate per Gbps at 1500-byte packets, for the drop counter.",
    ),
    "pause_spread_factor": Constant(
        value=1.5, unit="× congested links",
        source="estimate — PFC head-of-line spreading", estimated=True,
        blurb="How far pause frames spread congestion upstream.",
    ),
    "gray_loss_fraction": Constant(
        value=0.001, unit="fraction", source="spec 03 — 0.1% silent loss",
        estimated=False,
        blurb="Loss rate of the gray-failed link. Nothing reports down.",
    ),
    "gray_goodput_penalty": Constant(
        value=35, unit="% goodput lost on affected flows",
        source="estimate — TCP/RoCE retransmit collapse under 0.1% loss",
        estimated=True,
        blurb="Goodput penalty for flows crossing the gray link.",
    ),
    "sharp_link_relief": Constant(
        value=0.5, unit="fraction of collective traffic",
        source="estimate — in-network reduction halves what crosses the fabric",
        estimated=True,
        blurb="Share of all-reduce bytes SHARP keeps off the links.",
    ),
    "sharp_speedup": Constant(
        value=1.8, unit="× effective all-reduce rate",
        source="estimate — NVIDIA SHARP collective acceleration class",
        estimated=True,
        blurb="Effective all-reduce rate gain with SHARP on.",
    ),
    # --- Power --------------------------------------------------------------
    "asic_base_w": Constant(
        value=550, unit="W", source="estimate — Spectrum-class ASIC + board",
        estimated=True, blurb="Per-switch base power (ASIC, board, fans share).",
    ),
    "optic_pluggable_w": Constant(
        value=18, unit="W/port", source="estimate — spec 03: 15–25 W for 800G pluggables",
        estimated=True, blurb="Per-port pluggable optic power.",
    ),
    "optic_cpo_w": Constant(
        value=6, unit="W/port", source="estimate — co-packaged optics fraction",
        estimated=True, blurb="Per-port co-packaged optic power.",
    ),
    "campus_switch_base_w": Constant(
        value=60, unit="W", source="estimate — access-switch base draw",
        estimated=True, blurb="E3200 per-switch base power (before PoE delivery).",
    ),
    # --- PoE (spec 03 device table) -----------------------------------------
    "poe_ap_w": Constant(
        value=20, unit="W", source="estimate — spec 03: AP 15–30 W", estimated=True,
        blurb="Per-access-point PoE draw.",
    ),
    "poe_camera_w": Constant(
        value=13, unit="W", source="estimate — spec 03", estimated=True,
        blurb="Per-camera PoE draw.",
    ),
    "poe_phone_w": Constant(
        value=7, unit="W", source="estimate — spec 03", estimated=True,
        blurb="Per-phone PoE draw.",
    ),
    "stp_failover_s": Constant(
        value=2, unit="s", source="estimate — rapid-STP reconvergence class",
        estimated=True,
        blurb="Outage seconds when an access uplink fails.",
    ),
    # --- FCT proxy ----------------------------------------------------------
    "fct_flow_mb": Constant(
        value=64, unit="MB", source="modeling choice", estimated=False,
        blurb="Reference flow size for the flow-completion-time proxy.",
    ),
}


def value(name: str) -> float:
    return CONSTANTS[name].value
