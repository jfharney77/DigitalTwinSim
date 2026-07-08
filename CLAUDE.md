# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo layout: one directory per simulated component

The repo is organized by hardware component. `GPU/` holds the GPU digital twin (everything below); `DellPowerEdgeR760/`, `DellPowerStore/`, `DellAlienware/`, `DellIDRAC/`, `DellPowerMax/`, `DellPowerSwitchE3200/`, `DellVxRail/`, and `DellCloudIQ/` are the second through ninth components, following the same pattern (see their sections at the end of this file); future components (CPU, NIC, memory hierarchy, ...) get sibling top-level directories following the same pattern: a pure-engine FastAPI `backend/`, a React/Vite `frontend/` in the Dell clean-design skin, `scripts/`, and numbered `spec_NN_*.md` files driving the work. (Port note: `DellPowerMax/` + `DellPowerSwitchE3200/` were both authored on 8005/5178, and `DellVxRail/` on 8006/5179 — collisions; `DellCloudIQ/` uses the next free ports, 8007/5180. Run colliding twins one at a time or reassign.)

## Current state

The app is implemented as a **Python/FastAPI backend + React/Vite/TypeScript frontend**. The spec's three-layer design is split across the wire: the **backend owns the pure deterministic engine**, and the **frontend fetches the full `SimState[]` trace and animates it on its own clock**.

Reference files:
- `GPU/initial_spec.md` — the authoritative design + roadmap (data models, invariants, scope).
- `GPU/gpu-sim.html` — the original single-file reference implementation (inline SVG + vanilla JS). It is the **behavior oracle** — open it in a browser to compare behavior. Not the architecture; see "Oracle vs. spec" below.

### Layout & commands

```
GPU/backend/   app/{models,profiles,mapping,matrices,engine,mlp,anatomy,main}.py + tests/
GPU/frontend/  src/{api,types}.ts, App.tsx, components/{DieView,MatrixPanels,OpPipeline,
               Controls,Counters,Legend,InfoDot,AnatomyPage,AnatomyView}.tsx
GPU/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run everything: `./GPU/scripts/start_all.sh` (backend :8000 background, frontend :5173 foreground). Stop: `./GPU/scripts/stop_all.sh`.
- Backend tests: `cd GPU/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd GPU/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8000`; if :8000 is taken (another component's backend, another session), run the backend elsewhere and point Vite at it: `API_TARGET=http://localhost:8010 npm run dev`.
- Two workloads on the simulator page: `matmul` (spec_01–05) and `mlp_step` (spec_06 — an MLP training step as five chained matmuls). The die-anatomy page is the second tab.

### Where things live (maps spec's `src/` layout onto the split)

- `model/` → `GPU/backend/app/models.py` (pydantic `GpuProfile`/`Workload`/`SimState`, camelCase JSON) + `profiles.py`.
- `sim/` → `GPU/backend/app/engine.py` (`simulate(profile, workload) -> list[SimState]`, plus `analyze(...) -> Summary` for the roofline read-out) + `mapping.py`. **Keep this pure** — no FastAPI/IO imports, so the trace tests stay fast. Tiling (spec_03): the load/compute/writeback phases repeat per tile; `Workload.tile_size` of `0` or `>=N` means one tile = the whole matrix, which reproduces the original single-LOAD trace exactly (this is why the spec_01 tests still pass). `SimState.tile_row/tile_col/k_tile` carry tile context. Bandwidth model (spec_04): each LOAD stays one state with `stalled=True` and a `cycle_cost` (bytes/`bytes_per_cycle`); the **UI dwells** on costly loads instead of the trace emitting per-cycle states. `analyze()` returns the memory- vs compute-bound `regime` (intensity vs ridge point); it's illustrative, not cycle-accurate.
- `render/` → `GPU/frontend/src/components/DieView.tsx` (profile-driven SVG, painted from `SimState.coreState`) + `MatrixPanels.tsx` (A/B/C grids with tiling overlays). Operands come from `GPU/backend/app/matrices.py` (`make_operands`, deterministic) and ride in the simulate response as `a`/`b`. With tiling, C fills in tile-by-tile, so `MatrixPanels` replays the trace up to the cursor to compute each cell's accumulation depth (not a single global `k`).
- `ui/` → `Controls.tsx` / `Counters.tsx` / `Legend.tsx` / `OpPipeline.tsx` (spec_06 op strip).
- **MLP training step (spec_06)** → `GPU/backend/app/mlp.py`: pure like the engine; chains `engine.simulate()` once per matmul op (stripping per-op idle/done bookends, restamping cycle/mac counters, adding `op_index`/`op_name`/`step_index`), pointwise ops are one flash state, and the numerics are real (per-step `loss` in the response; `tests/test_mlp.py` asserts it strictly falls for the canned seed). `MlpInfo.ops` aligns with `SimState.op_index`; the frontend derives the panel operands and per-op tiling counters from the *display op* (current matmul, or nearest preceding one during pointwise/done).
- **Die-anatomy page** (second tab, deep-linkable via `/#anatomy/<dieId>`) → `GPU/backend/app/anatomy.py` (annotated floorplans of real GPUs as data — regions in a normalized coordinate space, stats, vendor whitepaper/die-shot sources, and per-region `Photo`s hotlinked from Wikimedia Commons whose `credit` line the UI must always render; geometry invariants in `GPU/backend/tests/test_anatomy.py`) + `GPU/frontend/src/components/AnatomyPage.tsx` / `AnatomyView.tsx` (data-driven SVG renderer; new dies are backend data, not frontend code). Layouts are stylized mental models traced from vendor diagrams, not mm²-accurate. **Both pages use the Dell clean-design skin** (light, Roboto, Dell blue) scoped under `.app.dell` + `body.dell-body` in `styles.css` — per the `dell-clean-design` skill: no eyebrow text, no step numbers, no divider rules, no highlighted text, no serifs. Page chrome is light; the die schematic, matrix panels, and anatomy floorplan stay dark — they are the diagrams, and their palette lives in the `:root` vars. Keep new page-chrome styles inside the `.app.dell` scope.
- `app.ts` → `GPU/frontend/src/App.tsx` — composition root; **owns the playback clock** (the `setInterval` lives here, never in the engine).

