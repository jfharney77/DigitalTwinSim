# Course design: the twins as one tutorial

Status: **built** (2026-09-18) as `Learn/`. This document was the brief; §9
at the end records where the build differs from it. Serve it with
`./Learn/scripts/serve.sh` and open `http://localhost:5172/Learn/`.

The repo holds forty-odd twins, and each one teaches one idea. A reader who opens
them in port order gets a stack of unrelated lessons. This design puts them in a
teaching order, gives each module a question to answer before pressing play, and
checks every deep link against the code, so the course breaks loudly when a twin
changes under it.

Every factual claim in a question or answer below cites the file that settles it.
The trace numbers were read from each engine's `simulate()` output on 2026-09-18,
and the physics claims come from the named pytest cases. If an engine changes, the
test that pins the claim changes with it; see "Keeping answers honest" at the end.

---

## 1. What exists today, and what the course needs first

> Superseded on the build date: tours and `#scenario=` both landed in every
> twin, so the course links them directly. See §9.

| Deep-link kind | Form | Supported today? | Pinned against |
|---|---|---|---|
| Narrative phase | `http://localhost:<fe>/#phase=<name>` | Yes, in all 21 narrative twins' `App.tsx` | the phase string in `<Twin>/backend/app/engine.py` |
| Narrative step | `http://localhost:<fe>/#step=<N>` | Yes (same parser, e.g. `DellPowerStore/frontend/src/App.tsx:32-40`) | step count from the engine, plus a declared `expectPhase` |
| Tour step | `http://localhost:<fe>/#tour/<stepId>` | **No.** Only `GPU/backend/app/tour.py` exists, and it serves the CUDA lesson tour. ACTIVE_TWIN_SPEC.md §8 names the signature ids; the rollout (§10) has not reached the narrative twins. | the id string in `<Twin>/backend/app/tour.py` |
| GPU lesson tour | `http://localhost:5173/#live/tour` | Yes (`GPU/frontend/src/components/LivePage.tsx:98-147`); it opens at the first lesson, not at a named step | `GPU/backend/app/tour.py` ids (for a future `#live/tour/<id>`) |
| Physics guided scenario | `http://localhost:<fe>/#scenario=<id>` | **No.** No physics `App.tsx` reads a hash; the scenario is picked from the Guided list (`DellPowerEdgeR760Thermal/frontend/src/App.tsx:159`) | the `GuidedScenario(id=...)` string in `<App>/backend/app/presets.py` |

Two small pieces of work outside `Learn/` come before the course is at its best.
Neither blocks the first build:

1. **`#scenario=<id>` in every physics app.** On the first successful
   `GET /api/scenarios`, if `location.hash` matches `#scenario=([a-z0-9-]+)`,
   call the handler the Guided list already calls. That is about 10 lines per
   app, across the 17 physics apps and R760Thermal. Until it lands, the course
   links to the app root and tells the reader which scenario to pick by title.
   The link test pins the id either way.
2. **`#tour/<stepId>` in the narrative twins**, delivered by the tour rollout
   in ACTIVE_TWIN_SPEC.md §10. Until it lands, each module uses its
   `#phase=`/`#step=` fallback. The course data carries both (see §5.3).

---

## 2. The teaching spine

The course climbs one layer at a time: the arithmetic inside one chip, then one
box, the heat that box makes, the rack, the liquid, the data, the network between
racks, keeping the data safe, running a fleet, the device at the edge, and last
the factory that couples all of them. Each module ends with a sentence that takes
the reader into the next one, and every one of those sentences reuses a
cross-reference the twins already make.

| # | Module | Twins (frontend port) | The one idea |
|---|---|---|---|
| M1 | The roofline | GPU (5173) | Whether a kernel is limited by compute or by memory is a ratio, not a property of the chip |
| M2 | A server wakes up | DellPowerEdgeR760 (5174), DellIDRAC (5177) | A plugged-in server is never off, and its slowest boot stage is teaching the memory to talk |
| M3 | Heat in one box | DellPowerEdgeR760Thermal (5203) | Fans are part of the load they cool, and fan power goes as speed cubed |
| M4 | Eight GPUs, then seventy-two | DellPowerEdgeXE9680 (5201), DellPowerEdgeXE9712 (5181), PhysicsCompute (5205) | The NVLink domain fuses atomically, and where its wall sits is the design decision |
| M5 | Liquid: heat in equals heat out | DellIR7000 (5182), PhysicsCDU (5216) | A cooling loop is a device for making three numbers equal, and coordination decides what gives |
| M6 | Storage arithmetic and the mirrored ack | PhysicsME5 (5214), DellPowerStore (5175) | Every write costs more than one write, and an acknowledged write already lives in two places |
| M7 | Deleting the controller | DellPowerFlex (5189), DellPowerScale (5196), DellExascale (5184), PhysicsStorage (5206) | Scale-out storage removes one thing (the controller, the volume, or the metadata hop), and the whole design follows from it |
| M8 | The fabric: lossless two ways | DellPowerSwitchSN6000 (5185), DellQuantumX800 (5202), PhysicsFabric (5207) | Ethernet proves losslessness under stress; InfiniBand makes loss impossible to express |
| M9 | Survive, verify, contain | DellPowerProtect (5183), DellCyberDetect (5192), DellFortZero (5195), PhysicsResilience (5209) | Three separate questions: does a copy survive, is it clean, and who can reach it |
| M10 | Running the estate | DellCloudIQ (5180), DellVxRail (5179), DellPrivateCloud (5198), DellNativeEdge (5187), PhysicsFleet (5208) | Operations is where the architecture choices send their bills |
| M11 | Inference at the edge | DellProMaxPlus (5186), PhysicsClient (5204) | Decode is memory-bound, so the winning move is to never move the weights again |
| M12 | Capstone: stand up an AI factory | PhysicsAIFactory (5219), CustomerSetup xAI-Colossus and TACC-Horizon (5170) | GPUs sit idle because data did not arrive, and that coupling decides the whole factory |

Ports come from `ports.json`; the physics apps' ports come from their `vite.config.ts`
and `ports.json`. PowerMax and PowerSwitch E3200 share 5178 and are deliberately
left out of the core spine. PowerMax appears as an optional extension in M6.

---

## 3. The modules

Each module uses the same template:

- **Twins** and **prerequisites** (ideas, not modules; a track can skip a module
  whose ideas the reader already has).
- **Objectives**: what the reader can do afterwards.
- **Entry**: the tour target (future), the phase/step fallback (works today), and
  any physics scenario.
- **Predict before you play**: one question asked before the trace runs. The
  reader commits to an answer, then plays to the step that settles it.
- **Check your understanding**: 2–3 questions with answers.
- **Bridge**: the sentence that leads into the next module.

### M1 The roofline

- **Twins:** GPU.
- **Prerequisites:** a matrix multiply is N³ multiply-adds; data has to be
  loaded before anything can use it.
- **Objectives:** define arithmetic intensity (MACs per byte moved) and the ridge
  point; predict the regime from them; explain why the playback clock lives in
  the browser and not in the engine.
- **Entry:** sim page `http://localhost:5173/` (set N and the tile size, then
  switch dtype). Lesson tour: `http://localhost:5173/#live/tour`, whose step
  `the-roof` (`GPU/backend/app/tour.py:394`) replays CUDA lesson 06. A future
  `#live/tour/the-roof` is pinned against that id.
- **Predict before you play:** "Keep the matmul and the tile size the same and
  change only the data type, from fp32 to int8. Does the kernel stay memory-bound?"
  - *Answer:* No. At fp32 it is memory-bound; at int8 the same workload becomes
    compute-bound, because fewer bytes carry the same MACs, so intensity rises
    past the ridge.
  - *Evidence:* `GPU/backend/app/engine.py` `analyze()`:
    `regime = "memory" if intensity < ridge else "compute"`;
    `GPU/backend/tests/test_bandwidth.py::test_regime_flips_with_dtype`
    (4×4 with tile 2: fp32 → `memory`, int8 → `compute`).
