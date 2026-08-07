# Spec: Interactive Dell PowerEdge R760 Power & Thermal Simulator

Status: **built** as `DellPowerEdgeR760Thermal/` (2026-08-07, backend :8030,
frontend :5203) following the §11 repo adaptations. This file is kept as
the design record.

## 1. Purpose and framing

Build an educational, interactive simulator of a Dell PowerEdge R760 2U server. The user configures a hypothetical unit (CPUs, memory, drives, GPUs, PSUs), assigns a workload, and adjusts a small set of environmental variables. The app computes power draw, per-zone temperatures, and fan response in real time, and visualizes the causal chain: **configuration → load → power → heat → fan response → feedback**.

This is NOT a digital twin (no live telemetry) and NOT CFD. It is a simplified, legible physics model — a "flight simulator" for understanding the platform. Correct *relationships and orders of magnitude* matter more than exact numbers. All constants must live in one editable data file so the user can refine them against Dell's published documentation over time.

**[ADJUSTED for this repo.]** The 2D diagram of the R760 internals already exists here: `DellPowerEdgeR760/backend/app/anatomy.py` is a tested, stylized 100×46 top-down chassis floorplan with stable region ids, rendered by `ChassisView.tsx`. Use it as the default chassis view — thermal zones (§5.1) map onto its region ids, and the temperature coloring becomes a second paint mode over the same regions the power-on twin lights. Do not draw a second, independent R760 that can drift from the first; the custom-image overlay stays as the drop-in option.

## 2. Tech constraints

