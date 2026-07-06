# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo layout: one directory per simulated component

The repo is organized by hardware component. `GPU/` holds the GPU digital twin (everything below); `DellPowerEdgeR760/` and `DellPowerStore/` are the second and third components, following the same pattern (see their sections at the end of this file); future components (CPU, NIC, memory hierarchy, ...) get sibling top-level directories following the same pattern: a pure-engine FastAPI `backend/`, a React/Vite `frontend/` in the Dell clean-design skin, `scripts/`, and numbered `spec_NN_*.md` files driving the work.

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