- **Check your understanding:**
  1. *Shrinking the tile makes intensity go which way, and why?* Down. Less reuse
     per tile means more bytes moved for the same MACs.
     (`GPU/backend/tests/test_bandwidth.py::test_smaller_tiles_lower_intensity_toward_memory_bound`)
  2. *In a memory-bound run, which is larger: total load cycles or total compute
     cycles?* Load cycles.
     (`GPU/backend/tests/test_bandwidth.py::test_regime_consistent_with_cycle_totals`)
  3. *Where does the `setInterval` that animates the die live?* In
     `GPU/frontend/src/App.tsx`. The engine emits a finished `SimState[]` and holds
     no timers. (CLAUDE.md "Non-negotiable invariants"; engine purity is
     AST-checked by `twinkit.testing.assert_engine_is_pure` in the component suites.)
- **Bridge:** "A GPU is a chip. Before it computes anything, the box around it has
  to power on, and in a server that box has its own computer that never sleeps.
  M2 turns on an R760."

### M2 A server wakes up

- **Twins:** DellPowerEdgeR760, DellIDRAC.
- **Prerequisites:** M1 is not required. You need to know that a server has
  CPUs, DIMMs, drives and fans.
- **Objectives:** put the power-on phases in order (`off→standby→bmc→poweron→post→boot→os`);
  explain why the BMC boots before the host; name the longest stage and say why
  it cannot be hard-coded.
- **Entry:**
  - Tour (future): `http://localhost:5174/#tour/memory-training` (ACTIVE_TWIN_SPEC.md §8).
  - Fallback: `http://localhost:5174/#step=8` (expectPhase `post`, "DDR5 memory training").
  - Companion: `http://localhost:5177/#tour/always-on`, with fallback `http://localhost:5177/#step=8`
    (expectPhase `services`, Lifecycle Controller init).
- **Predict before you play:** "Which stage of the R760 power-on is the longest:
  the iDRAC boot, DDR5 memory training, or the OS load?"
  - *Answer:* DDR5 memory training, inside POST.
  - *Evidence:* step 8 carries `cycle_cost=6`, the unique maximum in the trace
    (`DellPowerEdgeR760/backend/app/engine.py`);
    `DellPowerEdgeR760/backend/tests/test_engine.py::test_memory_training_is_the_longest_stage`.
- **Check your understanding:**
  1. *Does iDRAC come up before or after someone presses the power button?* Before:
     `bmc` is steps 2–3 and `poweron` starts at step 4. Step 3 takes a hardware
     inventory while the host is still off.
     (`DellPowerEdgeR760/backend/app/engine.py`)
  2. *Why do all six fans go to 100% at step 5 and then drop?* Until firmware has
     read the thermal sensors, maximum airflow is the safe assumption. After that,
     iDRAC thermal control settles the fans (60% at step 6, 25% at `os`).
     (`DellPowerEdgeR760/backend/app/engine.py` step 5 description and `fan_percent`)
  3. *In the iDRAC twin, what is the most power the BMC domain ever draws?*
     8 W. The test caps it at 20 W because the host never powers on.
     (`DellIDRAC/backend/tests/test_engine.py::test_host_never_powers_on`; trace
     `power_watts` peaks at 8)
- **Bridge:** "The R760 reached `os` idling near 250 W with fans at 25%. Now leave
  it running and raise the room temperature. M3 is the same machine in the
  physics simulator."

### M3 Heat in one box

- **Twins:** DellPowerEdgeR760Thermal.
- **Prerequisites:** M2's fan behaviour; power in watts becomes heat.
- **Objectives:** state the per-tick power balance (component watts sum to DC,
  and AC = DC ÷ efficiency); explain the fan-power feedback loop; predict what
  losing a fan costs.
- **Entry:** `http://localhost:5203/#scenario=fan-feedback`, then
  `#scenario=kill-a-fan`. Until `#scenario=` exists, link the app root and say
  "choose *The fan-power feedback loop*". Both ids are in
  `DellPowerEdgeR760Thermal/backend/app/presets.py`.
- **Predict before you play:** "The workload never changes. At 3 minutes the inlet
  air rises to 40 °C. Does the server's power draw go up, stay flat, or go down?"
  - *Answer:* It goes up. The fans spin faster to hold the silicon at temperature,
    and fan watts are part of the DC sum.
  - *Evidence:* scenario `fan-feedback` is `BALANCED` + `DATABASE` with
    `SimEvent(at_s=180, action="set-inlet", value=40)`
    (`DellPowerEdgeR760Thermal/backend/app/presets.py`); fan power is
    `alive_fans * fan_pmax * (rpm/100)**3` (`DellPowerEdgeR760Thermal/backend/app/engine.py:214`);
    `DellPowerEdgeR760Thermal/backend/tests/test_engine.py::test_power_balance_every_tick`
    includes `fan_power_w` in the sum.
- **Check your understanding:**
  1. *Kill two of six fans under HPC load on the Balanced build. Does it throttle?*
     No. The four survivors spin faster and the CPUs do not throttle.
     (`test_engine.py::test_fan_failure_survivors_ramp`)
  2. *Why can five fans at a higher speed use more power than six at a lower
     speed?* Because power scales with the cube of speed, while airflow scales
     only linearly. (`engine.py:214`; `kill-a-fan` narration in `presets.py`)
  3. *At steady state, what sets the air's temperature rise through the box?*
     ΔT = DC / (ṁ·cp). (`test_engine.py::test_heat_balance_at_steady_state`)
- **Bridge:** "One R760 moves its heat with air. An eight-GPU server draws around
  11 kW, and at that density air runs out of room. M4 scales the box up."

### M4 Eight GPUs, then seventy-two

- **Twins:** DellPowerEdgeXE9680, DellPowerEdgeXE9712; PhysicsCompute for the
  physics version.
- **Prerequisites:** M2 (a server boots its host first); M3 (fans are load).
- **Objectives:** explain why the NVLink domain appears all at once; locate the
  domain wall (the chassis for XE9680, the rack for XE9712); explain "liquid
  before silicon".
- **Entry:**
  - XE9680: `http://localhost:5201/#phase=fuse`, then `#phase=fabric`. There is no
    §8 storyboard; the proposed tour id is `chassis-wall` (§6).
  - XE9712: tour `http://localhost:5181/#tour/atomic-fuse`; fallbacks
    `http://localhost:5181/#phase=coolant` and `#phase=fused`.
  - PhysicsCompute: `http://localhost:5205/#scenario=starved` (used again in M12).
- **Predict before you play:** "An XE9712 rack brings up 72 GPUs across its trays.
  As they train their links, does `gpusInDomain` climb gradually (8, 16, 32…) or
  jump?"
  - *Answer:* It jumps from 0 to 72 in one step, at `fused`, and never takes an
    intermediate value.
  - *Evidence:* trace `gpus_in_domain` is 0 through `fabric` (step 5) and 72 from
    `fused` (step 6) on (`DellPowerEdgeXE9712/backend/app/engine.py`);
    `DellPowerEdgeXE9712/backend/tests/test_engine.py::test_fuse_joins_all_72_gpus_at_once`.
- **Check your understanding:**
  1. *In the XE9680, which comes first: the eight NICs joining the fabric, or the
     NVLink fuse?* The fuse. `gpus_in_domain` reaches 8 at step 4 (`fuse`) while
     `nics_up` is still 0, and `nics_up` reaches 8 at step 5 (`fabric`). The
     domain never grows past 8.
     (`DellPowerEdgeXE9680/backend/tests/test_engine.py::test_the_fuse_is_atomic_and_the_domain_stops_at_eight`,
     `::test_one_nic_per_gpu_joins_the_fabric_after_the_fuse`)
  2. *What does the XE9712 do before any tray boots?* It starts coolant flow:
     `coolant` is step 2 and `trayboot` is step 3.
     (`DellPowerEdgeXE9712/backend/tests/test_engine.py::test_coolant_flows_before_any_silicon`)
  3. *Which stage is longest in each twin, and why do they differ?* XE9680:
     `gpuinit` (cost 5, HBM training ×8). XE9712: `fabric` (cost 5, NVLink training
     over the copper spine). The XE9680's fuse runs over board traces and needs no
     cable training. (`…XE9680/backend/tests/test_engine.py::test_gpu_init_is_the_longest_stage`;
     `…XE9712/backend/tests/test_engine.py::test_fabric_training_is_the_longest_stage`)