### Cross-cutting gotcha

`models.py` uses a camelCase alias generator, but `cores_per_sm` would camelize to `coresPerSm` — it has an explicit `alias="coresPerSM"` to match the spec/TS. If you add a field whose camelCase is ambiguous (embedded numbers/acronyms), verify the JSON key matches `GPU/frontend/src/types.ts` by hand.

## Oracle vs. spec — known discrepancies

The oracle does **not** implement the spec literally. A refactor must reconcile these deliberately, not copy bugs forward blindly:

- **Phases differ.** The spec describes 5 phases (`idle→load→compute→writeback→done`). The oracle's state machine has only 3 (`phase` = `0` load, `1` compute, `2` done). There is no `idle` phase in state (it's just the pre-run label) and **no separate writeback phase** — writeback is folded into the final compute step (when `k>=N`, cores flash `--core-hot` and it jumps straight to done). If you keep the spec's 5-phase model, that's a *change* from the oracle.
- **The oracle's `step()` is not pure.** It reads inputs from the DOM (`el("size").value`), mutates the DOM directly (counters, `paintCores`, `setMem`), and uses module-global `state`/`timer`. This violates the spec's purity/separation principles on purpose — the refactor's whole point is to extract a pure engine emitting `SimState` and move all DOM work into `render/`.
- **No `SimState`/`CoreState` data layer.** The oracle paints SVG fill colors inline rather than emitting the `coreState[]` / `utilization` data the spec's `SimState` defines.
- **Hardwired dimensions.** SM grid is hardcoded `4×2`, cores `4×4` → 128 lanes (not driven by a `GpuProfile`); `N` is square only, slider-capped at 2–8. Generalizing these is roadmap work, not part of the structural refactor.

## Behavior the oracle establishes (preserve these in a refactor)

- `cycle` increments once per phase-step (including the single load step) — it is not a hardware cycle count.
- LOAD is one step: memory highlights, cores paint `--sm-edge`.
- COMPUTE runs `N` accumulation steps; each adds `N*N` MACs (`macDone += N*N`), so total is `N*N*N`.
- Cell→core map is round-robin `core = (i*N + j) % totalCores`; in compute, every mapped core is active each k-step, so `activeCores = min(N*N, totalCores)`.
- `utilization = activeCores / totalCores` (totalCores = 128 in the oracle).
- Changing `N` resets; Step pauses the timer and runs one step; Speed retunes the interval live (`ms = max(40, 600/speed)`).

## Design principle: strict separation of concerns

Data flows one direction: **UI (frontend) → Sim (backend engine) → Renderer (frontend)**, communicating only through plain-data `SimState`. `GpuProfile` describes the die; all visual/structural geometry derives from it, so new GPUs are *data* (`profiles.py`), not code. The renderer (`DieView.tsx`) is swappable (SVG → Canvas/WebGL) as long as it consumes `SimState.coreState`.

The implemented engine follows the spec's **5-phase model** (`idle → load → compute → writeback → done`), reconciling the oracle's 3-phase shortcut (the oracle folds writeback into the last compute step — see below).

## Non-negotiable invariants

Enforced by `GPU/backend/tests/` (`test_engine.py`, `test_tiling.py`, `test_bandwidth.py`, `test_double_buffering.py`, `test_mlp.py`, `test_anatomy.py`) — keep them green:

- **The clock lives in the frontend, never in the engine.** No timers in `engine.py`/`SimState`; the `setInterval` is in `App.tsx`. The trace is pure data.
- Phases follow `idle→load→compute→writeback→done`; with tiling the `load→compute→writeback` cycle repeats once per output tile (so phase order is only monotonic within the single-tile / whole-matrix case).
- `macDone <= macTotal` and is monotonic non-decreasing; at `done` `macDone === N*N*N === macTotal`, for every tile size.
- `activeCores <= totalCores`, where `totalCores = sm.rows*sm.cols * coresPerSM.rows*coresPerSM.cols`.
- `utilization === activeCores / totalCores`.
- Cell→core mapping is **tile-aware** (`mapping.tile_aware_core`): a whole output tile is assigned to one SM (tiles round-robin across SMs by linear index), and each cell maps to a lane *within that SM*. A tile never straddles two SMs — they don't share memory. The legacy global round-robin `core = (i*N + j) % totalCores` (`cell_to_core`) is retained for reference only; it could scatter one tile across several SMs.
- Changing N refetches the trace and resets the cursor; Step advances exactly one state; Speed retunes the interval live.
- **MLP training step (spec_06):** `macTotal = steps × 5 × N³`; op order is exactly `Z1, relu, Z2, δ2, dW2, δ1, dW1, update` per step; every spec_01–05 invariant holds *inside* each matmul op; and the per-step `loss` strictly falls for the canned seed (η = 0.01) — the network must genuinely learn or `test_mlp.py` fails.

## Testing approach (spec §8)

Test the engine against full-trace assertions (the invariants above), not the HTTP layer. The engine is pure precisely so these tests need no server or DOM. Add cases when you touch phase logic or mapping.

## Scope guardrails (spec §1)

Not a cycle-accurate simulator; timing is illustrative. Not tied to any vendor ISA — "SM", "CUDA core", "warp" are generic vocabulary. Renders tens to low-hundreds of elements, not real GPU-scale tensors. Favor a correct *mental model* over correct numbers. See spec §7 for the roadmap (M×K×N generalization, tiling, tensor-core/systolic mode) before adding features.

## DellPowerEdgeR760 — server digital twin (second component)

Same architecture as GPU/, applied to the Dell PowerEdge R760 2U rack server. See `DellPowerEdgeR760/initial_spec.md` for the full spec.

