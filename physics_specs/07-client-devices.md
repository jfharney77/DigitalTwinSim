# 07 — Client Devices: Alienware, Dell Pro Max Plus

Both are **Archetype A (Power/Thermal)** — direct reuse of the R760 engine at laptop/desktop scale, plus a battery model. These are excellent second builds after the R760 because they prove the engine generalizes.

## Shared client-device extensions to the Archetype-A engine
- **Battery model:** capacity (Wh), charge/discharge state; on battery, total system power drains it (runtime = Wh ÷ W, with a discharge-efficiency factor ~0.92, estimate); charging adds heat (~10% of charge power, estimate). Battery-wear toggle: 80% health reduces capacity and raises internal-resistance heat slightly.
- **Power-limit regimes (the core laptop lesson, absent from servers):** silicon has PL1 (sustained) and PL2 (burst) power limits; on load spike, power jumps to PL2 for a boost window (τ ~28 s, estimate) then settles to PL1 as the skin-temp limit binds. Performance readout tracks power, so users SEE the burst-then-fade shape that defines laptop benchmarks.
- **Skin-temperature constraint:** unlike servers, the chassis touches humans — add a skin-temp zone with a hard cap (~45–48 °C, estimate) that overrides fan logic and forces power-limit reduction. "Performance mode" toggles trade skin temp + noise vs sustained watts.
- **Acoustics proxy:** fan rpm% → dB(A) curve (estimate); instrument it — noise is a first-class output for client devices.
- **Environment knobs:** ambient temp, on-lap vs on-desk toggle (bottom-intake blockage), charger wattage (an undersized charger under full load drains the battery WHILE plugged in — great scenario).

## Alienware — gaming desktop/laptop
- **Config:** pick form factor: laptop (16/18-class) or desktop tower. CPU tier + discrete GPU tier (laptop GPUs: 80–175 W TGP tiers; desktop: 200–450 W tiers, estimates); RAM, NVMe; laptop: battery Wh; desktop: PSU wattage with the same efficiency-curve model as R760.
- **Workload presets:** idle, esports title (GPU 60%/CPU 40%), AAA ray-traced (GPU 100%/CPU 70%), streaming+gaming (both high + encode load), synthetic stress.
- **Personality:** **shared thermal budget** — laptop CPU and GPU share heat pipes: a combined dissipation cap means max CPU + max GPU simultaneously is impossible; dynamic power-shift logic favors GPU under game load (model as a budget allocator; visualize as two bars fighting over one cap). Frame-rate proxy = f(GPU power delivered) so throttling becomes visible as FPS sag.
- **Scenarios:** "The 10-minute benchmark lie" (burst vs sustained: FPS at minute 1 vs minute 15); "On-lap gaming" (blocked intake cascade); "Quiet mode cost" (cap fans, watch FPS); "The undersized charger" (180 W charger vs 230 W load).
- Sanity: gaming laptop full load ≈ 200–280 W system, desktop ≈ 400–800 W (estimates).

## Dell Pro Max Plus — mobile workstation (with enterprise NPU option)
- **What it is:** Dell's Pro Max plus-tier mobile workstation line (2025+ branding); notable option: an enterprise-class discrete NPU (Qualcomm AI-100-based) for on-device AI inference. Exact SKUs/TDPs: `verify` against Dell Pro Max Plus spec sheets.
- **Config:** CPU tier, workstation GPU tier, optional **discrete NPU card** (~tens of watts, `verify`), RAM up to workstation scale, battery Wh.
- **Personality — on-device AI inference:** a third compute unit competing for the shared thermal budget. Inference workload preset (local LLM, tokens/s proxy) can run on: CPU (slow, watts-hungry per token), GPU (fast, hot), or NPU (moderate speed, dramatically better tokens-per-joule — estimates). Instrument **tokens per joule** per engine — the efficiency argument for NPUs, made experimental.
- **Sustained-workstation lesson:** ISV-style workloads (render, simulate) run for hours — sustained (PL1) performance and acoustics matter more than burst; contrast directly with the Alienware burst personality in a shared scenario.
- **Scenarios:** "Same model, three engines" (run the LLM preset on CPU/GPU/NPU: speed, heat, battery drain, tokens/joule); "8-hour render on battery?" (spoiler: no — do the Wh math live); "Meeting-room inference" (NPU keeps fans near-silent while the GPU option sounds like the Alienware).
