# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo layout: one directory per simulated component

The repo is organized by hardware component. `GPU/` holds the GPU digital twin (everything below); `DellPowerEdgeR760/`, `DellPowerStore/`, `DellAlienware/`, `DellIDRAC/`, `DellPowerMax/`, `DellPowerSwitchE3200/`, `DellVxRail/`, `DellCloudIQ/`, `DellPowerEdgeXE9712/`, `DellIR7000/`, `DellPowerProtect/`, `DellExascale/`, `DellPowerSwitchSN6000/`, `DellProMaxPlus/`, `DellPowerFlex/`, `DellCyberDetect/`, and `DellFortZero/` are the second through eighteenth components, following the same pattern (see their sections at the end of this file); future components (CPU, NIC, memory hierarchy, ...) get sibling top-level directories following the same pattern: a pure-engine FastAPI `backend/`, a React/Vite `frontend/` in the Dell clean-design skin, `scripts/`, and numbered `spec_NN_*.md` files driving the work. (Port note: `DellPowerMax/` + `DellPowerSwitchE3200/` were both authored on 8005/5178, and `DellVxRail/` on 8006/5179 — collisions; `DellCloudIQ/` uses the next free ports, 8007/5180. Run colliding twins one at a time or reassign.)

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

## DellPowerEdgeXE9712 — rack-scale AI digital twin (tenth component)

Same architecture as the chassis twins, applied to the **Dell PowerEdge XE9712** — Dell's rack-scale AI system built around **NVIDIA GB200 NVL72** (Dell AI Factory with NVIDIA, 2024–25). The twist versus every earlier twin: the subject is an **integrated liquid-cooled rack**, not a box in a rack — 18 compute trays (36 NVIDIA Grace CPUs + 72 Blackwell GPUs as GB200 superchips), 9 NVLink switch trays, power shelves feeding a DC busbar, and an in-rack CDU. The "anatomy" is a front-of-rack elevation (4 of 18 compute trays and 2 blocks for the 9 switch trays are drawn — stylized), and the "power-on" trace ends with the signature move no other twin has: the NVLink fabric **fusing all 72 GPUs into one domain** that software sees as a single giant GPU. See `DellPowerEdgeXE9712/README.md`. Grounded in Dell's XE9712 product page, the OCP-2024 AI Factory announcement (IR7000/PowerCool), and NVIDIA's GB200 NVL72 page.

