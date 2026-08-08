"""Every model constant with units and a source — data & observability
edition."""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    "gpu_process_speedup": Constant(
        value=6.0, unit="×",
        source="estimate — Dell cites a 6×-class GPU-acceleration claim; verify against Dell AI Data Platform materials",
        estimated=True,
        blurb="Process-stage speedup with GPU acceleration on.",
    ),
    "gpu_analytics_speedup": Constant(
        value=6.0, unit="×",
        source="estimate — Starburst-engine GPU scan claim; verify and cite Dell",
        estimated=True,
        blurb="Analytics scan speedup with GPU acceleration on.",
    ),
    "base_sessions": Constant(
        value=40, unit="concurrent long-context sessions",
        source="estimate — KV cache resident in GPU memory", estimated=True,
        blurb="Long-context inference sessions GPU memory alone can hold.",
    ),
    "kv_offload_multiplier": Constant(
        value=4.0, unit="×",
        source="estimate — KV spill to fast shared storage (NVIDIA CMX-class)",
        estimated=True,
        blurb="Session-capacity multiplier when KV cache spills to shared storage.",
    ),
    "kv_latency_tax_pct": Constant(
        value=12, unit="% per token",
        source="estimate — the small price of the freed GPU memory", estimated=True,
        blurb="Per-token latency tax when sessions run from offloaded KV cache.",
    ),
    # --- CloudIQ ------------------------------------------------------------
    "fleet_servers": Constant(
        value=20, unit="servers", source="spec 06 — the synthetic fleet",
        estimated=False, blurb="Servers in the standalone synthetic fleet.",
    ),
    "fleet_arrays": Constant(
        value=3, unit="arrays", source="spec 06", estimated=False,
        blurb="Arrays in the synthetic fleet.",
    ),
    "fleet_switches": Constant(
        value=4, unit="switches", source="spec 06", estimated=False,
        blurb="Switches in the synthetic fleet.",
    ),
    "baseline_fill_pct_day": Constant(
        value=0.3, unit="%/day", source="estimate — organic growth", estimated=True,
        blurb="Baseline array fill rate.",
    ),
    "issue_fill_pct_day": Constant(
        value=2.5, unit="%/day", source="estimate — the injected capacity issue",
        estimated=True,
        blurb="Fill rate once the capacity issue is injected.",
    ),
    "noise_sigma": Constant(
        value=1.0, unit="σ units", source="modeling choice — deterministic sinusoid mix",
        estimated=False,
        blurb="Amplitude of the deterministic metric noise (no randomness).",
    ),
    "issue_signal_sigma": Constant(
        value=1.2, unit="σ per day active",
        source="estimate — real issues drift away from baseline", estimated=True,
        blurb="How fast an injected issue's metric departs from baseline.",
    ),
    "forecast_window_h": Constant(
        value=168, unit="h", source="estimate — a week of history in the fit",
        estimated=True,
        blurb="Rolling window of the days-to-full linear fit (the source of its lag).",
    ),
}


def value(name: str) -> float:
    return CONSTANTS[name].value
