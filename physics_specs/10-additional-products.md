# 10 — Additional Dell Products (expansion roster)

Products not in the original 29 that fit the suite well. Same framework (file 00); physics modules referenced from file 09.

## 1. PowerEdge MX7000 — modular/composable chassis (Archetype A + D)
- **What it is:** Dell's 7U modular platform: compute sleds, storage sleds, networking fabric, and shared power/cooling in one chassis; resources composable across sleds.
- **Why it earns a sim — shared-infrastructure physics:** unlike rack servers, fans and PSUs are chassis-level and shared. One hot sled makes the shared fans spin for everyone (noise/power tax on innocent neighbors); PSU redundancy is pooled (grid vs N+N policies). Composability: reassign storage sleds to different compute sleds as a config action.
- **Modules:** M1, M2, M3, M11 (chassis power budget), M12.
- **Scenarios:** "The noisy neighbor, thermally" (one 100%-load sled vs seven idle — watch shared fan power allocate the pain); "Pooled redundancy math" (grid redundancy survives a whole-feed loss; N+1 doesn't).
- Specs (sled counts, PSU sizes): `verify` against MX7000 documentation.

## 2. PowerEdge XR-series — rugged edge servers (Archetype A)
- **What it is:** short-depth, extended-temperature, NEBS-class servers for cell sites, factories, vehicles (e.g., XR8000 sled-based, XR4000 stackable; exact models `verify`). Already implied by the Telecom sim (file 08) — this spec makes them a first-class product.
- **Personality:** the R760 engine with the environment sliders unlocked to hostile ranges: −5…55 °C class ambient (`verify`), dust/filter fouling accumulation over sim-months (feeds M1's resistance curve), vibration exposure (feeds M5 if HDDs foolishly configured — teachable: rugged sites want SSDs), single-phase weird power (feeds M11: brownout ride-through matters more at a cell site than in a data hall).
- **Scenarios:** "Rooftop in Phoenix, February in Fargo" (one config, two climate profiles via M9); "The filter nobody changed" (six sim-months of fouling, then a heat wave).

## 3. PowerVault ME5 — entry block storage (Archetype B)
- **What it is:** Dell's entry SAN array (dual-controller, SAS/iSCSI/FC).
- **Why include it:** the perfect *first* storage sim — the shared storage engine (file 02) with everything simple: two controllers, classic RAID levels (1/5/6/10 with their distinct write penalties: R5 write = 4 I/O ops, R6 = 6 — explain-mode gold), no dedupe by default. Its simplicity makes PowerStore's added machinery legible by contrast.
- **Modules:** M5 (it's the natural home of HDD tiers), M6 for SSD tiers.
- **Scenarios:** "RAID write penalty" (same drives, R10 vs R6, watch write IOPS); "Rebuild a 20 TB drive" (days — why R6 replaced R5 as drives grew; connect to the rebuild-window risk gauge).

## 4. PowerProtect Data Domain (DD appliance) — dedupe deep dive (Archetype B)
- **What it is:** Dell's purpose-built backup appliance family (DD series) behind much of PowerProtect; its soul is variable-length deduplication.
- **Why a separate sim from file 05:** dedupe deserves its own physics-grade treatment. Model: incoming backup streams → chunking → fingerprint lookup → only novel chunks stored. Dedupe ratio emerges from data properties: daily change rate, retention length (more generations = better ratio), and **entropy** — encrypted or compressed data doesn't dedupe (ratio → 1:1). That entropy fact is the bridge to Cyber Detect (file 05): ransomware-encrypted data is high-entropy, which is partly how corruption detection works — the two sims share one concept from opposite sides.
- **Instruments:** logical vs physical capacity, emergent dedupe ratio, ingest throughput vs fingerprint-index pressure.
- **Scenarios:** "Why 30 backups fit in 2×" (generational dedupe emerges live); "The encrypted-source mistake" (host-side encryption before backup: ratio collapses, capacity planning explodes); "Entropy as a smoke alarm" (cross-link to Cyber Detect).

## 5. PowerCool CDU C7000, PowerRack & Integrated Rack Controller — the facility layer (Archetype A at rack/row scale)
- **What they are (per Dell 2026 announcements):** PowerCool CDU C7000 — Dell's coolant distribution unit (Q3 2026); PowerRack — factory-integrated rack-scale systems (compute/storage/networking engineered as one, with rack-level thermal and power management); Dell Integrated Rack Controller (IRC) — unified rack-level power/cooling management. All details `verify` — these are new products; check Dell's current documentation at build time.
- **Sim design:** the CDU is the star: primary (facility) loop ↔ heat exchanger ↔ secondary (rack) loop, with M10's hydraulics and M9's dew-point constraint as its core physics; pump redundancy, flow/temperature setpoints, capacity in kW of heat moved. PowerRack/IRC become the "container + control plane" wrapping XE9712-class trays (extend file 01's IR7000 app rather than a new one): IRC as a simulated management console (like iDRAC, file 01, but rack-scope) exposing setpoints, per-tray power caps, and coordinated responses (facility-water warm event → IRC sheds load gracefully vs uncoordinated tray-level panic).
- **Scenarios:** "Size the CDU" (add trays until heat-exchange capacity binds); "Warm water day" (facility supply +6 °C: watch setpoint chain react); "One pump down."

## 6. Rack PDUs & UPS (Dell power accessories) — Archetype A/F
- **What they are:** Dell-branded metered/switched rack PDUs and rack UPS units (`verify` current lineup).
- **Sim design:** the natural home of M11 (three-phase balancing, per-outlet metering, breaker limits) and M4-adjacent battery aging: UPS runtime = battery Wh ÷ load W (with inverter efficiency ~0.93, estimate), batteries fade with age/temperature (VRLA vs lithium toggle), periodic self-test events. Feeds every rack-scale sim as an optional layer.
- **Scenarios:** "Balance the phases" (drag servers between A/B/C feeds); "The 4-year-old batteries" (runtime you think you have vs runtime you have — the classic outage post-mortem, simulated); "Breaker math" (80% continuous-load rule as a validation rule).

## 7. UltraSharp / displays — optional client add-on (Archetype A-lite + F)
- Small module, not a full sim: panel power = f(brightness, size, mini-LED zones vs edge-lit), color/brightness specs as config, power + M12 acoustics = silence, lifecycle carbon via file 08's Circular Design engine (a monitor's embodied vs use-phase split differs instructively from a laptop's). Include only if the user wants completeness.

## 8. Client-brand map (documentation note, not a sim)
Dell's 2025 client rebrand: **Dell** (consumer, absorbing XPS/Inspiron), **Dell Pro** (business, née Latitude/OptiPlex), **Dell Pro Max** (workstation, née Precision) with Base/Plus/Premium tiers — which is where file 07's "Pro Max Plus" sits. Alienware remains its own brand. Add this map as a static explainer page in the file 07 app so the naming is teachable; `verify` current tiering.

## 9. Dell AI Factory — the capstone meta-scenario (not a new engine)
- **What it is:** Dell's umbrella for end-to-end AI infrastructure — AI-optimized compute (XE-series), storage/data (AI Data Platform), networking (SN6000/Quantum), facility (PowerRack/CDU), services — with thousands of enterprise customers per Dell's 2026 materials.
- **Sim design:** a **grand scenario mode** spanning the whole suite rather than new physics: "Stand up an AI factory" — the user sizes a training cluster (file 01), its fabric (03), its data platform (02/06), its facility power/cooling (this file + 09's M9–M11), its resilience (05), its operations (04), and watches one integrated dashboard: tokens/s, MW, PUE, GPU-idle-due-to-data %, $/token proxy, and time-to-first-token-of-training. Every earlier lesson becomes a line item. This only works if the shared-library architecture (file 00) was honored — treat it as the suite's final exam, for both the user and the coding agent.
