# 01 — AI Compute: PowerEdge XE7745, XE9680, XE9712, IR7000 rack, iDRAC

All build on **Archetype A (Power/Thermal)** — reuse the R760 engine (zones, fan model, thermal mass, throttling, PSU efficiency, validation rules) and extend it as noted. Read the R760 spec first; only deltas are specified here.

## 1. PowerEdge XE7745 — 4U PCIe GPU server
**What it teaches:** air-cooled GPU density and the PCIe-attached GPU model (vs. SXM/NVLink).
- **Config:** 2 CPUs (TDP tiers as R760); 0–8 double-wide PCIe GPUs in 300–600 W tiers; DIMMs, NVMe, NICs as R760; PSU capacities up to 2800 W class, N+N. Mark exact GPU counts/riser rules `verify` against Dell's XE7745 spec sheet.
- **New physics:** GPU zone becomes the dominant heat path; model GPU inlet preheat from upstream components; per-GPU thermal throttle. Fan wall scaled up (higher max airflow, higher max fan power ~ hundreds of watts total — teach that fan overhead at full bore is non-trivial).
- **New validation rules:** GPU count × TDP vs PSU capacity; GPU tier vs max supported ambient (restriction-matrix style, `verify`); mixed-GPU-tier warning.
- **Key scenario:** "8 GPUs at 30 °C inlet" — watch fan power climb and one GPU (worst airflow position) throttle first. Teaches positional thermal inequality inside a chassis.
- **Sanity range:** maxed config full load ≈ 6–10 kW DC (estimate).

## 2. PowerEdge XE9680 — 8-way HGX GPU server (6U)
**What it teaches:** the SXM baseboard model — 8 GPUs on one HGX board with NVLink, the flagship air-cooled AI trainer.
- **Config:** fixed 8× SXM GPU baseboard (selectable GPU tier: 700 W-class H100-style, 1000 W-class B200-style, `verify`); 2 CPUs; up to 32 DIMMs; NVMe; up to 8 or more high-speed NICs (400G class) — NIC power matters here (~25–35 W each, estimate); 4–6 PSUs.
- **New physics:** GPU-to-GPU coupling — the HGX board is one thermal zone with shared fate: all 8 throttle together (simplification worth a footnote). Model "GPU busy vs stalled waiting on data": a **data-starvation slider** (0–100%) that caps effective GPU utilization — power drops but so does simulated training throughput (tokens/s proxy). This links to the storage specs (file 02) conceptually.
- **Instruments add:** training-throughput proxy, GPU-hours wasted to stalls, per-kW-of-IT cooling burden.
- **Key scenarios:** "Why AI servers are power-plant problems" (idle vs full: ~1 kW → ~10+ kW swing, estimate); "Starved GPUs" (high power, low useful output when data pipeline slider is low).
- **Sanity range:** full load ≈ 10–12 kW DC (estimate).

## 3. PowerEdge XE9712 — rack-scale liquid-cooled NVL72-class system
**What it teaches:** the shift from server-level to **rack-level** design: 72-GPU NVLink domain, direct liquid cooling (DLC), busbar power.
- **Scope change:** the simulated unit is the whole rack, not one server. Components: N compute trays (each: 2 CPU + 4 GPU superchip-style, `verify`), NVLink switch trays, power shelves feeding a DC busbar, liquid cooling loop to a CDU.
- **New physics — liquid loop:** coolant supply temp (slider 17–45 °C), flow rate, ΔT across rack; heat removed = ṁ·cp·ΔT with water cp = 4186 J/(kg·K). Small residual air-cooled fraction (~10–15%, estimate) still hits the room. Failure toggles: pump degradation, CDU supply-temp excursion, single-tray coolant restriction → tray-level throttle then trip.
- **Instruments add:** total rack power (target sanity ≈ 100–130 kW class at full load, estimate), coolant ΔT, liquid vs air heat split, PUE-style overhead comparison vs the XE9680 air-cooled equivalent.
- **Key scenario:** "Air vs liquid" — same GPU count as 9 hypothetical XE9680s; compare fan overhead vs pump overhead and room heat load. This is the single best cross-product lesson in the suite.

## 4. IR7000 — Integrated Rack for liquid-cooled AI systems
**What it teaches:** the rack itself as a product: power distribution, manifolds, serviceability.
- **Model:** not a separate physics engine — an **environment container** for XE9712-style trays. Config: rack height/tray slots, power shelf capacity and redundancy, manifold capacity, optional rear-door heat exchanger for the air fraction. `verify` all capacities against Dell IR7000 documentation.
- **Validation rules are the product here:** tray power sum vs busbar/power-shelf capacity; coolant demand vs manifold capacity; weight budget (floor-loading advisory).
- **Key scenario:** "Populate the rack" — add trays until a rule trips; teaches that at rack scale, power and coolant budgets bind before space does.
- Implementation note: build IR7000 and XE9712 as one app with the rack as the outer model.

## 5. iDRAC — server management plane (cross-cutting)
**What it teaches:** out-of-band management — the thing that would turn these sims into twins.
- **Not a physics sim.** Archetype D flavor: a simulated iDRAC web console UI bound to the R760/XE simulator state. Panels: sensor dashboard (reads live values from the running sim), virtual power control (power cycle the sim), fan-offset control (bias the fan floor and watch consequences), simulated SEL (System Event Log — mirror the sim's event log in iDRAC's format), firmware level as a config attribute, and a **mock Redfish API explorer**: a panel showing `GET /redfish/v1/Chassis/.../Thermal` returning live JSON from the sim. Redfish schema shapes: `verify` against DMTF/Dell docs.
- **Key scenario:** "From sim to twin" — poll the mock Redfish endpoint from the explain panel; narrate that a real twin replaces the sim's synthetic state with these same calls against real hardware. Closes the loop on the digital-twin discussion that motivated this suite.