- **Bridge:** "The XE9712 pauses at `coolant` until the loop proves itself. The
  IR7000's `verify` phase is what it is waiting for. M5 is that loop."

### M5 Liquid: heat in equals heat out

- **Twins:** DellIR7000; PhysicsCDU.
- **Prerequisites:** M3 (the heat identity in air); M4 (liquid before silicon).
- **Objectives:** state the heat balance (liquid + air = IT load, exactly); explain
  "flow before heat"; compare what a rack controller does on a warm-water day
  with what happens without one.
- **Entry:**
  - IR7000: tour `http://localhost:5182/#tour/heat-balance`; fallback
    `http://localhost:5182/#phase=verify`, then `#phase=steady`.
  - PhysicsCDU: `http://localhost:5216/#scenario=warm-water-day`, then
    `#scenario=warm-water-panic` (`PhysicsCDU/backend/app/presets.py`).
- **Predict before you play:** "Building water arrives 6 °C warmer. In one run the
  rack controller coordinates; in the other, each bank of trays protects only
  itself. Which run keeps more banks online?"
  - *Answer:* The coordinated run keeps all six banks online with zero trips; it
    caps every bank a little. The uncoordinated run trips at least two banks,
    shedding more compute than the physics required, because the loop's lag
    keeps the survivors hot after the first trip.
  - *Evidence:* `PhysicsCDU/backend/tests/test_engine.py::test_acceptance_warm_water_day_coordinated_sheds_gracefully`
    (`trips == 0`, `groups_online == 6` throughout) and
    `::test_acceptance_warm_water_day_uncoordinated_cascades` (`trips >= 2`); both
    use `set-facility-supply` to 23 °C at 120 s.
- **Check your understanding:**
  1. *At IR7000 steady state, what share of the 264 kW leaves through the liquid?*
     240 kW of 264 kW, about 91%. The rest (24 kW) goes to air, and the two sum
     exactly on every step. (`DellIR7000/backend/app/engine.py` step 7;
     `tests/test_engine.py::test_heat_balance_holds_on_every_step`,
     `::test_liquid_carries_the_overwhelming_share`)
  2. *Why is `flow_lpm` 300 while IT load is still 0?* Flow must exist before the
     first watt of heat. (`::test_flow_before_heat`; steps 2–4)
  3. *Which IR7000 stage is longest?* `verify` (cost 5), the per-branch leak and
     flow check. (`::test_verification_is_the_longest_stage`)
- **Bridge:** "The rack is powered, fused and cooled, and now it wants data. M6
  starts with the arithmetic every storage system pays."

### M6 Storage arithmetic and the mirrored ack

- **Twins:** PhysicsME5, DellPowerStore (optional extension: DellPowerMax on 5178,
  run on its own).
- **Prerequisites:** none beyond "a drive can fail".
- **Objectives:** compute the RAID write penalty; explain why the write
  acknowledgement comes from NVRAM, not from the drives; explain the dual-node
  lockstep.