```
DellPowerEdgeR760/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellPowerEdgeR760/frontend/  src/{api,types}.ts, App.tsx, components/{ChassisView,AnatomyPage,CatalogPage,UseCasePage,PowerOnControls,PowerOnCounters}.tsx
DellPowerEdgeR760/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellPowerEdgeR760/scripts/start_all.sh` (backend :8001 background, frontend :5174 foreground — ports offset from GPU's 8000/5173 so both apps run together). Stop: `./DellPowerEdgeR760/scripts/stop_all.sh`.
- Backend tests: `cd DellPowerEdgeR760/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellPowerEdgeR760/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8001`.

Key points (the GPU invariants carry over):

- **Purity invariant:** `engine.py`'s `simulate()` emits the whole power-on sequence as a `PowerOnState[]` trace — pure data, no timers/IO/FastAPI imports (AST-checked in `tests/test_engine.py`). The playback clock (`setInterval`) lives in `frontend/src/App.tsx`, never in the engine. Phase order `off→standby→bmc→poweron→post→boot→os` never regresses; `activeRegions` ids must exist in the anatomy; long stages (DDR5 memory training) carry `cycleCost > 1` and the UI dwells on them.
- **Chassis anatomy, component catalog, and use cases are backend data, not frontend code** (`anatomy.py` — stylized 100×46 floorplan traced from Dell's interior photo, geometry invariants in `tests/test_anatomy.py`; `catalog.py` — 12 option categories with `regionIds` tying them to the floorplan; `usecases.py` — build sheets whose category/option ids must resolve against the catalog, enforced in `tests/test_catalog.py`). `ChassisView.tsx` renders whatever regions it is sent.
- All four pages (`/` power-on sim, `#anatomy`, `#components`, `#usecases`) use the Dell clean-design skin; the chassis floorplan stays dark — it is the diagram.
- Copy is written for a technically skilled reader new to the product: spell out Dell terms (iDRAC, PERC, BOSS-N1, OCP 3.0) on first use; wattages/timings are illustrative, not measured.

## DellPowerStore — storage-array digital twin (third component)

Same architecture, applied to the Dell PowerStore all-NVMe storage appliance (2U, **two active-active controller nodes** sharing a 25-slot dual-ported NVMe drive bay). See `DellPowerStore/initial_spec.md` for the full spec.

```
DellPowerStore/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellPowerStore/frontend/  src/{api,types}.ts, App.tsx, components/{ChassisView,AnatomyPage,CatalogPage,UseCasePage,PowerOnControls,PowerOnCounters}.tsx
DellPowerStore/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellPowerStore/scripts/start_all.sh` (backend :8002 background, frontend :5175 foreground — ports offset from GPU's 8000/5173 and the R760's 8001/5174 so all three apps run together). Stop: `./DellPowerStore/scripts/stop_all.sh`.
- Backend tests: `cd DellPowerStore/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellPowerStore/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8002`.

Key points beyond the R760 pattern:

- **Phase order** is `off→power→boot→drives→cluster→services→online` (no power button — applying AC is the power-on). The PowerStoreOS container-boot step carries the largest `cycleCost`.
- **Dual-node symmetry invariant** (`tests/test_engine.py`): per-node regions come in `-a`/`-b` twins (same kind and size, checked in `tests/test_anatomy.py`), and during the `power`/`boot` phases every lit `-a` region must light its `-b` twin — the nodes bring up in lockstep.
- Region kinds add `nvram` (mirrored write cache; writes acknowledge from both nodes' NVRAM) and `battery` (BBUs that vault cache on AC loss). Photos are the local `/powerstore1..4.webp` files in `frontend/public/` — tests forbid external photo URLs.
- Copy spells out storage vocabulary (NVRAM, vaulting, active/active, NVMe-oF, Metro Volume) on first use; wattages/timings are illustrative.

## DellAlienware — gaming-laptop digital twin (fourth component)

Same architecture, applied to the Alienware m18 gaming laptop — a digital twin of the AC power path answering "what happens inside when you plug it in" (adapter conversion, 1-Wire PSID handshake, power budgeting, Li-ion charge ramp, hybrid battery supplement under load). See `DellAlienware/initial_spec.md` for the full spec.

```
DellAlienware/backend/   app/{models,catalog,anatomy,engine,usecases,main}.py + tests/
DellAlienware/frontend/  src/{api,types}.ts, App.tsx, components/{PowerPathView,AnatomyPage,AnatomyView,UseCasePage,PowerControls,PowerCounters}.tsx
DellAlienware/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellAlienware/scripts/start_all.sh` (backend :8003 background, frontend :5176 foreground — ports offset from GPU's 8000/5173, the R760's 8001/5174, and PowerStore's 8002/5175 so all four apps run together). Stop: `./DellAlienware/scripts/stop_all.sh`.
- Backend tests: `cd DellAlienware/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellAlienware/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8003`.

Key points beyond the R760 pattern:

- **Phase order** is `off→detect→handshake→budget→charge→boot→load→steady`; `POST /api/simulate` takes a `Scenario` (profile, adapter, start charge, thermal mode, workload) and returns profile + adapter + `Summary` + `PowerState[]` trace. The PSID handshake stage is `stalled` with the dwell `cycleCost`.
- **Energy-conservation invariant** (`tests/test_engine.py`): every state satisfies `acW + batteryW == systemW + chargeW` (±0.5 W); never charging and discharging at once; `acW <= adapter.watts`; `hybrid` is true exactly while the battery supplements the adapter (demand above the adapter budget, pack above 20%). An `AdapterOption` with `recognized: false` models a failed handshake — `regime "throttled"`, `chargeW == 0`, capped CPU/GPU, but the phase machine still completes.
- **Catalog, anatomy, and use cases are backend data** (`catalog.py` — laptops with adapter options, every profile keeps one unrecognized adapter so the throttled path stays reachable; `anatomy.py` — stylized 100×62 interior floorplan traced from the service photo `frontend/public/alienware-interior.jpg`, geometry + required-region-id invariants in `tests/test_anatomy.py`; `usecases.py` — step `regionIds` must resolve against the anatomy, enforced in `tests/test_catalog.py`). Trace `activeRegions` ids must exist in the profile's anatomy.
- Copy spells out laptop-power vocabulary (EC, PSID, ExpressCharge, TGP, AWCC, hybrid power, UVP) on first use; wattages/timings are illustrative, anchored to Dell KB sources carried in the API's `sources` fields.

## DellIDRAC — service-processor digital twin (fifth component)

Same architecture, applied to the **iDRAC9** (integrated Dell Remote Access Controller) — the always-on baseboard management controller (BMC) embedded in every PowerEdge server. The twist: the subject is a *subsystem*, not a chassis, so the shared "anatomy" is a **functional block diagram** of the BMC (host-facing sideband buses on the left, the SoC core in the middle, the outside world on the right), and the "power-on" trace becomes iDRAC's **own firmware bring-up** — from AC-applied standby to a ready, watching controller, **with the host powered off the whole time**. It is the companion to the R760 power-on twin: iDRAC is the "brain" that R760 twin boots first. See `DellIDRAC/README.md`.

```
DellIDRAC/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellIDRAC/frontend/  src/{api,types}.ts, App.tsx, components/{BlockView,AnatomyPage,CatalogPage,UseCasePage,BringUpControls,BringUpCounters}.tsx
DellIDRAC/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellIDRAC/scripts/start_all.sh` (backend :8004 background, frontend :5177 foreground — ports offset from GPU 8000/5173, R760 8001/5174, PowerStore 8002/5175, Alienware 8003/5176 so all five apps run together). Stop: `./DellIDRAC/scripts/stop_all.sh`.
- Backend tests: `cd DellIDRAC/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellIDRAC/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8004`. Endpoint names differ from the chassis twins: the trace is `GET /api/bringup` (not `/api/poweron`), returning `BringUpResponse`.

Key points beyond the R760 pattern:

- **Renamed model shapes** (`models.py`): the anatomy container is `SubsystemMap` (not `ChassisAnatomy`) and its blocks are `Block` (not `ChassisRegion`), though the wire shape and camelCase rules are identical; `RegionKind` is a BMC-specific set (`soc`, `memory`, `network`, `sideband`, `io`, `power`, `security`, `sensor`) — `test_anatomy.py` asserts every kind is exercised (`kinds == EXPECTED_KINDS`), exactly one `soc`, and three `sideband` buses.
- **Bring-up trace** (`engine.py`, pure — AST-checked): phase order `off→standby→reset→bootldr→kernel→services→ready` never regresses; the host never powers on, so BMC-domain draw stays ≤20 W throughout (`test_host_never_powers_on`); `progressPercent` is monotonic 0→100; **Lifecycle Controller init is the single longest stage** (`cycleCost` max, UI dwells). `BringUpState` carries `progressPercent` (iDRAC init %, replaces the chassis twins' `fanPercent`) and `powerWatts` (standby BMC draw, single/low-double-digit watts).
- **Capabilities are unlocked by license, not bolted in** (`catalog.py`): the first category is the **license tier** (Basic/Express/Enterprise/Datacenter) — the same SoC/flash hardware does more as the tier rises. Categories map to blocks via `regionIds`; use-case configs are sets of *enabled capabilities* (license + interfaces + features), and `test_catalog.py` enforces every config line resolves to a real option.
- Copy spells out systems-management vocabulary (BMC, Redfish, RACADM, NC-SI, Lifecycle Controller, Root of Trust, SCP, ZTP, telemetry streaming) on first use; the anatomy page carries Dell doc `sources`. The only visual asset is a self-contained, honestly-credited illustration `frontend/public/idrac9-console.svg` (not a Dell product image). Timings/wattages are illustrative.

## DellPowerMax — mission-critical scale-out storage twin (sixth component)

Same architecture, applied to the Dell **PowerMax 2500/8500** — Dell's flagship end-to-end NVMe **scale-out** array. The twist versus PowerStore: PowerMax is rack-scale and built from modular **node pairs** (two compute *directors* each) joined by a 100 Gb/s **InfiniBand Dynamic Fabric**, with drives living separately in **Dynamic Media Enclosures (DMEs)** reached over that fabric — so compute and capacity scale independently. See `DellPowerMax/initial_spec.md`.

```
DellPowerMax/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellPowerMax/frontend/  src/{api,types}.ts, App.tsx, components/{ChassisView,AnatomyPage,CatalogPage,UseCasePage,PowerOnControls,PowerOnCounters}.tsx
DellPowerMax/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellPowerMax/scripts/start_all.sh` (backend :8005 background, frontend :5178 foreground — ports offset from GPU 8000/5173, R760 8001/5174, PowerStore 8002/5175, Alienware 8003/5176, iDRAC 8004/5177 so all apps run together). Stop: `./DellPowerMax/scripts/stop_all.sh`.
- Backend tests: `cd DellPowerMax/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellPowerMax/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8005`. Same endpoint names and model shapes as the PowerStore twin (`/api/poweron` → `PowerOnResponse`, `ChassisAnatomy`/`ChassisRegion`).

Key points beyond the PowerStore pattern:

- **Phase order** is `off→power→vault→boot→fabric→drives→pool→services→online` (nine phases). PowerMaxOS 10 boot carries the strictly-largest `cycleCost`. A dedicated **`fabric` phase precedes `drives`** — the drives hang off the InfiniBand fabric, not a director's bus, so `test_engine.py` asserts the first fabric-phase step comes before the first drives-phase step. Watts scale to a node pair's ~2 kVA envelope (the array is rack-scale, not a 2U appliance).
- **PowerMax-specific `RegionKind` set**: `storage · vault · cache · cpu · fabric · io · power · cooling · battery · management · board`. New vs PowerStore: `vault` (NVMe SED vault-to-flash modules, where cache is dumped on power loss) distinct from `battery` (the standby power supply/SPS that powers the flush); `cache` (per-node DRAM = PowerMax "global memory"); `fabric` (InfiniBand Dynamic Fabric adapters + the shared `fabric-bus`). `test_anatomy.py` asserts `kinds == EXPECTED_KINDS` (every kind exercised) and exactly one `storage`/DME region.
- **Anatomy is one node-pair engine + one DME** (`anatomy.py`, stylized 100×52 top-down floorplan; a real array is 1–8 node pairs and many DMEs). **Dual-director A/B symmetry** carries over from PowerStore: per-node ids end `-a`/`-b`, and in the `power`/`vault`/`boot` phases every lit `-a` region lights its `-b` twin; the shared `fabric-bus` and `dme` regions carry no node suffix (the symmetry tests key on the `-a`/`-b` *suffix*, not a substring). No product photos are shipped (the `photo` field is optional and null — `test_anatomy.py` only requires credit *when* a photo is present); the roadmap note is to add credited local images later as PowerStore does.
- **Catalog (14 categories) and use cases (3) are backend data**: array family (2500/8500), node pairs, director CPUs (memory config), cache, drives, DME, Flexible RAID, Dynamic Fabric, front-end I/O, vault & standby power, PowerMaxOS software, management, power & PDUs, cabinet & dispersion; use cases are mainframe+open-systems consolidation, zero-RPO SRDF/Metro database, and a cyber-resiliency vault. `test_catalog.py` enforces resolvable ids/regions as elsewhere.
- Copy spells out enterprise-storage vocabulary (DME, director, node pair, SRDF/SRDF-Metro, SnapVX, FICON, zHyperLink, vault-to-flash, SPS, memory config, Flexible RAID, service levels) on first use; wattages/timings are illustrative, anchored to Dell's PowerMax 2500/8500 spec sheet carried in the anatomy `sources`.

## DellPowerSwitchE3200 — network-switch digital twin (seventh component)

Same architecture as the R760/PowerStore chassis twins, applied to the **Dell PowerSwitch E3200-ON Series** — a 1RU open-networking edge switch (Layer 3 distribution for enterprise/campus/branch). The "anatomy" is a top-down floorplan of the switch and the "power-on" trace is the switch **booting from AC to line-rate forwarding** — distinctively via the `-ON` (Open Networking) path: standby → CPU → **ONIE** (Open Network Install Environment bootloader) → disaggregated **network OS** (SmartFabric OS10 on the E3224F, Enterprise SONiC on the E3248 models) → **switching ASIC** programmed → ports/PoE up → line rate. See `DellPowerSwitchE3200/README.md`. Grounded in the E3200-ON spec sheet (Aug 2024) + Dell OS10/SONiC/ONIE docs.

```
DellPowerSwitchE3200/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellPowerSwitchE3200/frontend/  src/{api,types}.ts, App.tsx, components/{ChassisView,AnatomyPage,CatalogPage,UseCasePage,BootControls,BootCounters}.tsx
DellPowerSwitchE3200/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellPowerSwitchE3200/scripts/start_all.sh` (backend :8005 background, frontend :5178 foreground — ports offset from GPU 8000/5173, R760 8001/5174, PowerStore 8002/5175, Alienware 8003/5176, iDRAC 8004/5177 so all twins run together). Stop: `./DellPowerSwitchE3200/scripts/stop_all.sh`.
- Backend tests: `cd DellPowerSwitchE3200/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellPowerSwitchE3200/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8005`. The trace endpoint is `GET /api/boot` (not `/api/poweron`), returning `BootResponse`.

Key points beyond the R760 pattern:

- **Region kinds** (`models.py`, `RegionKind`) are switch-specific: `ports`, `uplink`, `poe`, `asic`, `cpu`, `mgmt`, `cooling`, `power` — `test_anatomy.py` asserts every kind is exercised, four `cooling` fans, two `power` PSUs, exactly one `asic`. The floorplan is the PoE-heavy 48-port layout, top-down, front (ports/console) at x=0 → rear (PSU/fans/100G uplinks) at x=100; airflow is I/O-to-PSU.
- **Boot trace** (`engine.py`, pure — AST-checked): phase order `off→standby→poweron→onie→nos→dataplane→ports→forwarding` never regresses; the **network-OS boot is the single longest stage** (`cycleCost` max, UI dwells — like the R760's memory training); `data_rate_gbps` is 0 through the boot phases and ramps to line rate at `forwarding`; **PoE delivery is the power peak** (most wattage is the PoE budget leaving the front ports, not the switch's own draw — `test_poe_step_is_the_power_peak`). `BootState` adds `data_rate_gbps` (forwarding Gbps) alongside `power_watts` + `fan_percent`.
- **Three fixed models, not a slot build** (`catalog.py`): the first category is the **model** (E3224F-ON fiber/OS10, E3248P-ON 30W-PoE/SONiC, E3248PXE-ON 90W-Multigig/SONiC); PoE class, uplink speed, NOS and PSU all follow from it. Categories map to floorplan regions via `regionIds` (the external power shelf has none — "mounts separately in the rack"); use-case configs resolve to real options (`test_catalog.py`).
- Copy spells out networking vocabulary (ONIE, NOS, PSE/802.3at/bt, MLAG, VRF-lite, VXLAN, SFP+/SFP28/QSFP28, Multigigabit) on first use; the anatomy page carries Dell doc `sources`. The only visual asset is a self-contained, honestly-credited front-panel illustration `frontend/public/e3200-front.svg` (not a Dell product image). Wattages/timings are illustrative.

## DellVxRail — hyperconverged-cluster digital twin (eighth component)

Same architecture as the chassis twins, applied to **Dell VxRail** — Dell's hyperconverged infrastructure (HCI) system, jointly engineered with VMware. The twist versus every earlier twin: the subject is a **cluster**, not one box. VxRail is built from identical PowerEdge-based nodes whose local NVMe drives are pooled by VMware vSAN into one shared datastore, managed for life by VxRail Manager. So the shared "anatomy" is a **four-node cluster floorplan** (identical nodes + a redundant top-of-rack switch pair), and the "power-on" trace is the cluster's **first run** — nodes booting in lockstep, electing a primary that runs VxRail Manager, then fusing their NVMe into one vSAN datastore. See `DellVxRail/README.md`. Grounded in the Dell VxRail product page, spec sheet (H16763), vSAN ESA Info Hub, and architecture guide.

```
DellVxRail/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellVxRail/frontend/  src/{api,types}.ts, App.tsx, components/{ClusterView,AnatomyPage,CatalogPage,UseCasePage,FirstRunControls,FirstRunCounters}.tsx
DellVxRail/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellVxRail/scripts/start_all.sh` (backend :8006 background, frontend :5179 foreground — ports offset from GPU 8000/5173, R760 8001/5174, PowerStore 8002/5175, Alienware 8003/5176, iDRAC 8004/5177, PowerMax/PowerSwitch 8005/5178 so all twins run together). Stop: `./DellVxRail/scripts/stop_all.sh`.
- Backend tests: `cd DellVxRail/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellVxRail/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8006`. The trace endpoint is `GET /api/firstrun` (not `/api/poweron`), returning `FirstRunResponse`.

Key points beyond the chassis-twin pattern:

- **Renamed model shapes** (`models.py`): the anatomy container is `ClusterAnatomy` and its regions are `ClusterRegion` (wire shape/camelCase identical to the chassis twins). `RegionKind` is HCI-node-specific: `compute · memory · storage · boot · network · management · power · fabric` — `test_anatomy.py` asserts `kinds == EXPECTED_KINDS`, one region of each per-node kind on every node, and exactly two `fabric` switches.
- **First-run trace** (`engine.py`, pure — AST-checked): phase order `off→power→esxi→discovery→primary→cluster→vsan→online` never regresses; `progressPercent` (replaces the chassis twins' `fanPercent`) climbs monotonically 0→100 mirroring the VxRail Manager build bar. **`FirstRunState`** carries `powerWatts` (whole-cluster draw) + `progressPercent`. Distinctive invariants: **nodes boot in lockstep** (`power`/`esxi`/`discovery` — every lit node region lights on all four nodes, keyed on the `-n1..-n4` suffix), **primary election lights exactly one node** (`primary` phase active set has suffixes `== {"n1"}` — the elected VxRail Manager node, breaking lockstep), and the **VxRail Manager cluster build is the single longest stage** (`cycleCost` max, UI dwells).
- **Anatomy is a four-node cluster** (`anatomy.py`, stylized 100×64 front-of-rack elevation; a real cluster is 2–64 nodes). Four-node symmetry: per-node ids end `-n1..-n4` and every node carries identical same-kind/same-size regions; the shared `tor-a`/`tor-b` switches carry no node suffix. No product photos ship — the only visual is a self-contained, honestly-credited schematic `frontend/public/vxrail-cluster.svg` (not a Dell product image); `test_anatomy.py` only requires credit *when* a photo is present.
- **Catalog (14 categories) and use cases (3) are backend data**: node platform (VE-660/VP-760/VS-760/VD-4000 + AMD VP-7625/VE-6615), processor (Intel Xeon 4th/5th gen, AMD EPYC), memory, vSAN architecture (ESA vs OSA), drives, boot (BOSS-N1), networking (25/100 GbE + RoCE), top-of-rack fabric (SmartFabric/customer-managed/Dynamic Node Networking), GPU, topology (standard/2-node ROBO/stretched/Dynamic Nodes), VxRail HCI System Software, VMware software (vSphere+vSAN / VCF), management, power; use cases are VDI, edge/ROBO, and a VMware Cloud Foundation stretched private cloud. Per-node categories light all four nodes via `regionIds`; `test_catalog.py` enforces resolvable ids/regions as elsewhere.
- Copy spells out HCI/Dell/VMware vocabulary (vSAN, ESA/OSA, BOSS, RoCE, vMotion, VCF, SDDC Manager, SmartFabric, Dynamic Nodes, witness, ROBO, primary election) on first use; the anatomy page carries Dell doc `sources`. Wattages/timings are illustrative.

## DellCloudIQ — CloudIQ / Dell AIOps observability twin (ninth component)

Same architecture, applied to **CloudIQ** — Dell's cloud-native **AIOps observability SaaS** (rebranded **Dell AIOps**, part of APEX AIOps, in 2024). The big twist: this is **software, not a box**, so both metaphors are adapted the way the iDRAC twin did. The shared "anatomy" is a **platform architecture diagram** (the telemetry-to-insight pipeline, laid out left→right), and the "power-on trace" is the **lifecycle of a batch of telemetry becoming an actionable insight**. See `DellCloudIQ/initial_spec.md`. Grounded in Dell's AIOps product page + support docs (Secure Connect Gateway, AIOps Collector); researched via web search.

```
DellCloudIQ/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellCloudIQ/frontend/  src/{api,types}.ts, App.tsx, components/{PlatformView,ArchitecturePage,CatalogPage,UseCasePage,PipelineControls,PipelineCounters}.tsx
DellCloudIQ/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellCloudIQ/scripts/start_all.sh` (backend :8007 background, frontend :5180 foreground — the next free ports after the 8005/5178 and 8006/5179 collisions among the earlier twins). Stop: `./DellCloudIQ/scripts/stop_all.sh`.
- Backend tests: `cd DellCloudIQ/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellCloudIQ/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8007`. The trace endpoint is `GET /api/pipeline` (not `/api/poweron`), returning `PipelineResponse`.

Key points beyond the R760/iDRAC pattern:

- **Renamed, SaaS-domain model shapes** (`models.py`, wire-compatible with the hardware twins so the frontend/tests carry over): `PlatformMap` (was `ChassisAnatomy`), `PlatformRegion` (was `ChassisRegion`), `PipelineState` (was `PowerOnState`). `PipelineState` swaps the hardware `powerWatts`/`fanPercent` telemetry for the CloudIQ metrics `progressPercent` (0→100) and `healthScore` (0–100), plus `dataPoints`.
- **`RegionKind`** is an AIOps-pipeline set: `source · gateway · ingest · analytics · security · insight · assistant · action`. `test_anatomy.py` asserts every kind is exercised, exactly one `gateway` and one `assistant`, and ≥2 `source` families. The "anatomy" is a **left→right architecture diagram** (100×58): monitored systems (telemetry in) → Secure Connect Gateway → cloud ingest → ML analytics + cybersecurity → insights/AIOps Assistant → notify (insights out); `PlatformView.tsx`'s orientation labels are "TELEMETRY IN" / "INSIGHTS & ACTIONS OUT" rather than FRONT/REAR.
- **Pipeline trace** (`engine.py`, pure — AST-checked): phase order `idle→collect→transmit→ingest→analyze→detect→surface→assist→notify` never regresses; the **ML `analyze` stage is the single longest** (`cycleCost` max, UI dwells). Signature behavior enforced in `test_engine.py`: `healthScore` starts at 100 (idle), dips below 100 at/after `detect`, and the final step recovers (above the low-water mark, below 100); `progressPercent` is monotonic 0→100; and **telemetry flows one way** (first `transmit` precedes first `surface`). No power/watts here at all.
- **Capabilities, not a bill of materials** (`catalog.py`, 10 categories): monitored systems, connectivity (SCG/Collector/SupportAssist/direct), health, capacity, performance, cybersecurity, sustainability, AIOps Assistant, integrations, access & licensing — each mapped to a diagram region via `regionIds`. Use cases (3: prevent a capacity shortfall, find a noisy-neighbor performance anomaly, watch cybersecurity posture) list *capabilities used* rather than parts (the UI drops the qty column); `test_catalog.py` enforces resolvable ids as elsewhere.
- Copy spells out AIOps/observability vocabulary (telemetry, Secure Connect Gateway, AIOps Collector, SupportAssist, Health Score, anomaly detection, noisy neighbor, capacity forecasting, ITSM/ServiceNow, AIOps Assistant / Infrastructure Context Awareness) on first use; the architecture page carries Dell `sources`. No product images ship (the `photo` field is optional/null; `test_anatomy.py` only requires credit when a photo is present). Counts/timings/Health-Score are illustrative.