```
DellPowerEdgeXE9712/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellPowerEdgeXE9712/frontend/  src/{api,types}.ts, App.tsx, components/{RackView,AnatomyPage,CatalogPage,UseCasePage,PowerOnControls,PowerOnCounters}.tsx
DellPowerEdgeXE9712/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellPowerEdgeXE9712/scripts/start_all.sh` (backend :8008 background, frontend :5181 foreground — the next free ports after CloudIQ's 8007/5180). Stop: `./DellPowerEdgeXE9712/scripts/stop_all.sh`.
- Backend tests: `cd DellPowerEdgeXE9712/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellPowerEdgeXE9712/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8008`. Trace endpoint is `GET /api/poweron` returning `PowerOnResponse` (chassis-twin style).

Key points beyond the chassis-twin pattern:

- **Renamed model shapes** (`models.py`): `RackAnatomy` / `RackRegion` / `PowerOnState` (wire shape/camelCase identical to the chassis twins). `RegionKind` is rack-scale-AI-specific: `gpu · compute · network · nvswitch · cooling · power · management` — `test_anatomy.py` asserts `kinds == EXPECTED_KINDS`, exactly two `nvswitch` blocks, two `power` shelves, cooling ids exactly `{cdu, manifold}`, one `management` block, and gpu/compute/network on every tray. `PowerOnState` carries `powerWatts` (whole rack, →~120 kW) and **`gpusInDomain`** (0–72, replaces `fanPercent`/`progressPercent` — the number that matters here is how many GPUs the fabric has fused).
- **Power-on trace** (`engine.py`, pure — AST-checked): phase order `off→power→coolant→trayboot→gpuinit→fabric→fused→ready` never regresses. Distinctive invariants (`test_engine.py`): **liquid before silicon** (first `coolant` step precedes first `trayboot` step — the inversion vs every air-cooled twin); **power is monotonic** to full load with its single biggest jump at `gpuinit` (the 72 ~1 kW Blackwells waking); **NVLink fabric training is the single longest stage** (`cycleCost` max, UI dwells — 5,000+ copper links); trays boot in **lockstep** (`-t1..-t4` suffix twins in `trayboot`/`gpuinit`); and the **fuse is atomic** — `gpusInDomain` is 0 for every step before `fused` and exactly 72 from then on, with the fuse step lighting every `gpu` region plus the `nvswitch` blocks (no partial domain, ever).
- **Anatomy is one integrated rack** (`anatomy.py`, stylized 100×86 front elevation): power shelves + rack mgmt at top, identical GB200 trays above/below the mid-rack NVLink switch trays (physically central so all copper runs stay short enough to skip optics), CDU at bottom, vertical coolant `manifold` up the right edge. Four-tray symmetry mirrors VxRail's node symmetry. The only visual is the self-contained, honestly-credited schematic `frontend/public/xe9712-rack.svg` (not a Dell product image); `test_anatomy.py` only requires credit *when* a photo is present.
- **Catalog (12 categories) and use cases (3) are backend data**: rack platform (GB200/GB300 NVL72), compute trays, GPUs (Blackwell/Blackwell Ultra), CPUs (Grace only — no Xeon/EPYC option, that's the point), NVLink scale-up fabric (switch trays + the 5,000-cable copper cartridge), scale-out networking (Quantum InfiniBand / Spectrum-X / BlueField-3), liquid cooling (PowerCool RCDU + eRDHx), power (shelves + busbar), management (BMC/OpenManage + NVIDIA Mission Control), external storage (PowerScale/ObjectScale — no drives in the rack), AI software (NVIDIA AI Enterprise/NIM + Dell AI Factory), delivery (IRSS factory integration + services). Use cases: 8-rack foundation-model training, single-GB300-rack real-time trillion-parameter inference, and a sovereign AI factory. `test_catalog.py` enforces resolvable ids/regions as elsewhere.
- Copy spells out rack-scale-AI vocabulary (superchip, NVLink/NVLink-C2C, NVSwitch, CDU/RCDU, cold plate, busbar, DPU, RoCE, SHARP, NIM, IRSS) on first use; the anatomy page carries Dell + NVIDIA `sources`. Wattages/timings/counts are illustrative.

## DellIR7000 — liquid-cooling digital twin (eleventh component)

Same architecture as the other twins, applied to the **Dell Integrated Rack 7000 (IR7000)** + **PowerCool** liquid cooling (OCP 2024; 33–264 kW per rack, roadmap to 480 kW). The twist versus every earlier twin: the subject is a **thermal system**, not a computer — nothing boots. The "anatomy" is the rack drawn *as a cooling loop* (CDU, supply/return manifolds, four generic IT bays under cold plates, enclosed rear-door heat exchanger, facility water, leak/flow sensors), and the "power-on" trace is the loop's **commissioning and thermal ramp** — fill, pump, verify, air door, load, balance, steady. It is the other side of the XE9712 twin's cold plate: that twin's power-on pauses at "liquid before silicon", and this twin's verify phase is what it waits for. See `DellIR7000/README.md`. Grounded in Dell's OCP-2024 announcement (IR7000/PowerCool), Dell's cooling blog, and the OCP Open Rack v3 project.

```
DellIR7000/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellIR7000/frontend/  src/{api,types}.ts, App.tsx, components/{RackView,AnatomyPage,CatalogPage,UseCasePage,ThermalControls,ThermalCounters}.tsx
DellIR7000/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellIR7000/scripts/start_all.sh` (backend :8009 background, frontend :5182 foreground — next free after XE9712's 8008/5181). Stop: `./DellIR7000/scripts/stop_all.sh`.
- Backend tests: `cd DellIR7000/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellIR7000/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8009`. Trace endpoint is `GET /api/thermal` returning `ThermalResponse`.

Key points beyond the chassis-twin pattern:

- **Thermal-domain model shapes** (`models.py`): `RackAnatomy` / `RackRegion` / **`ThermalState`** (wire shape/camelCase identical to the other twins). `RegionKind` is loop-specific: `cdu · manifold · coldplate · airdoor · power · facility · sensor` — `test_anatomy.py` asserts `kinds == EXPECTED_KINDS`, exactly one cdu/airdoor/facility/sensor/power, a supply+return manifold pair, and four same-size `coldplate` bays. `ThermalState` drops the compute telemetry entirely for `itLoadWatts` / `liquidWatts` / `airWatts` / `flowLpm`.
- **Thermal trace** (`engine.py`, pure — AST-checked): phase order `off→fill→pump→verify→airdoor→load→balance→steady` never regresses. Signature invariants (`test_engine.py`): **heat balance** — `liquid_watts + air_watts == it_load_watts` on *every* step with **no tolerance** (the twin's version of the Alienware energy identity, and its whole reason for existing); **liquid share ≥85%** whenever there is load; **flow before heat** (`flow_lpm > 0` strictly before the first watt of IT load, and flow monotonic); load monotonic to ≥200 kW; **per-branch leak/flow verification is the single longest stage** (`cycleCost` max, UI dwells); and the four bays always light together.
- **Anatomy is the loop, not the box** (`anatomy.py`, stylized 100×84 front elevation): power shelf across the top (the *input* meter — busbar watts are the heat load), four IT bays between vertical supply (left) and return (right) manifolds, the eRDHx as the far-right strip, and the plant row along the bottom — CDU, facility water, instrumentation. Bays are drawn generic on purpose: to the loop, any payload is just heat. Only visual is the self-contained, credited schematic `frontend/public/ir7000-loop.svg`.
- **Catalog (10 categories) and use cases (3) are backend data**: rack platform (IR7000 ORv3 / IR5000 19-inch), coolant distribution (in-rack RCDU / row-scale CDU), rear-door heat exchange (active eRDHx / passive coil), cold plates & leak containment, manifolds + dry-break quick disconnects + treated coolant (PG25), instrumentation, rack power, facility integration (TCS loop / heat reuse), IT payload (XE9712, XE9685L), monitoring & services. Use cases: cooling a GB200 NVL72 row, retrofitting density into a legacy air-cooled building, max-density HPC with campus heat reuse.
- Copy spells out liquid-cooling vocabulary (CDU/RCDU, ORv3, cold plate, eRDHx, quick disconnect/dry-break, PG25, degassing, TCS/FWS, warm-water economization) on first use; anatomy page carries Dell + OCP `sources`. Wattages/flows/timings are illustrative.

## DellPowerProtect — data-protection digital twin (twelfth component)

Same architecture, applied to **Dell PowerProtect Data Domain** (the purpose-built backup appliance; all-flash generation announced Sept 2025) + **PowerProtect Cyber Recovery** (air-gapped vault) + **CyberSense** (ML integrity analytics). The twist: the subject is a **data path across two sites**, so — like the CloudIQ twin — the "anatomy" is a left→right map (production estate → air gap → vault) and the "power-on" trace is the **lifecycle of the data itself**: backed up, deduplicated, replicated through a briefly-open gap, locked immutable, scanned, attacked, recovered. Closes a loop the PowerMax twin opened (its cyber-resiliency vault use case is concretely this architecture). See `DellPowerProtect/README.md`. Grounded in Dell's PowerProtect product pages, the Sept 2025 all-flash announcement, and the Data Domain family data sheet.

```
DellPowerProtect/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellPowerProtect/frontend/  src/{api,types}.ts, App.tsx, components/{SiteView,AnatomyPage,CatalogPage,UseCasePage,LifecycleControls,LifecycleCounters}.tsx
DellPowerProtect/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellPowerProtect/scripts/start_all.sh` (backend :8010 background, frontend :5183 foreground). Stop: `./DellPowerProtect/scripts/stop_all.sh`.
- Backend tests: `cd DellPowerProtect/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellPowerProtect/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8010`. Trace endpoint is `GET /api/lifecycle` returning `LifecycleResponse`.

Key points beyond the chassis-twin pattern:

- **Data-path model shapes** (`models.py`): `SiteAnatomy` / `SiteRegion` / **`LifecycleState`**. `RegionKind` is protection-specific: `workload · backup · appliance · gap · analytics · recovery · mgmt` — `test_anatomy.py` asserts `kinds == EXPECTED_KINDS`, exactly two `appliance` regions **drawn identical in size** (the vault's power is reachability, not hardware), one gap/analytics/recovery/backup, ≥2 workloads, and that **every vault region lies strictly right of the gap and every production region strictly left**. `LifecycleState` carries `logicalTb` / `storedTb` (dedupe's arithmetic) and `elapsedHours`.
- **Lifecycle trace** (`engine.py`, pure — AST-checked): phase order `idle→backup→dedupe→replicate→airgap→scan→attack→recover→restored` never regresses. Signature invariants (`test_engine.py`): **dedupe economics** — `stored_tb <= logical_tb` always, logical monotonic, ratio ≥10:1 from the dedupe phase on; **air-gap discipline** — the `gap` region is active in `replicate` and `recover` and *exactly* those two phases (both opened from the vault side); **the attack cannot reach the vault** — at the `attack` step no vault region (`dd-vault`/`cybersense`/`recovery-host`) and no gap is active while production's blast radius is; **the vaulted copy is sealed strictly before the attack**; **the CyberSense scan is the single longest stage** (`cycleCost` max); and recovery is driven from the vault side (vault + clean room + gap + prod appliance all active).
- **Catalog (9 categories) and use cases (3) are backend data**: appliances (All-Flash / DD9910 / DD3410), DDOS software (variable-length dedupe, DD Boost, Data Invulnerability Architecture), immutability & hardening (Retention Lock Compliance, root of trust), Cyber Recovery vault (software, operational air gap, clean room), CyberSense analytics + forensics, backup software (PPDM + third-party ecosystem), replication & cloud tiering, estate integration (PowerStore/PowerMax direct backup, CloudIQ AIOps), resilience services. Use cases: hospital ransomware vault, bank compliance + cyber resilience, 40 branch offices into one vault.
- Copy spells out data-protection vocabulary (deduplication, DD Boost, MTree, Retention Lock/WORM, operational air gap, CyberSense, clean room, RPO/RTO, DDOS, Cloud Tier, ROBO) on first use; anatomy page carries Dell `sources`. Only visual is the self-contained, credited schematic `frontend/public/powerprotect-vault.svg`. Capacities/ratios/timings are illustrative.

## The AI Factory quartet

Four twins model the four pillars of a Dell AI Factory and deliberately cross-reference each other; run them together to see one machine from four angles:

| Pillar | Twin | Ports | The one idea |
|---|---|---|---|
| Compute | `DellPowerEdgeXE9712/` | 8008/5181 | 72 GPUs fuse into one NVLink domain |
| Cooling | `DellIR7000/` | 8009/5182 | Heat in equals heat out, exactly |
| Data | `DellExascale/` | 8011/5184 | Metadata leaves the data path |
| Fabric | `DellPowerSwitchSN6000/` | 8012/5185 | The fabric never drops a packet |

The XE9712's power-on pauses at "liquid before silicon" — the IR7000's verify phase is what it waits for. NVLink stops at the rack wall — the SN6000 carries traffic past it. The Exascale rack's fan-out reads are the incast the SN6000's congestion control absorbs. Keep these references intact when editing any of the four.

## DellExascale — parallel-storage digital twin (thirteenth component)

Same architecture, applied to **Dell Exascale Storage** + the **Lightning File System** (the production form of Project Lightning: parallel NFS on PowerScale's OneFS with a metadata server and Flex Files layouts; Exascale unifies PowerFlex block, PowerScale/Lightning file, and ObjectScale object in one ~6 TB/s rack). The twist versus PowerStore/PowerMax: those move every byte through a controller, and that controller's ceiling is the system's. A parallel file system refuses that — the client asks the metadata server *once* where the stripes live, then reads straight from every data server at once. See `DellExascale/README.md`. Grounded in Dell's Lightning blog, Blocks & Files' Project Lightning coverage, StorageReview's GTC 2026 report, and the DTW 2026 announcements.

```
DellExascale/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellExascale/frontend/  src/{api,types}.ts, App.tsx, components/{PlatformView,AnatomyPage,CatalogPage,UseCasePage,DataControls,DataCounters}.tsx
DellExascale/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellExascale/scripts/start_all.sh` (backend :8011 background, frontend :5184 foreground). Stop: `./DellExascale/scripts/stop_all.sh`.
- Backend tests: `cd DellExascale/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellExascale/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8011`. Trace endpoint is `GET /api/datapath` returning `DataResponse`.

Key points beyond the chassis-twin pattern:

- **Parallel-storage model shapes** (`models.py`): `PlatformAnatomy` / `PlatformRegion` / **`DataState`**. `RegionKind` is data-path-specific: `client · fabric · metadata · dataserver · media · protocol · management` — `test_anatomy.py` asserts `kinds == EXPECTED_KINDS`, exactly one metadata server, four same-size dataserver+media pairs, and all three protocol engines (`protocol-file`/`-object`/`-block`). `DataState` carries `throughputGbps`, `dataServersStreaming` (0–4), and `layoutHeld`.
- **Data-path trace** (`engine.py`, pure — AST-checked): phase order `idle→mount→layout→stripe→feed→checkpoint→tier→steady` never regresses. Signature invariants (`test_engine.py`): **metadata leaves the data path** — the `metadata` region is absent from every phase in `BULK_PHASES` and active in *exactly* `{mount, layout}` (this is the twin's whole reason for existing); **layout precedes data** and is never lost mid-job; **throughput requires fan-out** — nonzero throughput implies all four servers streaming, zero servers implies zero throughput; data servers light in lockstep each with its media; peak ≥48,000 Gbps (~6 TB/s); the **checkpoint burst is the longest stage**.
- **Geometry carries the lesson** (`anatomy.py`, stylized 100×72 left→right path): clients, fabric, then the metadata server drawn *above* the data-server band with `test_anatomy.py::test_metadata_sits_off_the_data_path` pinning `mds.y + mds.h <= server.y`. Data servers run down the middle with their NVMe; the file/object/block protocol engines line the bottom. Only visual is the credited schematic `frontend/public/exascale-path.svg`.
- **Catalog (10 categories) and use cases (3)**: platform (Exascale rack / PowerScale cluster), Lightning parallel FS (+ MDS and Flex Files), data servers, media, object (ObjectScale), block (PowerFlex), client access (GPUDirect, standards-based pNFS — no proprietary kernel module), storage fabric, management (+ CloudIQ AIOps), validated designs and residencies. Use cases: feeding an eight-rack AI factory, an HPC centre replacing a legacy parallel FS, consolidating three storage silos.
- Copy spells out parallel-storage vocabulary (pNFS, layout, stripe, Flex Files, MDS, OneFS, GPUDirect, RDMA, incast, tiering) on first use. Bandwidths/timings illustrative.

## DellPowerSwitchSN6000 — AI-fabric digital twin (fourteenth component)

Same architecture, applied to the **Dell PowerSwitch SN6000** (NVIDIA Spectrum-6: 1.6 Tb/s ports, up to 409.6 Tb/s switching capacity, 2,048 breakout connections, liquid cooling and co-packaged optics options, Spectrum-X Ethernet; GA July 2026). The twist versus the E3200 twin: that one is a single campus switch booting via ONIE; this is the **fabric** several switches form — a leaf/spine topology joining GPU racks, picking up exactly where the XE9712's NVLink domain stops at the rack wall. See `DellPowerSwitchSN6000/README.md`. Grounded in Dell's SN6000 spec sheet and the March 2026 AI Factory announcement.

```
DellPowerSwitchSN6000/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellPowerSwitchSN6000/frontend/  src/{api,types}.ts, App.tsx, components/{FabricView,AnatomyPage,CatalogPage,UseCasePage,FabricControls,FabricCounters}.tsx
DellPowerSwitchSN6000/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellPowerSwitchSN6000/scripts/start_all.sh` (backend :8012 background, frontend :5185 foreground). Stop: `./DellPowerSwitchSN6000/scripts/stop_all.sh`.
- Backend tests: `cd DellPowerSwitchSN6000/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellPowerSwitchSN6000/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8012`. Trace endpoint is `GET /api/fabric` returning `FabricResponse`.

Key points beyond the chassis-twin pattern:

- **Fabric model shapes** (`models.py`): `FabricAnatomy` / `FabricRegion` / **`FabricState`**. `RegionKind` is topology-specific: `spine · leaf · endpoint · optics · telemetry · cooling · management` — `test_anatomy.py` asserts `kinds == EXPECTED_KINDS`, two spines, four leaves, four endpoints, matched leaf/endpoint counts, uniform sizing within each tier, and **tiers vertically ordered** (spines above leaves above endpoints — the geometry encodes the two-hop path). `FabricState` carries `fabricTbps`, `peakLinkPercent`, and **`droppedPackets`**, which exists to be zero.
- **Fabric trace** (`engine.py`, pure — AST-checked): phase order `off→power→linktrain→topology→ready→collective→congestion→reroute→steady` never regresses. Signature invariants (`test_engine.py`): **zero packet loss on every step** (the product claim, and this twin's reason for existing); **congestion is genuinely tested** — the congestion step must drive the busiest link ≥95%, so losslessness is proven under stress rather than asserted at idle; **adaptive routing relieves without losing work** — after the reroute the hot link is strictly cooler *and* `fabricTbps` has not fallen (98%@24 Tb/s → 71%@31 Tb/s); no traffic before links train and routing converges; spine and leaf tiers light in lockstep; any traffic crosses both tiers; **link training is the longest stage**.
- **`FabricView.tsx` derives the leaf/spine mesh from the region data** — every leaf drawn to every spine, plus each leaf down to its rack — so a bigger fabric stays data, not code. The mesh is the topology's whole point, so it must be visible.
- **Catalog (9 categories) and use cases (3)**: switch platform (SN6000 / Quantum-X800 InfiniBand), topology (leaf/spine, 1:1 non-blocking), lossless & congestion control (RoCE, ECN+PFC, adaptive routing), optics (co-packaged vs pluggable), endpoints & SuperNICs, collective acceleration (SHARP, NCCL tuning), switch cooling (liquid/air), fabric management (OS10/SONiC, validation), design services. Use cases: eight-rack training cluster fabric, storage fabric for the parallel file system, multi-tenant AI cloud.
- Copy spells out AI-networking vocabulary (leaf/spine, oversubscription, incast, RoCE, ECN, PFC, adaptive routing, CPO, SHARP, NCCL, SuperNIC) on first use. Capacities/timings illustrative.

## DellProMaxPlus — on-device inference digital twin (fifteenth component)

Same architecture, applied to the **Dell Pro Max 16 Plus** with the **Qualcomm AI 100 PC Inference Card** — the first mobile workstation with an enterprise-grade *discrete* NPU (two AI-100 NPUs, 32 AI cores, ~450 TOPS INT8, and **64 GB of dedicated on-card AI memory**). Dell demonstrated a 109-billion-parameter Llama 4 model generating text on it with no network. The twist versus every other accelerator twin here: those are stories about moving data fast, and this one is about refusing to move it. See `DellProMaxPlus/README.md`. Grounded in Dell's discrete-NPU blog and Pro Max Plus product brief, the Qualcomm Cloud AI SDK architecture docs, and arXiv 2507.00418.

```
DellProMaxPlus/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellProMaxPlus/frontend/  src/{api,types}.ts, App.tsx, components/{DeviceView,AnatomyPage,CatalogPage,UseCasePage,InferenceControls,InferenceCounters}.tsx
DellProMaxPlus/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellProMaxPlus/scripts/start_all.sh` (backend :8013 background, frontend :5186 foreground). Stop: `./DellProMaxPlus/scripts/stop_all.sh`.
- Backend tests: `cd DellProMaxPlus/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellProMaxPlus/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8013`. Trace endpoint is `GET /api/inference` returning `InferenceResponse`.

Key points beyond the chassis-twin pattern:

- **Inference-path model shapes** (`models.py`): `DeviceAnatomy` / `DeviceRegion` / **`InferenceState`**. `RegionKind` is inference-specific: `host · memory · storage · link · npu · aimemory · thermal · power · runtime` — `test_anatomy.py` asserts `kinds == EXPECTED_KINDS`, two identically-drawn NPUs, and exactly one of every other kind. `InferenceState` carries `weightsResidentGb`, `tokensPerSecond`, `npuWatts`, and **`linkGbps`**, which exists to be zero.
- **Inference trace** (`engine.py`, pure — AST-checked): phase order `off→compile→load→resident→prefill→decode→sustained→offline` never regresses. Signature invariants (`test_engine.py`): **the weights cross the link exactly once** — `linkGbps > 0` during the `load` phase and no other, the twin's reason for existing; **never evicted** — `weightsResidentGb` monotonic to 61 GB and pinned there (no paging is what makes the thousandth token as predictable as the first); **the host is idle during generation** — no `host`/`memory`/`storage` region active once tokens flow, the counterpart to Exascale's "metadata leaves the data path"; **sustained power never throttles** (within 10% of peak from first decode — the discrete-NPU claim versus a laptop GPU); **disconnecting the network changes nothing** (the final step is a deliberate non-event); and **model load is the longest stage** (unique max `cycleCost`, cost paid per model not per prompt).
- **Geometry carries the lesson** (`anatomy.py`, stylized 100×54 map built around one boundary): host CPU / system DRAM / NVMe on the left, a narrow PCIe strip in the middle, two AI-100s and the 64 GB pool on the right. `test_anatomy.py::test_the_boundary_is_drawn_and_the_sides_are_separate` pins every host-side region strictly left of the strip and every card-side region strictly right; the AI memory must span both NPUs and be the biggest block on the card, because capacity — not TOPS — decides which models run. `DeviceView.tsx` derives the dashed weights path from region *kinds*, and draws it heavy only while the link is busy.
- **Catalog (10 categories) and use cases (3)**: platform, discrete NPU card, host processor, system memory, model library, other accelerators on board (integrated NPU vs workstation GPU — the honest contrast), toolchain (ONNX → hardware container, quantization, Dell Pro AI Studio), models that fit, thermal and power, deployment/security. Use cases: regulated case review on material that cannot leave the building, an agent dev loop with no metered API, and a disconnected field engineer.
- Copy spells out on-device-inference vocabulary (NPU, TOPS, FP16, quantization, ONNX, prefill/decode, KV cache, mixture-of-experts) on first use, and is explicit that the 64 GB / ~120B pairing implies ~4-bit weight quantization — Dell's FP16 claim is about the arithmetic, not the storage, and only the storage decision makes the model fit. Cross-references the GPU twin (decode *is* its memory-bound roofline regime), the Alienware twin (laptop power path), and the datacenter quartet. Wattages/rates/timings illustrative.

## DellPowerFlex — software-defined storage digital twin (sixteenth component)

Same architecture, applied to **Dell PowerFlex** (5.0 Ultra — scalable availability engine, erasure coding): shared block storage assembled out of ordinary servers' local NVMe, running over ordinary IP, scaling 3 → 2,000+ nodes and past 240 million IOPS. The third storage twin here, and the one that argues with the other two — PowerStore and PowerMax are controller architectures, and this is what happens when you delete the controller. See `DellPowerFlex/README.md`. Grounded in Dell's PowerFlex product page and rebuild technical overview, WWT's 5.0 Ultra write-up, and Dell's May 2026 data-center announcement.

```
DellPowerFlex/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellPowerFlex/frontend/  src/{api,types}.ts, App.tsx, components/{ClusterView,AnatomyPage,CatalogPage,UseCasePage,ClusterControls,ClusterCounters}.tsx
DellPowerFlex/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellPowerFlex/scripts/start_all.sh` (backend :8016 background, frontend :5189 foreground). Stop: `./DellPowerFlex/scripts/stop_all.sh`.
- Backend tests: `cd DellPowerFlex/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellPowerFlex/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8016`. Trace endpoint is `GET /api/cluster` returning `ClusterResponse`.

Key points beyond the chassis-twin pattern:

- **Pool model shapes** (`models.py`): `ClusterAnatomy` / `ClusterRegion` / **`ClusterState`** (names deliberately mirror the VxRail twin's — both subjects are clusters; the apps are independent). `RegionKind` is pool-specific: `client · network · coordinator · node · protection · management` — `test_anatomy.py` asserts `kinds == EXPECTED_KINDS`, six identically-drawn nodes, and exactly one of every other kind. `ClusterState` carries `nodesOnline`, `iopsThousands`, `protectedPercent`, and **`rebuildParticipants`**, the field the twin exists for.
- **Cluster trace** (`engine.py`, pure — AST-checked): phase order `off→cluster→pool→volumes→io→failure→rebuild→rebalanced→steady` never regresses. Signature invariants (`test_engine.py`): **every surviving node rebuilds** — `rebuildParticipants == nodesOnline` during rebuild, never a subset, which is why recovery gets *faster* as the pool grows (in a controller array this number is 1 at any scale); **no node is privileged** — the lit node set is always empty, all six, or all five survivors; **the failed node never comes back** (recovery is redistribution, not replacement); **service survives the failure** — I/O never stops and never falls below 70% of steady, so there is no failover pause to find; **protection dips and fully returns** (may fall, may not settle anywhere but 100) and recovers monotonically; **the coordinator is absent from the steady data path** — the metadata manager hands out the chunk map and goes dark.
- **The `cycleCost` pattern is deliberately inverted.** Every other twin dwells on a recovery-ish stage (R760 memory training, SN6000 link training, Pro Max Plus model load). Here `test_building_the_pool_is_the_longest_stage_not_repairing_it` pins the unique max on the initial scatter *and* asserts rebuild costs strictly less — the scatter is slow so the repair can be fast, which is the product claim.
- **Geometry carries the lesson** (`anatomy.py`, stylized 100×55 map): clients across the top, IP fabric, then a band of six identical servers — and no controller row, because there is no controller. `test_the_coordinator_is_the_smallest_thing_in_the_picture` pins the metadata manager smaller than any node (drawing it large would tell the reader something false about where bytes go), and `test_there_is_no_tier_between_clients_and_nodes` forbids anything but the fabric in that gap. `ClusterView.tsx` derives two link sets from region *kinds*: client-to-node paths always, and the many-to-many node-to-node recovery mesh only while rebuilding.
- **Catalog (9 categories) and use cases (3)**: storage nodes, deployment topology (two-layer / hyperconverged / **mixed in one pool** — the option that justifies the architecture), protection (mesh mirroring, erasure coding, fault sets), network fabric, client access (SDC vs NVMe/TCP), metadata management, data services, lifecycle, platform integration. Use cases: consolidating a database estate that cannot pause, a container platform growing a node at a time, and replacing every server without a migration project.
- Copy spells out software-defined-storage vocabulary (SDS, SDC, metadata manager, mesh mirroring, erasure coding, fault set, two-layer vs hyperconverged) on first use. Cross-references PowerStore/PowerMax (the controller architectures it argues with), VxRail (hyperconverged), Exascale (PowerFlex is that rack's block tier), SN6000 (the fabric is part of the storage design), PowerProtect (replication is not a backup), and CloudIQ. IOPS/timings illustrative.

## DellCyberDetect — ransomware-detection digital twin (seventeenth component)

Same architecture, applied to **Dell Cyber Detect** — machine-learning ransomware detection running directly against snapshots on primary storage, inspecting data at the **byte level** rather than reasoning about metadata, file activity, or signatures (content analysis by Index Engines; Dell states 99.99% accuracy across thousands of variants; PowerStore Q3 2026, PowerMax 2H 2026). The companion to the PowerProtect twin: that one models the isolated vault and answers "will a copy survive?", and this one answers the question isolation leaves open — *which copy?* See `DellCyberDetect/README.md`.

```
DellCyberDetect/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellCyberDetect/frontend/  src/{api,types}.ts, App.tsx, components/{TimelineView,AnatomyPage,CatalogPage,UseCasePage,DetectControls,DetectCounters}.tsx
DellCyberDetect/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellCyberDetect/scripts/start_all.sh` (backend :8019 background, frontend :5192 foreground). Stop: `./DellCyberDetect/scripts/stop_all.sh`.
- Backend tests: `cd DellCyberDetect/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellCyberDetect/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8019`. Trace endpoint is `GET /api/detect` returning `DetectResponse`.

Key points beyond the chassis-twin pattern:

- **Detection model shapes** (`models.py`): `DetectAnatomy` / `DetectRegion` / **`DetectState`**. `RegionKind` is detection-specific: `array · snapshot · inspect · classifier · models · verdict · recovery` — `test_anatomy.py` asserts `kinds == EXPECTED_KINDS`, seven uniformly-drawn snapshots, and exactly one of every other kind. `DetectState` carries `snapshotsCorrupted`, `contentConfidencePercent`, **`metadataAlerts`** (exists to be zero) and **`lastCleanSnapshot`** (`-1` until the verdict — the deliverable).
- **The first adversarial twin in this repo.** Every other twin's invariant holds because the system is working; here `metadataAlerts == 0` holds because the system is being *fooled*. `test_metadata_detection_is_blind_while_corruption_spreads` asserts both halves — corruption demonstrably present *and* alerts at zero — because silence proves nothing unless damage is happening.
- **Detection trace** (`engine.py`, pure — AST-checked): phase order `clean→intrusion→encrypt→blind→inspect→classify→verdict→recover→restored` never regresses. Other signature invariants: **confidence comes only from reading content** (zero until inspection has run); **the deliverable is a date, not an alert** (`lastCleanSnapshot` unset before the verdict, named after); **the named copy is actually clean** — strictly older than the first corrupted snapshot, since a false negative here is somebody restoring the attack from a copy the product certified; **no verdict without evidence**; **recovery uses the copy the verdict named**; **content inspection is the longest stage** (unique max `cycleCost` — reading every byte is expensive and that expense *is* the product).
- **Geometry carries the lesson** (`anatomy.py`, stylized 100×58): unlike every other map here, the middle band is an axis of **time** — seven snapshots left to right, oldest to newest, pinned by `test_the_middle_band_is_a_timeline` (uniform size, one row, strictly increasing x). `test_evidence_sits_above_conclusion` puts inspection/classifier/corpus above verdict/recovery, mirroring the engine's ordering constraint in space.
- **`TimelineView.tsx` takes a `revealed` prop** — corrupted snapshots are drawn identically to clean ones until content analysis has run. Pausing on the blind step shows a timeline the viewer genuinely cannot read, which is the administrator's actual position. Marking corruption early would quietly undo the whole lesson; keep this behavior if you touch the component.
- **Catalog (8 categories) and use cases (3)**: where detection runs (primary array / backup appliance / inside the vault — placement first, because it sets how early an answer is possible), detection method, the trained model and its error budget (the false negative is the expensive error), what the analysis produces, snapshot frequency and retention (if dwell time exceeds retention there is no clean copy to find), immutability and isolation, estate coverage, operations. Use cases: a manufacturer choosing between last night and last month, a bank that must prove when it started, a hospital for which the over-cautious month-old restore is not clinically viable.
- Copy spells out cyber-recovery vocabulary (dwell time, entropy, false negative, immutability, RPO, forensic report) on first use, and labels the 99.99% figure as Dell's own. Cross-references PowerProtect (the vault half — the two are designed to be read together), PowerStore/PowerMax (where it runs), and CloudIQ (getting the verdict to a human). Counts/timings illustrative.

## DellFortZero — zero-trust digital twin (eighteenth component)

Same architecture, applied to **Dell Project Fort Zero** — Dell's turnkey zero-trust private cloud, which in April 2025 completed the US Department of Defense's assessment for **Target Level** validation as a sovereign, on-premises deployment, tested against sophisticated attack. See `DellFortZero/README.md`.

```
DellFortZero/backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
DellFortZero/frontend/  src/{api,types}.ts, App.tsx, components/{PillarView,AnatomyPage,CatalogPage,UseCasePage,AccessControls,AccessCounters}.tsx
DellFortZero/scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./DellFortZero/scripts/start_all.sh` (backend :8022 background, frontend :5195 foreground). Stop: `./DellFortZero/scripts/stop_all.sh`.
- Backend tests: `cd DellFortZero/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd DellFortZero/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8022`. Trace endpoint is `GET /api/access` returning `AccessResponse`.

Key points beyond the chassis-twin pattern:

- **This twin inverts the repo's dominant idiom.** Every other map here carries its lesson in a *boundary* — the Pro Max Plus PCIe strip, the PowerProtect air gap, the PowerFlex gap between client and node bands. Fort Zero carries its lesson in the absence of one, and `test_nothing_is_drawn_as_a_perimeter` caps every region at 40% of the map's width and height so no shape can act as an enclosure. There is a centre and no inside.
- **Zero-trust model shapes** (`models.py`): `ZeroTrustMap` / `Pillar` / **`AccessState`** (named `Map`/`Pillar` rather than `Anatomy`/`Region` for the same reason the iDRAC twin uses `SubsystemMap`/`Block` — the subject is a decision architecture, not an object). `RegionKind` is the **US DoD reference architecture's seven pillars** plus the policy engine: `identity · device · network · workload · data · visibility · automation · policy`. `AccessState` carries `resourcesReachable`, `trustScore`, `verifications`, `trustTtlSeconds`, and **`implicitTrustGrants`**, which exists to be zero.
- **Access trace** (`engine.py`, pure — AST-checked): phase order `idle→request→verify→context→decide→grant→monitor→expire→breach→contained` never regresses. Signature invariants: **nothing is ever trusted implicitly**; **network location never authorizes** (the `context` step considers the network pillar and still reaches zero resources — in a perimeter model that step *is* the authorization); **the breach reaches nothing**, with `test_the_breach_is_actually_inside` checking the attacker genuinely holds the position a perimeter would have honoured, so the claim is tested rather than asserted; **verification is continuous, not once**; **trust is a lease, not a property** (a grant carries a TTL, and outside a grant there is no lease at all); **least privilege is literal** (≤1 resource, ever); **all seven pillars feed the decision** (the model is an architecture, not a menu — a gap in any pillar is a route around all of them); **the policy engine is consulted on every active step**; and **continuous monitoring is the longest stage** — the honest location of zero trust's cost is not the login, it is the never stopping.
- **Geometry** (`anatomy.py`, stylized 100×72): seven co-equal pillars around a central policy engine. `test_the_pillars_are_co_equal` requires all seven identical in size (a diagram making one larger would be arguing with the reference architecture — the policy engine matches them too, since it decides *using* the pillars rather than outranking them), and `test_the_policy_engine_is_the_centre` puts the decision point closer to the map centre than anything else. `PillarView.tsx` derives spokes from each pillar to the policy engine and lights them only when both ends are active, so the `decide` step visibly draws on all seven at once. Do **not** add a ring or enclosing shape for visual tidiness; it would reverse the argument.
- **Catalog (8 categories) and use cases (3)**: the categories are the DoD's pillars rather than a product line, and there is deliberately no perimeter category. Use cases: a sovereign environment that must assume it is already breached, a manufacturer whose suppliers need access but not trust, and an enterprise whose perimeter stopped existing years ago. The catalog is honest about the two ways adoptions actually fail — policy-engine latency (people route around it and the exceptions become permanent) and alert volume (more alerts than anyone reviews converts a security control into a compliance artefact).
- Copy spells out zero-trust vocabulary (policy decision/enforcement point, microsegmentation, lateral movement, least privilege, posture, SIEM/SOAR, Target Level) on first use. Cross-references iDRAC (hardware root of trust), PowerProtect (isolation) and Cyber Detect (integrity) as the three distinct questions people confuse: who may reach data, does a copy survive, and is the copy intact. Scores/counts/timings illustrative.

## Loop-driven twin discovery

`LOOP_LOG.md` tracks a self-paced loop that researches untwinned Dell products, picks the three most interesting per iteration, specs all three, and fully builds one. Iteration 1 built `DellProMaxPlus/` and left specs at `DellNativeEdge/initial_spec.md` (8014/5187) and `DellAIDataPlatform/initial_spec.md` (8015/5188). Iteration 2 built `DellPowerFlex/` and left specs at `DellTelecomBlocks/initial_spec.md` (8017/5190) and `DellObjectScale/initial_spec.md` (8018/5191). Iteration 3 built `DellCyberDetect/` and left specs at `DellPowerEdgeXE7745/initial_spec.md` (8020/5193) and `DellAutomationStudio/initial_spec.md` (8021/5194). Iteration 4 built `DellFortZero/` and left specs at `DellPowerScale/initial_spec.md` (8023/5196) and `DellCircularDesign/initial_spec.md` (8024/5197). Read `LOOP_LOG.md` before adding a twin so a later iteration does not re-pick a product, and update it (picks, ports, next-iteration exclusions) when one lands.