- **Entry:**
  - PhysicsME5: `http://localhost:5214/#scenario=write-penalty`, then
    `#scenario=second-failure` (`PhysicsME5/backend/app/presets.py`).
  - PowerStore: tour `http://localhost:5175/#tour/mirrored-ack`; fallback
    `http://localhost:5175/#step=7` (expectPhase `drives`, "NVRAM write cache
    initializes").
  - PowerMax extension: `http://localhost:5178/#phase=vault` (tour id
    `vault-to-flash`).
- **Predict before you play:** "Same drives, a saturating pure-write load. RAID 10
  against RAID 6: how far apart are the served write IOPS?"
  - *Answer:* Exactly 3×. The penalties are 2 and 6 backend I/Os per write.
  - *Evidence:* `PhysicsME5/backend/tests/test_engine.py::test_write_penalty_ratio_r10_vs_r6`
    (`abs(w10/w6 - 3.0) < 0.05`); the penalty table is pinned in
    `PhysicsME5/backend/tests/test_model_data.py`.
- **Check your understanding:**
  1. *A second drive fails mid-rebuild. Which survives, RAID 5 or RAID 6?* RAID 6.
     (`PhysicsME5/backend/tests/test_engine.py::test_second_failure_mid_rebuild_r6_survives_r5_does_not`)
  2. *During PowerStore's `power` and `boot` phases, can node A light a region
     without node B lighting its twin?* No. Every lit `-a` region lights its `-b`
     twin. (`DellPowerStore/backend/tests/test_engine.py::test_dual_node_bring_up_is_symmetric`)
  3. *Which PowerStore stage is longest?* The PowerStoreOS container boot, step 5
     (cost 4). (`::test_powerstoreos_boot_is_the_longest_stage`)
- **Bridge:** "PowerStore puts two controllers in front of the drives, and every
  byte passes through one of them. M7 is about what happens when you delete that
  controller."

### M7 Deleting the controller

- **Twins:** DellPowerFlex, DellPowerScale, DellExascale; PhysicsStorage.
- **Prerequisites:** M6 (controllers, rebuilds).
- **Objectives:** explain why rebuilds get faster as a scale-out pool grows; say
  what "no volumes" means for growth; explain why the metadata server leaves the
  data path.
- **Entry:**
  - PowerFlex: tour `http://localhost:5189/#tour/no-controller`; fallback
    `http://localhost:5189/#phase=rebuild`.
  - PowerScale: tour `http://localhost:5196/#tour/onefs-stripe`; fallback
    `http://localhost:5196/#phase=addnode`.
  - Exascale: tour `http://localhost:5184/#tour/metadata-leaves`; fallback
    `http://localhost:5184/#phase=layout`, then `#phase=feed`.
  - PhysicsStorage: `http://localhost:5206/#scenario=scale-out-rebuild`
    (`PhysicsStorage/backend/app/presets.py`).
- **Predict before you play:** "One of six PowerFlex nodes dies. How many nodes do
  the rebuild work: one, two, or all five survivors?"
  - *Answer:* All five survivors.
  - *Evidence:* at step 6 (`rebuild`), `rebuild_participants == nodes_online == 5`
    (`DellPowerFlex/backend/app/engine.py`);
    `DellPowerFlex/backend/tests/test_engine.py::test_every_surviving_node_rebuilds`.
- **Check your understanding:**
  1. *Does PowerFlex I/O stop during the failure?* No. IOPS go 1,800k → 1,620k →
     1,500k (rebuild) → 1,800k, and never drop below 70% of steady.
     (`::test_service_survives_the_failure`; trace steps 4–8)
  2. *PowerScale grows from 4 to 6 nodes at `addnode`. What happens to
     `migrationsRequired` and `usedPercent`?* Migrations stay at 0. Capacity goes
     from 400 to 600 TB, and used falls from 81% to 54% without moving or
     deleting anything. (`DellPowerScale/backend/app/engine.py` steps 4–5;
     `tests/test_engine.py::test_growing_the_cluster_requires_no_migration`,
     `::test_capacity_grows_with_nodes_not_with_planning`)
  3. *In which Exascale phases is the metadata server active?* Exactly `mount` and
     `layout`. It is absent from every bulk phase, while throughput peaks at
     48,000 Gbps with all four data servers streaming.
     (`DellExascale/backend/tests/test_engine.py::test_metadata_leaves_the_data_path`,
     `::test_peak_throughput_reaches_rack_scale`)
  4. *(physics) Does a 20-node cluster rebuild faster than a 5-node cluster and
     than PowerStore?* Faster than both.
     (`PhysicsStorage/backend/tests/test_engine.py::test_rebuild_faster_with_more_nodes_and_the_inversion`)
- **Bridge:** "Exascale's fan-out reads converge on one reader at once: the incast
  the SN6000's congestion control has to absorb. M8 is that network."

### M8 The fabric: lossless two ways

- **Twins:** DellPowerSwitchSN6000, DellQuantumX800; PhysicsFabric.
- **Prerequisites:** M4 (NVLink stops at the chassis or rack wall; scale-out
  traffic is the fabric's job); M7 (incast).
- **Objectives:** contrast reactive losslessness (ECN/PFC plus adaptive routing)
  with credit-based flow control; explain SHARP's crossing counters; recognise a
  gray failure.
- **Entry:**
  - SN6000: tour `http://localhost:5185/#tour/zero-drops-under-stress`; fallback
    `http://localhost:5185/#phase=congestion`.
  - Quantum-X800: `http://localhost:5202/#phase=sharp`, then `#phase=burst`. There
    is no §8 storyboard; the proposed tour id is `credit-before-send` (§6).
  - PhysicsFabric: `http://localhost:5207/#scenario=gray-failure`
    (`PhysicsFabric/backend/app/presets.py`).
- **Predict before you play:** "The SN6000's hottest link reaches 98%. How many
  packets does the fabric drop?"
  - *Answer:* Zero, on every step. Adaptive routing then cools the hot link to 71%
    while total fabric throughput rises from 24 to 31 Tb/s.
  - *Evidence:* trace steps 6–7 (`DellPowerSwitchSN6000/backend/app/engine.py`);
    `tests/test_engine.py::test_fabric_never_drops_a_packet`,
    `::test_congestion_actually_happens_and_is_survived`,
    `::test_adaptive_routing_relieves_without_losing_work`.
- **Check your understanding:**
  1. *When SHARP turns on in the Quantum-X800 twin, what happens to `fabricTbps`
     and `allreduceGbps`?* Fabric traffic falls (36 → 22 Tb/s) while the effective
     all-reduce rate rises (1,600 → 2,900 Gb/s). The math moved into the switches.
     (`DellQuantumX800/backend/tests/test_engine.py::test_sharp_moves_the_math_into_the_fabric`)
  2. *What does the incast burst cost InfiniBand, if not drops?* Stalls: 1,800 µs/s,
     on the `burst` step only. `packetsSentWithoutCredit` stays 0 everywhere.
     (`::test_the_burst_stalls_senders_instead_of_losing_work`,
     `::test_stalls_happen_only_under_the_burst`,
     `::test_no_packet_is_ever_sent_without_a_credit`)
  3. *(physics) After a gray failure, what does the status panel show?* All green,
     with zero dropped packets counted, while delivered throughput falls and flow
     completion time rises more than 1.5×.
     (`PhysicsFabric/backend/tests/test_engine.py::test_gray_failure_green_and_wrong`)
- **Bridge:** "Gray failure is damage the dashboard does not show. Ransomware is
  the same shape: M9 starts from the question the gray link raises, which is what
  you can still trust."

### M9 Survive, verify, contain

- **Twins:** DellPowerProtect, DellCyberDetect, DellFortZero; PhysicsResilience
  (PhysicsDataDomain optional).
- **Prerequisites:** M6 (snapshots, dedupe vocabulary helps).
- **Objectives:** tell apart three questions that are often confused: does a copy
  survive (isolation), is the copy clean (integrity), and who can reach the data
  (access). Explain why recovery time is set by the decision plus the bandwidth.
- **Entry:**
  - PowerProtect: tour `http://localhost:5183/#tour/airgap-discipline`; fallback
    `http://localhost:5183/#phase=attack`.
  - Cyber Detect: tour `http://localhost:5192/#tour/blind-then-read`; fallback
    `http://localhost:5192/#phase=blind`, then `#phase=verdict`.
  - Fort Zero: tour `http://localhost:5195/#tour/breach-reaches-nothing`; fallback
    `http://localhost:5195/#phase=breach`.
  - PhysicsResilience: `http://localhost:5209/#scenario=backups-arent-enough`
    (`PhysicsResilience/backend/app/presets.py`).
  - Optional: `http://localhost:5215/#scenario=entropy-alarm` (PhysicsDataDomain).
- **Predict before you play:** "Ransomware encrypts snapshots over several days.
  How many alerts does metadata-based detection raise before byte-level inspection
  runs?"
  - *Answer:* Zero. At `blind`, 4 of 7 snapshots are corrupted and
    `metadataAlerts` is still 0. Confidence stays at 0 until inspection has run,
    then jumps to 99%, and the verdict names snapshot 3 as the last clean copy.
  - *Evidence:* trace steps 3–6 (`DellCyberDetect/backend/app/engine.py`);
    `tests/test_engine.py::test_metadata_detection_is_blind_while_corruption_spreads`,
    `::test_confidence_comes_only_from_reading_content`,
    `::test_the_named_copy_is_actually_clean` (the named snapshot is older than
    `CLEAN_SNAPSHOTS + 1`).
- **Check your understanding:**
  1. *In PowerProtect, in which phases is the air gap open?* Only `replicate` and
     `recover`. During `attack`, no vault region and no gap region is active.
     (`DellPowerProtect/backend/tests/test_engine.py::test_air_gap_discipline`,
     `::test_attack_cannot_reach_the_vault`)
  2. *What dedupe ratio does PowerProtect's trace reach?* 20:1 (500 TB logical,
     25 TB stored). The test requires at least 10:1.
     (`DellPowerProtect/backend/app/engine.py` step 2; `::test_dedupe_economics`)
  3. *In Fort Zero, the attacker holds an inside position at `breach`. How many
     resources can it reach?* 0. `implicitTrustGrants` is 0 on every step, and even
     a legitimate grant reaches at most 1 resource, on a 300 s lease.
     (`DellFortZero/backend/tests/test_engine.py::test_the_breach_reaches_nothing`,
     `::test_the_breach_is_actually_inside`, `::test_least_privilege_is_literal`)
  4. *(physics) Why does a 200 TB restore at 1 GB/s take days even with a clean
     copy?* RTO = decision time + TB ÷ bandwidth. The test pins it above 48 hours.
     (`PhysicsResilience/backend/tests/test_engine.py::test_rto_is_decision_plus_bandwidth`)
- **Bridge:** "Every one of these depended on someone watching. M10 is the
  watching, and the rest of the operations bill."

### M10 Running the estate

- **Twins:** DellCloudIQ, DellVxRail, DellPrivateCloud, DellNativeEdge; PhysicsFleet.
- **Prerequisites:** M2 (iDRAC out-of-band); M7 (clusters).
- **Objectives:** follow telemetry to an insight; contrast hyperconverged coupling
  (VxRail) with disaggregated pools (Private Cloud); explain zero-touch as
  attestation first; price manual against automated operations.
- **Entry:**
  - CloudIQ: tour `http://localhost:5180/#tour/analyze-dip`; fallback
    `http://localhost:5180/#phase=analyze`, then `#phase=detect`.
  - VxRail: tour `http://localhost:5179/#tour/primary-election`; fallback
    `http://localhost:5179/#phase=primary`.
  - Private Cloud: `http://localhost:5198/#phase=growstorage`. There is no §8
    storyboard; the proposed tour id is `hypervisor-slot` (§6).
  - NativeEdge: tour `http://localhost:5187/#tour/zero-touch`; fallback
    `http://localhost:5187/#phase=attest`.
  - PhysicsFleet: `http://localhost:5208/#scenario=three-node-trap`
    (`PhysicsFleet/backend/app/presets.py`).
- **Predict before you play:** "Private Cloud doubles its storage pool. What happens
  to its compute units?"
  - *Answer:* Nothing. Storage goes from 200 to 400 TB at `growstorage` and compute
    stays at 48. On VxRail, a new node would have brought processors whether or
    not you needed them.
  - *Evidence:* trace steps 5–6 (`DellPrivateCloud/backend/app/engine.py`);
    `tests/test_engine.py::test_compute_and_storage_scale_independently`,
    `::test_nothing_scales_that_was_not_asked_for`.
- **Check your understanding:**
  1. *How many VxRail nodes light during primary election?* Exactly one (`n1`),
     which breaks the lockstep. (`DellVxRail/backend/tests/test_engine.py::test_primary_election_lights_exactly_one_node`)
  2. *How many human actions does a NativeEdge site take?* One: power and a cable
     at `power`. Nothing comes online until attestation establishes trust, and
     attestation is the longest stage (cost 5).
     (`DellNativeEdge/backend/tests/test_engine.py::test_exactly_one_human_action`,
     `::test_nothing_runs_before_trust_is_established`,
     `::test_attestation_is_the_longest_stage`)
  3. *What does CloudIQ's health score do across the pipeline?* It starts at 100,
     dips to 71 at `detect`, and ends at 88 at `notify`: recovered, but not to 100.
     (`DellCloudIQ/backend/tests/test_engine.py::test_health_starts_perfect_dips_on_detection_then_recovers`)
  4. *(physics) Same fleet and faults, run manually versus automated: how many more
     admin hours does manual take?* More than 5×.
     (`PhysicsFleet/backend/tests/test_engine.py::test_automation_is_an_order_of_magnitude`)
- **Bridge:** "One endpoint in a NativeEdge estate is a Pro Max Plus workstation
  running a model with no network at all. M11 opens it and returns to the
  roofline from M1."

### M11 Inference at the edge

- **Twins:** DellProMaxPlus; PhysicsClient.
- **Prerequisites:** M1 (memory-bound regime).
- **Objectives:** explain why the weights cross PCIe once; connect decode to the
  memory-bound regime; separate token rate from tokens per joule.
- **Entry:**
  - Pro Max Plus: tour `http://localhost:5186/#tour/weights-cross-once`; fallback
    `http://localhost:5186/#phase=load`, then `#phase=offline`.
  - PhysicsClient: `http://localhost:5204/#scenario=three-engines`
    (`PhysicsClient/backend/app/presets.py`).
- **Predict before you play:** "During generation, how much traffic crosses the
  PCIe link between host and card?"
  - *Answer:* None. The link carries 52 Gb/s only during `load` (61 GB of weights)
    and 0 on every other step, including the whole of `decode`.
  - *Evidence:* trace (`DellProMaxPlus/backend/app/engine.py`);
    `tests/test_engine.py::test_weights_cross_the_link_exactly_once`,
    `::test_weights_are_monotonic_and_never_evicted`.
- **Check your understanding:**
  1. *What changes at the final `offline` step, when the network is unplugged?*
     Nothing. Tokens per second stay at 21.
     (`::test_disconnecting_the_network_changes_nothing`)
  2. *(physics) Ranked by token rate and by tokens per joule, where do CPU, GPU and
     NPU land?* Rate: GPU > NPU > CPU. Efficiency: NPU > GPU > CPU.
     (`PhysicsClient/backend/tests/test_engine.py::test_npu_wins_tokens_per_joule`)
  3. *Why is decode memory-bound?* Each generated token re-reads the weights and
     the KV cache for very few MACs, so intensity falls below the ridge. The GPU
     twin's `llm_decode` workload pins the fall and the regime flip.
     (`GPU/backend/tests/test_llm.py::test_intensity_pinned_fall_and_monotone_decrease`,
     `::test_regime_flips_across_the_ridge`)
- **Bridge:** "The Pro Max Plus wins by refusing to move data. An AI factory can't
  refuse: its data has to arrive, and when it doesn't, every other module's
  hardware waits. M12 couples them all."

### M12 Capstone: stand up an AI factory

- **Twins:** PhysicsAIFactory; PhysicsCompute; CustomerSetup `xAI-Colossus` and
  `TACC-Horizon` (served on 5170).
- **Prerequisites:** M4, M5, M7, M8, with M9 recommended.
- **Objectives:** reason from coupled subsystems to the six headline instruments;
  show that starvation, checkpoint cost and the power budget all emerge from the
  trace and are not set as parameters; map a real deployment onto the modules.
- **Entry:**
  - `http://localhost:5219/#scenario=stand-up`, `#scenario=starved-cluster`,
    `#scenario=checkpoint-goldilocks`, `#scenario=warm-day`
    (`PhysicsAIFactory/backend/app/presets.py`).
  - `http://localhost:5170/xAI-Colossus/setup.html` and
    `http://localhost:5170/TACC-Horizon/setup.html`. Each page's "What the twins
    would show you" section links the paused steps from M4, M5, M7 and M8.
- **Predict before you play:** "Storage delivers half the data the GPUs demand.
  What happens to tokens per second, and what happens to power?"
  - *Answer:* Tokens per second fall to about half, and GPU-idle-due-to-data rises
    to about 50%. Power does not fall with them: a starved GPU still draws most of
    its power, which is where the waste comes from.
  - *Evidence:* `PhysicsAIFactory/backend/tests/test_engine.py::test_starvation_emerges_from_the_arithmetic`
    (idle ≈ 50 ± 3%, token ratio 0.5 ± 0.05);
    `PhysicsCompute/backend/tests/test_engine.py::test_data_starvation_cuts_tokens_more_than_watts`
    (token ratio < 0.4 while power ratio > 0.6).
- **Check your understanding:**
  1. *Checkpoint every 5, 60 or 480 minutes: which yields the most tokens?* 60. Too
     often taxes every hour; too rarely loses more on each rollback.
     (`::test_checkpoint_goldilocks_interior_optimum`)
  2. *On the warm day, can facility power exceed the budget?* No. The engine sheds
     GPU clocks so facility power sits on the ceiling.
     (`::test_facility_never_exceeds_budget`, `::test_warm_day_sheds_load_and_logs_it`)
  3. *Where does the dice roll for GPU failures happen?* Nowhere. Failures arrive
     on MTBF arithmetic and roll the token counter back to the last checkpoint.
     (`::test_failures_arrive_on_the_mtbf_schedule_and_roll_back_tokens`; engine
     purity is AST-checked, and `random` is banned)
- **Bridge (course exit):** "Reopen the Colossus page with the modules behind you.
  Each block links to a twin you have now played. The page's note box separates
  what the sources state from what the drawing invents, and that habit is the
  last lesson."

---

## 4. Tracks

A track is an ordered subset of modules, with optional per-module trimming (for
example, "skip the physics entry"). Tracks share module progress: finishing M7 in
one track marks it done in all of them.

| Track | For | Modules | Est. time |
|---|---|---|---|
| `full` | Anyone, in order | M1–M12 | 6–8 h |
| `ai-infrastructure` | Architects building GPU clusters | M1 → M4 → M5 → M7 (Exascale only) → M8 → M12 | 3 h |
| `storage-admin` | Storage and backup admins | M6 → M7 → M9 → M10 (CloudIQ only) → M12 (starved-cluster only) | 3 h |
| `datacenter-facilities` | Facilities, power and cooling | M2 → M3 → M5 → M4 (XE9712 coolant only) → M12 (warm-day only) | 2 h |
| `security` | Security and resilience teams | M2 (iDRAC only) → M9 → M10 (NativeEdge only) → M8 (gray failure only) | 2 h |
| `operations` | Platform and ops teams | M2 → M10 → M7 (PowerScale only) → M9 (PowerProtect only) | 2 h |
| `executive-overview` | Decision makers | Predict-before-you-play only, no checks: M1, M4, M7, M9, M12 | 45 min |
| `what-goes-wrong` | Operators and anyone on call | Failure stops only: M2 (iDRAC) → M4 (XE9712) → M6 (PowerStore) → M8 (SN6000) → M9 (PowerProtect, Cyber Detect) → M10 (CloudIQ, VxRail, NativeEdge) → E6 (Alienware) | 90 min |

The executive track uses each module's predict question and the one-sentence
idea, and skips the check questions. That fits the reading-level mechanism
described in §5.4. RackPower, MX7000, XR, Display, Lifecycle, Data and DataDomain
are left out of the spine on purpose. §7 lists them as electives, so the core
stays at twelve modules.

---

## 5. Mechanics

### 5.1 Layout (static, no build step)

```
Learn/
  index.html          course home: spine table, track picker, progress summary
  module.html         one renderer; /Learn/module.html#m=M7&track=storage-admin
  track.html          track view; /Learn/track.html#t=ai-infrastructure
  course.js           the course as data: window.COURSE = { ... }  (pure JSON after the prefix)
  learn.js            renderer + progress store (plain ES5, like setup.js)
  learn.css           page-specific accents only; imports nothing
  README.md           how to add a module, how deep links are pinned
  scripts/serve.sh    python3 -m http.server 5172 --directory <repo root> --bind 127.0.0.1
  tests/test_links.py the link test (§5.5)
```

- Pages link `../CustomerSetup/shared/setup.css` and `../CustomerSetup/shared/setup.js`.
  `serve.sh` serves the **repo root**, so `/Learn/` and `/CustomerSetup/` resolve
  side by side. Opening the files directly with `file://` also works, because the
  paths are relative.
- **Liveness chips come free:** the renderer emits entry links as
  `<a href="…" data-twin-port="5189" data-twin-start="DellPowerFlex" data-twin-trace="cluster">`.
  `setup.js` wires them on `DOMContentLoaded` (`CustomerSetup/shared/setup.js:289`),
  so `learn.js` has to render **synchronously**: load `course.js` and `learn.js` as
  plain `<script>` tags in `<body>`, before `setup.js`. With that ordering, the
  shared file needs no changes.
- **Dell clean design:** no eyebrow text above headings, no "Step 3 of 12" numbering
  in the UI (module ids like M7 stay in the data and the URL, never as visible
  step counters; modules show their titles), no divider rules, no highlight
  backgrounds on text, no serif fonts. Sections are separated by spacing.
  "Predict before you play" is a heading, not a badge.

### 5.2 Page behaviour

A module page shows:

1. Title, one-sentence idea, prerequisites (as links to modules), objectives.
2. The **predict** block: the question and three or four options (radio buttons).
   The entry links stay disabled until the reader commits to an answer. This is
   deliberate friction: the point is to commit first. After committing, the entry
   links unlock and a "Reveal" button shows the answer, the evidence sentence and
   the file citation, rendered as a `code` path.
3. **Entry links**, each with a liveness chip. When a twin is down, the chip shows
   its start command, as it does on the CustomerSetup pages.
4. **Checks**: each question has a "Show answer" disclosure. The reader marks it
   "got it" or "missed it". Nothing is graded.
5. **Bridge**: the bridge sentence, then a Next link to the next module in the
   current track.

### 5.3 Course data (`course.js`)

```js
window.COURSE = {
  "version": 1,
  "modules": [{
    "id": "M7", "title": "Deleting the controller", "idea": "…",
    "prereqs": ["M6"], "objectives": ["…"],
    "entries": [{
      "twin": "DellPowerFlex", "port": 5189,
      "tour": {"id": "no-controller", "ready": false},
      "fallback": {"kind": "phase", "value": "rebuild"},
      "trace": "cluster"
    }, {
      "twin": "PhysicsStorage", "port": 5206,
      "scenario": {"id": "scale-out-rebuild", "hashReady": false, "title": "Scale-up vs scale-out rebuild"}
    }],
    "predict": {"q": "…", "options": ["…"], "answer": 2, "evidence": "…", "cite": ["DellPowerFlex/backend/tests/test_engine.py::test_every_surviving_node_rebuilds"]},
    "checks": [{"q": "…", "a": "…", "cite": ["…"]}],
    "bridge": {"text": "…", "next": "M8"},
    "text": {"novice": {"idea": "…"}, "standard": {}}
  }],
  "tracks": [{"id": "storage-admin", "title": "…", "steps": [{"module": "M6"}, {"module": "M10", "only": ["DellCloudIQ"]}]}]
};
```

The renderer builds hrefs from the data, so a link is never typed by hand:
- if `tour.ready`, the href is `http://localhost:<port>/#tour/<id>`, otherwise the fallback;
- if `scenario.hashReady`, the href is `http://localhost:<port>/#scenario=<id>`,
  otherwise the root, with the instruction "choose *<title>* under Guided scenarios".

### 5.4 Progress and reading level

- **Progress:** `localStorage["learn-progress-v1"]` =
  `{ "M7": { "predicted": 2, "revealed": true, "checks": {"0": "got", "1": "missed"}, "done": true, "at": "2026-09-18" }, "track": "storage-admin" }`.
  Every read and write goes through `try/catch`; if the store is unavailable, the
  pages work without saving. A module counts as done once its answer has been
  revealed and every check has been marked. The course home shows done and total
  counts per track as text, with no progress bars. A "Reset progress" button
  clears the key.
- **Reading level:** use the shared `twin-reading-level` key through `setup.js`,
  which toggles `body[data-register]`: 1–2 novice, 3–5 standard. Authored text
  carries both registers in `text.novice` / `text.standard`, and the renderer
  emits `.lvl-novice` / `.lvl-standard` spans. The executive track forces the
  novice register only if the reader has not chosen a level. Because the key is
  shared, a reader who picks level 1 in a twin sees the novice course, and the
  other way round.

### 5.5 The link test (`Learn/tests/test_links.py`)

Same style as `CustomerSetup/tests/test_links.py`: stdlib only, runnable as
`python3 Learn/tests/test_links.py` and collected by the root `pytest`. It parses
`course.js` by stripping the `window.COURSE = ` prefix and the trailing `;`, then
calling `json.loads`. Tests:

| Test | Pins |
|---|---|
| `test_layout` | the files in §5.1 exist; every HTML page links `setup.js` after `learn.js` |
| `test_ports_match_registry` | each entry's `port` equals `ports.json["twins"][twin]["frontend"]`; `twin` is a real top-level dir |
| `test_reserved_port` | `ports.json["reserved"]["learnPages"] == 5172`; `serve.sh` uses it; no twin's frontend or backend uses 5172 |
| `test_phase_fallbacks_name_real_phases` | `"<phase>"` appears in `<twin>/backend/app/engine.py` (the same check as `test_phase_links_name_real_phases`) |
| `test_step_fallbacks_are_in_range_and_phase` | `#step=N` entries declare `expectPhase`; that phase is real. When the twin's `.venv` exists, `simulate()[N].phase == expectPhase` is checked in a subprocess with the twin's interpreter; otherwise the check is skipped |
| `test_tour_ids` | if `tour.ready`, the id appears in `<twin>/backend/app/tour.py`. If `ready` is false but `tour.py` now contains the id, the test **fails** with "flip ready to true", so the course picks up tours as they land |
| `test_scenario_ids` | the id is a `GuidedScenario(id=...)` in `<app>/backend/app/presets.py` (AST parse); `title` matches that scenario's `title` |
| `test_cites_resolve` | every `path::test_name` cite exists: the file exists, and `def test_name` appears in it |
| `test_modules_and_tracks_consistent` | ids unique; `prereqs` / `bridge.next` / track steps name real modules; `only` names twins that the module's entries use; no cycles in prerequisites |
| `test_every_module_has_the_contract` | predict (q, ≥ 3 options, answer index in range, evidence, ≥ 1 cite), 2–4 checks each with a cite, both reading registers for `idea` |
| `test_trace_endpoints_exist` | `data-twin-trace` values name a route in the twin's `main.py` (reuse the CustomerSetup helper logic) |
| `test_root_index_links_learn` | `index.html` contains `href="Learn/index.html"` |
| `test_customer_setup_links` | M12's links to CustomerSetup pages resolve to real `setup.html` files |

### 5.6 Changes outside `Learn/` the build will need

Each item is small, and none of them was made by this design task:

- `ports.json`: add `"learnPages": 5172` under `reserved`. 5170 is CustomerSetup.
  5171 is already used by `packages/twin-ui/gallery/vite.config.ts` but is **not
  registered**; registering it too would be a sensible follow-up.
- `index.html`: in the lede, next to the CustomerSetup gallery link, add one
  sentence and the link `<a href="Learn/index.html">Learn the twins as one course</a>`.
- `.gitlab-ci.yml`: add `Learn` to the shard list next to `CustomerSetup`
  (currently lines 30–31).
- The per-app `#scenario=` hash handling (§1) and the `#tour/<id>` route (the tour
  rollout).
- CLAUDE.md / README.md: add a short "Learn" section under the CustomerSetup one.

---

## 6. Tour ids the course needs that §8 does not define

ACTIVE_TWIN_SPEC.md §8 predates these twins. The course proposes the ids below so
the tour rollout can adopt them. Until a twin's `tour.py` contains its id, the
course uses `ready: false` and the phase fallback.

| Twin | Proposed signature id | Beat it pins | Fallback |
|---|---|---|---|
| DellPowerEdgeXE9680 | `chassis-wall` | `gpusInDomain` snaps to 8 and never grows when the NICs join | `#phase=fuse` |
| DellQuantumX800 | `credit-before-send` | the burst stalls senders; `packetsSentWithoutCredit` stays 0 | `#phase=burst` |
| DellPrivateCloud | `hypervisor-slot` | a second hypervisor arrives with one control plane and zero downtime | `#phase=switch` |
| DellPowerStoreElite | `zero-downtime-join` | `downtimeSeconds` is 0 through the longest stage (`rebalance`) | `#phase=rebalance` |
| DellPowerEdgeR760Thermal | none (physics app) | uses `#scenario=` | n/a |

The §8 ids the course uses directly: `memory-training`, `always-on`,
`mirrored-ack`, `vault-to-flash`, `atomic-fuse`, `heat-balance`, `no-controller`,
`onefs-stripe`, `metadata-leaves`, `zero-drops-under-stress`,
`airgap-discipline`, `blind-then-read`, `breach-reaches-nothing`, `analyze-dip`,
`primary-election`, `zero-touch`, `weights-cross-once`. Two of them,
`onefs-stripe` and `zero-touch`, come from §8 rows written while those twins were
only specs; the rows say "finalized when built", so check them when the tours are
authored.

---

## 7. Electives (outside the spine, same template)

Short single-scenario modules that tracks can append:

| Elective | Entry | Idea | Settled by |
|---|---|---|---|
| E1 Rack power | `:5217/#scenario=old-batteries` | The UPS front panel believes nameplate Wh until a self-test | `PhysicsRackPower/backend/tests/test_engine.py` (runtime-gap test) |
| E2 Shared chassis | `:5212/#scenario=noisy-neighbor` | One hot sled taxes the chassis fans for all eight bays | `PhysicsMX7000/backend/tests/test_engine.py::test_noisy_neighbor_taxes_the_shared_fans` |
| E3 Rugged edge | `:5213/#scenario=filter-nobody-changed` | A fouled filter makes the same heat wave throttle | `PhysicsXR/backend/tests/test_engine.py` (filter acceptance test) |
| E4 Dedupe as arithmetic | `:5215/#scenario=entropy-alarm` | The entropy alarm fires by day 42; capacity notices weeks later | `PhysicsDataDomain/backend/tests/test_engine.py::test_acceptance_entropy_alarm_fires_before_capacity_notices` |
| E5 Modernize without migrating | `:5220/#phase=rebalance` | `downtimeSeconds` stays 0; 3× only after cutover | `DellPowerStoreElite/backend/tests/test_engine.py` |
| E6 The laptop's power path | `:5176/#phase=handshake` | An unrecognized adapter throttles, but the phases still complete | `DellAlienware/backend/tests/test_engine.py` |
| E7 The data pipeline | `:5210/#scenario=find-the-bottleneck` | Throughput is the minimum of the stages; fixing one moves the bottleneck | `PhysicsData/backend/tests/test_engine.py::test_fixing_the_bottleneck_moves_it` |

Before an elective ships, its cite must be narrowed to an exact test name. That
is what `test_cites_resolve` requires.

---

## 8. Keeping answers honest

- An answer is only as good as its cite. `test_cites_resolve` checks that each
  cited test still exists, but not that it still asserts the same number. When an
  engine changes a number the course quotes (for example the 98% congestion or the
  20:1 ratio), the component's own test changes in the same commit, and the
  course's `cite` points straight at that test. Reviewers of engine changes should
  search `Learn/course.js` for the component name.
- Quoted trace numbers (the values in §3) come from `simulate()`. An optional test,
  `test_quoted_numbers` (a follow-up, not part of the first build), could store
  `{twin, step, field, value}` tuples and check them through each twin's venv, in
  the same subprocess pattern as `test_step_fallbacks_are_in_range_and_phase`.
- Wording follows the twins: figures are illustrative unless the twin marks them
  sourced. Product claims are attributed as the twins attribute them (for
  example Cyber Detect's 99.99%, which Dell quotes from a 2024 ESG report
  commissioned by Index Engines).

---

## 9. As built (2026-09-18)

Reality moved while this brief was written, and the build follows reality:

- **Tours landed everywhere.** Every narrative twin now has
  `backend/app/tour.py` and its `App.tsx` parses `#tour/<stepId>`, so every
  narrative entry links a tour beat first and keeps a `#phase=`/`#step=` link
  beside it. The `ready` flag in §5.3 is gone. `test_tour_ids_exist` pins ids
  against the `TourStep(id=...)` calls (resolving `id=SIGNATURE_STEP_ID`), and
  `test_twins_with_tours_link_one` fails if a module links a twin that has a
  tour only by phase.
- **§6's proposed ids were superseded by the shipped ones:** XE9680
  `domain-stops-at-eight` (not `chassis-wall`), Quantum-X800
  `credits-before-bytes` (not `credit-before-send`), Private Cloud
  `hypervisor-switch` (not `hypervisor-slot`); PowerStore Elite's
  `zero-downtime-join` matches. The course also uses non-signature beats where
  they carry the answer better (`every-survivor-rebuilds`, `add-a-node`,
  `liquid-before-silicon`, `sharp-counters-cross`, `storage-grows-alone`).
- **`#scenario=<id>` landed in every physics app**, so the `hashReady` flag is
  gone too; scenario links carry the scenario's exact title, pinned against
  `presets.py`.
- **One page per module**, not one `module.html#m=` renderer:
  `Learn/modules/<id>.html` are thin generated shells
  (`Learn/scripts/gen_pages.py`), so each module has a real address. Tracks
  are picked on the course home (`index.html#track=<id>`) and carried on
  module links as `#track=<id>`; there is no `track.html`.
- **Links are data kinds**, not a tour/fallback pair: `tour`, `phase`, `step`
  (with `expectPhase`), `scenario`, `root`, `lesson` (the GPU `#live/tour`,
  with the lesson id to step to, since there is still no `#live/tour/<id>`),
  and `setup` (a relative link to a CustomerSetup page).
- **`test_quoted_numbers` is in the first build**, not a follow-up: each
  module carries `pins` (`twin`, `step` or `"agg": "max"`, `field`, `value`)
  and the test reads them from each twin's default trace through the twin's
  own `.venv` (skipped where no venv exists, as in CI). All 60-odd quoted
  numbers matched the engines on the build date.
- **Electives E1 to E7 ship** with the full contract (predict plus two
  checks, exact cites) and an `electives` track. E1 and E3 cite
  `test_old_batteries_runtime_gap_is_the_capacity_fraction` and
  `test_fouled_filter_throttles_where_a_clean_one_survives`; E5 and E6 use
  the Elite and Alienware tours.
- Registers: the idea, the predict question, the reveal and the bridge are
  authored in both registers (`test_every_module_has_the_contract`); objectives
  and checks are standard-register only.
- Registered: `ports.json` `reserved.learnPages = 5172`, the `Learn` CI shard
  in `.gitlab-ci.yml`, and the root `index.html` link.

## 10. Failure stops (added 2026-09-18)

Ten narrative twins now serve one failure trace each beside the happy path
(`GET /api/<trace>?scenario=<id>`, listed by `GET /api/scenarios`, opened in
the UI with `#scenario=<id>&phase=<name>` or `&step=N`; the happy path is
pinned byte-identical in each twin). The course uses them as follows.

- **A "When it goes wrong" stop per twin**, in the module that already teaches
  it, after the checks. It is a prediction under the same contract as the
  module's own: a question in both registers, three options, a commitment
  that unlocks the deep link, the answer hidden until revealed, and the tests
  that settle it. The data lives in the module's `failures` list in
  `course.js`; `learn.js` renders it; no generated page changes.
- **The stops are optional inside a module.** A module is still done on its
  reveal plus its checks. The `what-goes-wrong` track (`failuresOnly`) shows
  only the stops, and there a stop is done when each answer is revealed.
  The short track (`predictOnly`) hides them.
- **Pinned like everything else.** `test_failure_scenario_ids_exist_in_the_backend`
  checks each id against the twin's `backend/app` statically and, through the
  twin's own `.venv` and FastAPI's `TestClient`, against `GET /api/scenarios`,
  the scenario trace, the 404 for an unknown id, and the phase or step the link
  pauses on. `test_failure_quoted_numbers` reads every quoted number from the
  failure trace. Alienware's trace is a `POST`, so its stop carries the request
  body the test sends.

| Module | Twin | Scenario | The invariant the stop teaches | Settled by |
|---|---|---|---|---|
| M2 | DellIDRAC | `firmware-update-rollback` | The host never changes power state while iDRAC is dark; one bootable image always remains | `test_firmware_rollback.py::test_the_host_power_state_never_changes` |
| M4 | DellPowerEdgeXE9712 | `coolant-fault` | No GPU draws power without verified flow; the domain is 0 or 72, never 68 | `test_scenarios.py::test_the_domain_is_only_ever_0_or_72_never_68` |
| M6 | DellPowerStore | `node-loss-failover` | Zero acknowledged writes lost; writes stay mirrored on the shared NVRAM pair (not the 500) | `test_failover.py::test_writes_stay_mirrored_while_single_node` |
| M8 | DellPowerSwitchSN6000 | `gray-link` | The sick link reads up, drops stay 0, and throughput returns only when an operator steers traffic | `test_gray_link.py::test_throughput_recovers_only_after_traffic_is_steered` |
| M9 | DellPowerProtect | `cleaning-gc` | Expiry frees nothing; a clean frees only what nothing references; locked data never goes early | `test_cleaning_scenario.py::test_the_first_clean_returns_less_than_the_estimate` |
| M9 | DellCyberDetect | `dwell-exceeds-retention` | A corrupted copy is never certified clean; recovery goes off-array at an older point | `test_scenarios.py::test_a_corrupted_copy_is_never_certified_clean` |
| M10 | DellCloudIQ | `connected-no-data` | Never a green score on no data; only the customer side can fix it | `test_scenarios.py::test_never_a_green_score_on_no_data` |
| M10 | DellVxRail | `node-add-mismatch` | A mismatched node never joins vSAN; the refusal touches nothing | `test_nodeadd.py::test_a_mismatched_node_never_joins_vsan` |
| M10 | DellNativeEdge | `attestation-fails` | Nothing is deployed to an unattested device, and one bad device never delays the rest | `test_scenarios.py::test_one_bad_device_never_blocks_the_estate` |
| E6 | DellAlienware | `charge-taper-diagnostics` | Every zero-charge state has one named limiter; the thermal pause holds with hysteresis | `test_diagnostics.py::test_the_heat_pause_is_not_a_budget_problem` |

The realism limits the twins state are carried into the answers: the iDRAC
image switch is inferred, the XE9712 rack-wide hold is site policy, the
PowerStore answer excludes the 500, the SN6000 steer-then-shut split is
operator practice, the Cyber Detect all-suspicious sequence is the twin's own
reading, the NativeEdge single-device failure is illustrative, the VxRail
refusal assumes an unsupported version pair, and the Alienware 45 °C and
42 °C thresholds are stand-ins.

## 11. Revision after the student review (2026-09-19)

Three simulated students (a newcomer reading at level 1, a practitioner at
level 3, a sceptical expert at level 5) took every module against the running
twins. `Learn/course.js` is the source of truth for what the pages say; §3 and
§7 above are the original brief and are superseded wherever they differ from
it. The findings clustered, and each cluster became a rule the tests now hold.

- **Only part of a page changed with the level.** The lede and the prediction
  were in two registers; the prerequisite, objectives, options, checks and
  every line under a link were not, so a level-1 reader met several undefined
  terms on the second line of most modules. Everything is now authored twice
  (`test_a_novice_reader_meets_no_unleveled_prose`), electives define their
  terms in a `background` line, and the pytest ids under an answer show in the
  standard register only.
- **Answers quoted the engine, not the screen.** Step numbers were the 0-based
  `#step=` index against a UI that counts from one; phases were engine ids
  (`bmc`, `gpuinit`, `growstorage`) the UI never shows; "cycle cost" appears on
  no screen; several numbers were a test's assert bound ("more than 1.5×",
  "under 40 W", "more than five times") when the screen shows a value. Answers
  now use the on-screen numbering and labels, describe the dwell as what the
  reader can watch (Run lingers, the elapsed clock jumps), gloss cycle cost
  once as a relative weight, and quote the displayed value with the test's
  bound named as a bound.
