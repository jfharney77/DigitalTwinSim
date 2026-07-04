# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

The app is implemented as a **Python/FastAPI backend + React/Vite/TypeScript frontend**. The spec's three-layer design is split across the wire: the **backend owns the pure deterministic engine**, and the **frontend fetches the full `SimState[]` trace and animates it on its own clock**.

Reference files:
- `initial_spec.md` — the authoritative design + roadmap (data models, invariants, scope).
- `gpu-sim.html` — the original single-file reference implementation (inline SVG + vanilla JS). It is the **behavior oracle** — open it in a browser to compare behavior. Not the architecture; see "Oracle vs. spec" below.

### Layout & commands

```
backend/   app/{models,profiles,mapping,engine,main}.py + tests/
frontend/  src/{api,types}.ts, components/, App.tsx
scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run everything: `./scripts/start_all.sh` (backend :8000 background, frontend :5173 foreground). Stop: `./scripts/stop_all.sh`.
- Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8000`.

### Where things live (maps spec's `src/` layout onto the split)

- `model/` → `backend/app/models.py` (pydantic `GpuProfile`/`Workload`/`SimState`, camelCase JSON) + `profiles.py`.
- `sim/` → `backend/app/engine.py` (`simulate(profile, workload) -> list[SimState]`, plus `analyze(...) -> Summary` for the roofline read-out) + `mapping.py`. **Keep this pure** — no FastAPI/IO imports, so the trace tests stay fast. Tiling (spec_03): the load/compute/writeback phases repeat per tile; `Workload.tile_size` of `0` or `>=N` means one tile = the whole matrix, which reproduces the original single-LOAD trace exactly (this is why the spec_01 tests still pass). `SimState.tile_row/tile_col/k_tile` carry tile context. Bandwidth model (spec_04): each LOAD stays one state with `stalled=True` and a `cycle_cost` (bytes/`bytes_per_cycle`); the **UI dwells** on costly loads instead of the trace emitting per-cycle states. `analyze()` returns the memory- vs compute-bound `regime` (intensity vs ridge point); it's illustrative, not cycle-accurate.
- `render/` → `frontend/src/components/DieView.tsx` (profile-driven SVG, painted from `SimState.coreState`) + `MatrixPanels.tsx` (A/B/C grids with tiling overlays). Operands come from `backend/app/matrices.py` (`make_operands`, deterministic) and ride in the simulate response as `a`/`b`. With tiling, C fills in tile-by-tile, so `MatrixPanels` replays the trace up to the cursor to compute each cell's accumulation depth (not a single global `k`).
- `ui/` → `Controls.tsx` / `Counters.tsx` / `Legend.tsx`.
- **Die-anatomy page** (second tab, deep-linkable via `/#anatomy/<dieId>`) → `backend/app/anatomy.py` (annotated floorplans of real GPUs as data — regions in a normalized coordinate space, stats, vendor whitepaper/die-shot sources, and per-region `Photo`s hotlinked from Wikimedia Commons whose `credit` line the UI must always render; geometry invariants in `tests/test_anatomy.py`) + `frontend/src/components/AnatomyPage.tsx` / `AnatomyView.tsx` (data-driven SVG renderer; new dies are backend data, not frontend code). Layouts are stylized mental models traced from vendor diagrams, not mm²-accurate. **Both pages use the Dell clean-design skin** (light, Roboto, Dell blue) scoped under `.app.dell` + `body.dell-body` in `styles.css` — per the `dell-clean-design` skill: no eyebrow text, no step numbers, no divider rules, no highlighted text, no serifs. Page chrome is light; the die schematic, matrix panels, and anatomy floorplan stay dark — they are the diagrams, and their palette lives in the `:root` vars. Keep new page-chrome styles inside the `.app.dell` scope.
- `app.ts` → `frontend/src/App.tsx` — composition root; **owns the playback clock** (the `setInterval` lives here, never in the engine).

### Cross-cutting gotcha

`models.py` uses a camelCase alias generator, but `cores_per_sm` would camelize to `coresPerSm` — it has an explicit `alias="coresPerSM"` to match the spec/TS. If you add a field whose camelCase is ambiguous (embedded numbers/acronyms), verify the JSON key matches `frontend/src/types.ts` by hand.

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

Enforced by `backend/tests/test_engine.py` — keep them green:

- **The clock lives in the frontend, never in the engine.** No timers in `engine.py`/`SimState`; the `setInterval` is in `App.tsx`. The trace is pure data.
- Phases follow `idle→load→compute→writeback→done`; with tiling the `load→compute→writeback` cycle repeats once per output tile (so phase order is only monotonic within the single-tile / whole-matrix case).
- `macDone <= macTotal` and is monotonic non-decreasing; at `done` `macDone === N*N*N === macTotal`, for every tile size.
- `activeCores <= totalCores`, where `totalCores = sm.rows*sm.cols * coresPerSM.rows*coresPerSM.cols`.
- `utilization === activeCores / totalCores`.
- Cell→core mapping is **tile-aware** (`mapping.tile_aware_core`): a whole output tile is assigned to one SM (tiles round-robin across SMs by linear index), and each cell maps to a lane *within that SM*. A tile never straddles two SMs — they don't share memory. The legacy global round-robin `core = (i*N + j) % totalCores` (`cell_to_core`) is retained for reference only; it could scatter one tile across several SMs.
- Changing N refetches the trace and resets the cursor; Step advances exactly one state; Speed retunes the interval live.

## Testing approach (spec §8)

Test the engine against full-trace assertions (the invariants above), not the HTTP layer. The engine is pure precisely so these tests need no server or DOM. Add cases when you touch phase logic or mapping.

## Scope guardrails (spec §1)

Not a cycle-accurate simulator; timing is illustrative. Not tied to any vendor ISA — "SM", "CUDA core", "warp" are generic vocabulary. Renders tens to low-hundreds of elements, not real GPU-scale tensors. Favor a correct *mental model* over correct numbers. See spec §7 for the roadmap (M×K×N generalization, tiling, tensor-core/systolic mode) before adding features.
