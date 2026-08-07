# 03 — Networking: PowerSwitch SN6000, PowerSwitch E3200, NVIDIA Quantum-X800 (Dell-integrated)

All are **Archetype C (Fabric/Topology)**. Build one fabric engine; parameterize per product.

## Shared fabric engine
- **Topology builder:** drag nodes (servers, switches, uplinks) onto a canvas or pick canned topologies: single ToR, leaf-spine (config: leaf count, spine count, uplinks per leaf), fat-tree/rail-optimized for AI. Ports have speeds; links connect ports.
- **Traffic model:** define flows (src group → dst group, demand in Gb/s, pattern: uniform, incast, all-to-all, elephant/mice mix). Per-link utilization = sum of flows routed across it (ECMP split across equal paths). No packet-level simulation — flow-level fluid model only.
- **The two core lessons, as first-class mechanics:**
  1. **Oversubscription:** downlink capacity ÷ uplink capacity per leaf, displayed prominently; congestion appears exactly where the ratio predicts.
  2. **Congestion → latency/loss:** per-link, utilization > ~90% → queue-delay curve rises steeply (same 1/(1−ρ) shape as the storage engine — point this out in explain mode); >100% demand → drops (or PFC pause propagation in lossless mode, see SN6000/X800).
- **Failure toggles:** kill any link or switch → flows re-route over survivors; watch utilization concentrate. "Gray failure" toggle: a link silently drops 0.1% (flows suffer, nothing looks down — teaches why telemetry matters).
- **Instruments:** per-link utilization heat coloring on the canvas, worst-link gauge, aggregate delivered vs demanded bandwidth, flow-completion-time proxy, drop/pause counters, oversubscription ratio, switch power draw (port count × per-port W + base, estimates).
- **Explain-mode equations:** oversubscription ratio, ECMP split, queue-delay curve, bisection bandwidth.

## PowerSwitch SN6000 series — AI Ethernet fabric (NVIDIA Spectrum-6 based)
- **What it is (per Dell 2026 materials):** sixth-generation NVIDIA Ethernet switching sold as Dell PowerSwitch; ~102.4 Tb/s per ASIC, 800 Gb/s ports built on 200G SerDes, Spectrum-X optimized (adaptive routing, congestion control), liquid-cooling and co-packaged-optics (CPO) options; series scales to ~409.6 Tb/s switching capacity and up to 2,048 breakout connections for GPU scale-out. Port counts per model: `verify` (e.g., SN6600-LD lists 128×800GbE).
- **Config:** model tier (capacity + port count, `verify`), breakout mode (800G → 2×400G/4×200G), air vs liquid cooling variant, CPO vs pluggable optics.
- **Personality mechanics:**
  - **Adaptive routing toggle:** OFF = static ECMP (hash collisions modeled as uneven link loads under all-to-all traffic); ON = loads rebalance toward even. Show delivered-bandwidth delta — this is Spectrum-X's pitch made tangible.
  - **Optics power lesson:** pluggable optics ~15–25 W/port vs CPO fraction of that (estimates) — at 128 ports the optics power rivals the ASIC; a toggle makes the switch-power instrument jump. Ties to liquid-cooling option.
  - **Lossless (RoCE) mode:** congestion emits pause frames upstream instead of drops — visualize pause propagation (head-of-line spreading) vs drop mode.
- **Scenarios:** "Build a 1,024-GPU fabric" (rail-optimized leaf-spine sized for XE9680 nodes from file 01); "Hash collision" (adaptive routing off/on under all-to-all); "The optics bill" (CPO vs pluggable at scale).

## PowerSwitch E3200 series — campus/edge access switching
- **What it is:** Dell campus/access-layer PowerSwitch line. Exact port configurations, PoE budgets, and stacking limits: `verify` against Dell's E3200 spec sheet before coding constants — do not guess model-level specs.
- **Sim reframe:** the fabric engine at building scale: access switches → distribution → core. New mechanic: **PoE budget** — each access port can power a device (AP ~15–30 W, camera ~13 W, phone ~7 W, estimates); total PoE demand vs switch PoE budget is the validation rule that binds first. Uplink oversubscription lesson applies at 1G/10G/25G scale instead of 800G.
- **Failure toggles:** PSU loss halves PoE budget (which devices drop? — priority config); uplink loss → STP/stack failover pause (model as brief outage event).
- **Scenarios:** "Wire a floor" (48 devices, watch PoE budget vs port count); "One uplink down at 9 am" (traffic concentrates, latency curve on the survivor).
- Pedagogical role: shows the same physics as SN6000 at human scale — good first networking sim.

## NVIDIA Quantum-X800 (Dell-integrated InfiniBand)
- **What it is (per Dell 2026 materials):** NVIDIA Quantum-X800 InfiniBand platform offered within Dell AI Factory; the Q3300-LD variant is a fully liquid-cooled OSFP switch for AI/HPC. Port counts/speeds (800G-class XDR): `verify`.
- **Personality vs SN6000 (the point of including both):** InfiniBand is lossless-native with credit-based flow control and subnet-manager routing; model as: no drops ever, congestion manifests purely as backpressure/queueing; **in-network computation toggle (SHARP-style reduction):** ON = collective operations (all-reduce traffic pattern) consume dramatically less link bandwidth — show delivered all-reduce time improve. Keep it conceptual; label the mechanism plainly.
- **Scenarios:** "Ethernet vs InfiniBand, same topology" (side-by-side run of SN6000 and X800 personalities under identical AI traffic — the suite's best A/B lesson); "Collectives in the network" (SHARP toggle under all-reduce).
- **Liquid cooling:** reuse the coolant-loop instrument from XE9712 (file 01) for the Q3300-LD variant.