- **[ADJUSTED for this repo — was "no backend, everything client-side".]** Follow the repo's twin split: a **pure Python engine** (FastAPI backend) and a React/Vite frontend that owns only the playback clock. The engine exposes `POST /api/simulate` taking a `Scenario` — configuration (§3), workload (§4), environment (§5.4), and a list of **timed events** (fan kill at t=120 s, inlet ramp, PSU pull, workload change) — and returns the full timestepped trace as plain data. The frontend animates the trace and re-requests on any change. This is the `DellAlienware/` twin's exact pattern (`Scenario → Summary + PowerState[]`), and it is what makes §9's acceptance criteria enforceable as backend pytest invariants instead of manual checks. Interactive dials that "change mid-flight" become scenario events, keeping the engine deterministic and AST-pure (no timers, no IO — checked by test, as in every twin here).
- Simulation loop: fixed sim timestep (e.g., 500 ms) **computed in the engine**; the ×1 / ×10 / ×60 time-multiplier is frontend playback pacing only (the clock lives in `App.tsx`, never in the engine — repo invariant).
- All model constants in **`backend/app/constants.py`** (backend data, like every twin's `anatomy.py`/`catalog.py`), each with units and a `source` field (e.g., "Dell R760 Technical Guide, Table X", "estimate — refine"). Backend tests validate the constants table itself (every constant has a source; every `estimate` is surfaced to the UI). The frontend receives constants over the wire — no second copy.
- No fabricated Dell part numbers or invented spec values presented as fact. Where a real value is unknown, use a clearly labeled estimate (`source: "estimate"`), and surface an "estimated" badge in the UI tooltip for any readout derived primarily from estimates.

## 3. Configuration model (what the user can build)

Represent the server as a typed configuration object. Options below reflect the real R760 platform envelope; keep the list editable in the constants file.

### 3.1 CPUs
- 1 or 2 sockets. 4th/5th Gen Intel Xeon Scalable.
- Model the CPU abstractly by **TDP tier**, not by exact SKU: selectable TDP values {125 W, 150 W, 185 W, 205 W, 250 W, 270 W, 300 W, 330 W, 350 W}.
- Each tier carries: base power at idle (~12–18% of TDP, estimate), max sustained power (= TDP), and a boost/turbo multiplier (short excursions to ~1.15× TDP for up to 60 sim-seconds, then settle to TDP).
- Heatsink requirement rule: TDP ≥ 250 W requires "high-performance heatsink"; TDP ≥ 300 W requires "high-performance heatsink + high-performance (Gold) fan kit". Encode as a validation rule (see §6).

### 3.2 Memory
- Up to 32 DDR5 DIMM slots (16 per CPU). Selectable population: 8 / 16 / 24 / 32 DIMMs, sizes 16–96 GB.
- Power per DIMM: idle ~1.5 W, active ~4 W at full memory bandwidth utilization (estimates; scale linearly with memory load component of the workload).
- Airflow rule: fully populated DIMM banks slightly increase airflow resistance → model as a small (~5%, estimate) penalty to effective airflow through the CPU zone.

### 3.3 Storage
- Front bay options: 12× 3.5", or 24× 2.5" SAS/SATA/NVMe, or 16× E3.S NVMe (choose one chassis config at build time).
- Per-drive power: 3.5" HDD ~8 W active / 5 W idle; 2.5" SSD ~4 W active / 2 W idle; NVMe ~12 W active / 5 W idle (estimates).
- Drives sit in the front intake path: total drive count adds airflow resistance ahead of everything else (each populated drive ~0.5% airflow penalty, estimate, capped at 15%).

### 3.4 GPUs / PCIe
- 0–2 double-wide GPUs (e.g., 300 W class) or 0–6 single-wide accelerators (75 W class). Riser config is implied; don't model risers in detail.
- Any double-wide GPU forces the "high-performance (Gold) fan kit" and raises minimum fan floor (see §5.3).
- NICs/HBAs: flat selectable aggregate "I/O card power" 0–100 W.

### 3.5 PSUs
- 1 or 2 PSUs; capacities {800 W, 1100 W, 1400 W, 2400 W}. Redundancy modes: 1+0, 1+1.
- PSU efficiency curve (Titanium-class approximation): 90% at 10% load, 94% at 20%, 96% at 50%, 94% at 100% (estimates). Wall power = DC load / efficiency at that load point. Show both DC and AC (wall) watts.
- Validation: total max DC load must fit within N (non-redundant) or 1 PSU (1+1). Warn, don't block, on oversubscription — and simulate the consequence (PSU overcurrent trip at 105% sustained for 30 sim-seconds → server hard-off event).

## 4. Workload model (assigning load)

A workload is a set of utilization dials, each 0–100%:
- **CPU utilization** (drives CPU power between idle and TDP, nonlinearly: power ≈ idle + (TDP − idle) × util^1.4, estimate of realistic curve).
- **Memory bandwidth utilization** (drives DIMM active power).
- **Storage IOPS level** (drives drive active power).
- **GPU utilization** (drives GPU power similarly to CPU curve).

Provide preset workload profiles as buttons: `Idle`, `Web serving` (CPU 35 / Mem 30 / Sto 20 / GPU 0), `Database` (CPU 60 / Mem 75 / Sto 70 / GPU 0), `HPC` (CPU 100 / Mem 80 / Sto 10 / GPU 0), `AI training` (CPU 50 / Mem 70 / Sto 40 / GPU 100), plus `Custom`.

Optional stretch: a 24-hour schedule editor (simple step chart) that varies the profile over sim time, so the user can watch diurnal thermal behavior at ×60 speed.

## 5. Physics model (simplified, legible — no CFD)

### 5.1 Zone model
Divide the chassis into serial/parallel thermal zones along the front-to-back airflow path:

```
[Front: drive bays] → [Fan wall: 4–6 hot-swap fans] → split into lanes:
   Lane A: [DIMM bank 1] → [CPU1] → [DIMM bank 2] → [CPU2] → rear
   Lane B: [PCIe/GPU zone] → rear
[PSUs draw their own rear airflow — model separately, simplified]
```

Each zone has: heat input Q (W) from its components, airflow share ṁ (kg/s) of total system airflow, and inlet temp = upstream zone's outlet temp. Outlet temp = inlet + Q / (ṁ × cp), with cp = 1005 J/(kg·K). Air density derated by altitude (see §5.4).

### 5.2 Thermal mass (so nothing is instantaneous)
Each major component (CPU dies, GPU, drive group) has a first-order thermal time constant: T_component approaches its steady-state value exponentially, τ = 20 s for CPU/GPU silicon+heatsink, τ = 300 s for drive group, τ = 600 s for "chassis bulk" (estimates). This is what makes the time-multiplier control worthwhile.

### 5.3 Fan model and control loop
- Fan wall: 6 fans standard config. Each fan: max airflow contribution and cubic power law — fan power ≈ P_max × (rpm%)³, with P_max ≈ 25 W/fan for Gold kit, 15 W standard (estimates). **Fan power feeds back into total system power.** This feedback is a core teaching point; surface it explicitly in the UI.
- Control: proportional controller stepped each tick. Target: keep CPU temp ≤ (Tjmax_proxy − margin), e.g., target 85 °C, and drive/ambient zones within limits. Fan floor: 15% idle; GPU config raises floor to 30%.
- Total airflow = f(average rpm%) linear approximation, reduced by the airflow penalties from §3 (drives, DIMMs).

### 5.4 Environment knobs (deliberately few)
- **Inlet air temperature**: 15–45 °C slider. Annotate ASHRAE A2 recommended/allowable bands on the slider itself.
- **Altitude**: 0–3000 m slider. Air density scales by ~−9% per 1000 m; annotate Dell-style derating note ("supported ambient decreases ~1 °C per 300 m above 950 m" — encode that as a validation warning, source it).
- **Hot-aisle recirculation**: 0–100% slider that mixes a fraction of the server's own exhaust temp back into its inlet. This one knob captures the "heat from other racks / bad containment" concept from earlier design discussions without any room CFD.
- No oxygen/humidity modeling. Humidity may be listed as a labeled non-factor in the UI's "what we don't model" footnote.

### 5.5 Protective behaviors (teachable failure modes)
- **CPU thermal throttling**: if CPU temp exceeds throttle threshold (e.g., 98 °C proxy), clamp CPU power in 10% steps per tick until temp recovers; show a prominent "THROTTLING" badge and the % performance lost.
- **GPU throttling**: same pattern at its own threshold.
- **Critical overtemp shutdown**: sustained CPU ≥ 105 °C proxy or inlet ≥ 55 °C → simulated emergency power-off event with an event-log entry.
- **Fan failure toggle**: per-fan kill switches. Remaining fans ramp to compensate (respecting max rpm); show the resulting noise/power/thermal consequences.
- **PSU failure toggle**: in 1+1, surviving PSU takes full load (watch its efficiency point change); in 1+0, instant power-off event.
- **Airflow blockage**: a "blocked intake %" slider (dust/failed blanking) reducing total airflow.

## 6. Validation rules engine

Rules evaluated on every config change; each yields `ok | warning | error` with a human-readable explanation and a `source` citation field. Initial rule set:
1. TDP ≥ 250 W ⇒ requires HP heatsink (error if not selected).
2. TDP ≥ 300 W or any double-wide GPU ⇒ requires Gold fan kit (error).
3. High TDP + high inlet temp combos ⇒ warning: "reduced maximum supported ambient" (thresholds in constants file, marked estimate until user sources Dell's restriction matrix).
4. PSU capacity vs. max theoretical draw (per §3.5).
5. Altitude ≥ 950 m ⇒ ambient derating advisory.
The rules panel should read like a mini version of Dell's thermal restriction documentation — that's the pedagogical intent.

## 7. UI layout

Three-column responsive layout (stack on narrow screens):

**Left — Build panel.** Configuration controls (§3), preset config buttons ("Entry", "Balanced", "Max CPU", "GPU node"), validation results inline under the relevant control plus a summary strip.

**Center — Chassis view.** 2D top-down schematic of the R760 interior (SVG). Zones colored by temperature on a fixed 20–110 °C color scale (legend required, color-blind-safe palette). Animated airflow arrows whose speed reflects fan rpm and whose color reflects air temp along the path (front cold → rear hot). Clicking any component opens a detail card: its current power, temp, time constant, and the formula currently governing it (render the actual equation with live numbers substituted — this is a key educational feature). Fan wall shows per-fan rpm% and per-fan kill switches. Support swapping this SVG for the user's own 2D diagram via a config option (their image as background + positioned hotspot overlays defined in one JSON file).

**Right — Instruments.** 
- Live readouts: total DC power, wall (AC) power, PSU efficiency point, fan power (highlighted as "overhead"), per-zone temps, CPU/GPU temp with throttle margin bars, airflow (CFM), exhaust temp, and ΔT front-to-back.
- Strip charts (last 10 sim-minutes): total power, CPU temp, fan rpm%, on shared time axis so cause-and-effect alignment is visible.
- Event log (throttle events, failures, shutdowns, rule violations) with sim timestamps.
- Environment panel (§5.4 sliders) and workload panel (§4 dials + presets).
- Time controls: pause / ×1 / ×10 / ×60, and a "reset to cold start" button.

## 8. Educational layer (differentiator — do not cut)

- **Explain mode toggle.** When on, every readout gets an ⓘ affordance showing: what this quantity is, the equation producing it with current values substituted, and which inputs affect it (rendered as a small causal diagram: e.g., `CPU util → CPU power → CPU heat → fan rpm → fan power → total power`).
- **Guided scenarios.** 5–8 scripted walkthroughs that set the config/environment and narrate what to watch, each ending with a question the user can verify by experiment. Minimum set:
  1. "Idle to full load" — watch thermal time constants and fan lag.
  2. "The fan-power feedback loop" — raise inlet temp; watch fan power climb wall power even at constant workload.
  3. "Kill a fan" — redundancy and its thermal cost.
  4. "The 350 W problem" — why max-TDP configs constrain ambient range.
  5. "Recirculation death spiral" — raise recirculation until exhaust feeds inlet into runaway; discuss containment.
  6. "PSU efficiency sweet spot" — same workload on 1 vs 2 PSUs; observe wall watts.
  7. "Altitude" — same config at 0 m vs 2500 m.
- **"What we don't model" footnote** listing simplifications honestly (no CFD, no per-core DVFS, no VR losses, humidity, acoustics only as rpm proxy, all `estimate`-tagged constants pending user calibration against Dell docs).

## 9. Acceptance criteria

1. Cold-start idle: a modest config (1× 150 W CPU, 8 DIMMs, 2 SSDs, 1+1 800 W) settles near 90–140 W wall power with fans near floor.
2. Max config at 100% HPC load: total DC power plausibly in the 1.2–1.9 kW range and CPU temps stabilize below throttle at 22 °C inlet with Gold fans.
3. Raising inlet from 22 °C to 40 °C at high load produces visible fan ramp, higher wall power, and eventually throttling — in that order, with lag.
4. Every failure toggle produces a distinct, logged, visually obvious consequence.
5. All constants live in one file; changing a constant changes behavior without touching component code.
6. Explain mode shows live-substituted equations for at least: CPU power, zone outlet temp, fan power, PSU wall power.
7. No invented Dell specifications presented as authoritative; every constant has a `source` field.

## 10. Phasing (suggested)

- **Phase 1:** Config model + power model + validation rules + instruments (no thermal sim yet). Static "steady-state" calculation.
- **Phase 2:** Time-stepped thermal zones, fan controller, feedback loop, strip charts.
- **Phase 3:** Failure toggles, protective behaviors, event log.
- **Phase 4:** Explain mode, guided scenarios, custom-diagram overlay support.

Each phase should be independently demo-able.

## 11. Repo adaptation notes (added after review against DigitalTwinSim conventions)

This spec arrived from outside the repo; the sections above marked
**[ADJUSTED]** were changed to fit conventions that are enforced by tests
and `tools/check_twins.py`. The remaining adaptations, to apply at build
time:

1. **Directory and ports.** Build as a sibling twin,
   `DellPowerEdgeR760Thermal/` — it cannot live inside
   `DellPowerEdgeR760/` (one twin directory = one backend, one vite
   config, one `ports.json` entry). Claim backend **:8030**, frontend
   **:5203** (next free after DellQuantumX800's 8029/5202) and register
   them in `ports.json`; the cross-twin linter fails on unregistered
   ports and on any twin missing
   `backend/app/{models,engine,main,leveling}.py`, backend tests, the
   four lifecycle scripts, `frontend/src/level.ts`, and
   `LevelControl.tsx`.

2. **Reading levels.** Ship the shared `leveling.py` mechanism
   (byte-identical across all twins — copy it, and copy
   `tests/test_leveling.py`). The natural home for five-level authoring
   here is the **Explain-mode text** (§8) and the guided-scenario
   narration: level 1 opens the physics up for a newcomer, level 5 is
   the equation and the numbers. Trace-step prose per se does not exist
   in this twin (states are numeric), so leveling attaches to the
   explain/scenario strings served by the backend.

3. **Conservation invariants (free upgrade).** The repo's strongest
   twins carry an identity checked on every step with no tolerance
   (Alienware: `acW + batteryW == systemW + chargeW`; IR7000:
   `liquid + air == IT load`). Adopt two here, as backend tests:
   - **Power balance, every tick:** sum of component DC powers
     (CPU + DIMM + drives + GPU + I/O + fans) == total DC; wall AC ==
     DC ÷ efficiency(load point). The fan-power feedback loop (§5.3)
     then stops being a UI claim and becomes an asserted fact.
   - **Heat balance at steady state:** watts in == heat out through the
     airflow (Q = ṁ × cp × ΔT summed over zones) — the IR7000 twin's
     identity, seen from inside one server. Cross-link the two twins'
     copy in both directions.
   Acceptance criteria §9.1–9.3 become pytest cases against canned
   scenarios; §9.5 becomes "constants live in backend data and a test
   asserts every one carries a source"; §9.7's honesty rule matches the
   repo's existing no-invented-specs norm.

4. **House skin and copy.** Dell clean-design chrome (light, Roboto,
   Dell blue; no eyebrow text, no step numbering, no divider rules);
   the chassis view and strip charts stay dark — they are the
   diagrams. Spell out vocabulary (TDP, DVFS, ASHRAE A2, Titanium
   efficiency, ΔT, Tjmax) on first use. The "what we don't model"
   footnote (§8) matches the repo's scope-guardrail style — keep it.

5. **Cross-references to keep intact.** `DellPowerEdgeR760/` (the same
   machine's power-on story; link both ways — this twin is the R760's
   steady-state physics, that one is its bring-up), `DellIR7000/` (the
   facility side of the heat this twin generates; its "heat in equals
   heat out" is this twin's §5.1 summed over a rack), `DellAlienware/`
   (the scenario→trace precedent and the energy-identity precedent at
   laptop scale), `GPU/` (the roofline behind the AI-training preset),
   and `DellCloudIQ/` (where the telemetry this simulator fakes would
   go in production).

6. **Integration checklist at build time** (the part that keeps the
   repo's meta-tests green): `ports.json` entry; repo-root `index.html`
   hub card; CLAUDE.md twenty-fifth-component section; twin `README.md`;
   and if the CustomerSetup pages ever reference it, per-page rows with
   `data-twin-port/-start/-trace` metadata. Trace endpoint name should
   be `POST /api/simulate` (Alienware style) — note that CustomerSetup's
   `data-twin-trace` enrichment expects a GET endpoint, so if a page
   ever links this twin, also expose `GET /api/simulate` returning the
   default scenario's trace.

7. **Naming note.** The repo reserves "digital twin" loosely; §1's "this
   is NOT a digital twin (no live telemetry)" stays true and worth
   keeping, but the R760 power-on twin makes the same disclaimer in
   spirit (illustrative, not measured). Frame this app in its README as
   the R760's second twin: same machine, different question — "what
   happens when it turns on" vs "what happens while it runs".