- **Predictions were given away.** Ledes, objectives, stop headings and the
  legible-but-locked link labels stated the answer. Ledes and objectives were
  reworded to pose the question, `lockedLabel` gives a neutral label until the
  reader commits, and three predictions that the module title settled were
  replaced (M8 asks what happens to total throughput when the hot link cools;
  M10 asks which Private Cloud stage takes longest; E5 asks what hosts see
  during the rebalance). Questions whose answer depended on an unstated
  premise now state it: M1 gives the die and the two starting numbers, M4's
  failure stop states the single-partition policy and asks only about the
  counter, M9 states that the attack stays under every threshold, M11 asks
  about the weights and not about all traffic, E6's failure stop gives the
  charge mode.
- **The evidence was not on the linked screen.** Checks leaned on experiments
  no link set up. Links were added for them (ME5 Lose a controller, MX7000's
  two feed-loss runs, RackPower Balance the phases, PowerFlex at steady I/O,
  the GPU simulator's LLM token decode workload in M11, Fleet's two ×8
  presets), every physics-app link carries a `how` line naming the speed
  control, the instrument and the moment to read it, and the XE9712 failure
  link now lands on the leak the question is about.
- **Nothing bridged one twin to the next.** Pairs of twins drawn separately
  disagree on illustrative numbers (R760 and iDRAC standby watts and clocks,
  IR7000 and PhysicsCDU flows, Pro Max Plus and PhysicsClient token rates),
  and PowerScale's "no metadata server" sits beside Exascale's metadata
  server. Each entry after a module's first now has a `note` saying what it
  adds and how its numbers relate
  (`test_modules_with_several_twins_bridge_between_them`).
- **Overclaims.** M1's "not a property of the chip" (the ridge point is one),
  M2's "cannot be skipped" (training is cached), M6's lockstep as a product
  fact (it is the twin's symmetry; the nodes boot independently), M8's "loss
  impossible to express" (congestion loss only, and both fabrics pay in
  backpressure), M5's "share that leaves through the liquid" (all of it does;
  91% is the cold-plate share), E1's self-test (a runtime calibration on real
  units), E2's N+1 answer (true of the model's single-feed cabling).
- **Scenario numbers are pinned.** `scenarioPins` and
  `test_scenario_quoted_numbers` read every figure the text quotes from a
  guided scenario through the app's own routes. Several twins changed while
  this review ran (R760Thermal's fan-feedback run, PhysicsAIFactory's hold
  power, PhysicsXR's filter run, PhysicsData's limiter readout, IR7000's
  flows, PowerFlex's IOPS); the text quotes the current values.
- **A chip that says running can be another app.** A dev server that finds
  its port busy drifts onto the next, and the liveness ping cannot tell. Each
  entry carries the twin's `pageTitle`; the page reads the title of whatever
  answers on the port and says so when it is a different app.

