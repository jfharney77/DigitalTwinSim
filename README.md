# GPU Matmul Visualizer

Interactive web app that draws the inner structure of a GPU and animates how a
matrix multiplication executes across it. Teaching/visualization tool — see
[`initial_spec.md`](initial_spec.md) for the full design and roadmap.

## Architecture

A Python/FastAPI backend owns the **deterministic simulation engine**; the React
frontend fetches the full `SimState[]` trace and animates it on its own clock
(the UI owns the clock — a core spec invariant).

```
backend/   FastAPI + pure engine
  app/
    models.py    GpuProfile, Workload, SimState (pydantic; camelCase JSON)
    profiles.py  default dies (Generic-128, Generic-512, RTX-4060-Laptop)
    mapping.py   output cell -> physical core (round-robin)
    engine.py    pure simulate(profile, workload) -> SimState[]
    main.py      FastAPI: /api/health, /api/profiles, /api/simulate
  tests/         trace-based invariant tests (spec §8)

frontend/  React + Vite + TypeScript
  src/
    api.ts            fetch profiles + trace
    types.ts          mirrors backend models
    components/       DieView (SVG), Controls, Counters, Legend
    App.tsx           composition root; owns the playback clock

scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

Data flow: `Controls → POST /api/simulate → trace: SimState[] → DieView`.

## Run it

```bash
./scripts/start_all.sh      # backend (background) + frontend (foreground)
# or individually:
./scripts/start_backend.sh  # FastAPI on :8000
./scripts/start_frontend.sh # Vite dev server on :5173
./scripts/stop_all.sh       # stop both
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the backend on
:8000.

## Develop

```bash
# Backend tests (from backend/, venv active)
cd backend && python -m pytest -q

# Frontend typecheck / build
cd frontend && npm run build
```

## API

- `GET  /api/health` → `{"status":"ok"}`
- `GET  /api/profiles` → `GpuProfile[]`
- `GET  /api/profiles/default` → `GpuProfile`
- `POST /api/simulate` `{profile, workload}` → `{profile, workload, totalCores, macTotal, trace}`

## Live CUDA co-browsing

The third tab (`#live`) shows real CUDA activity on this machine's RTX 4060
Laptop GPU: instrumented lessons (`GPU/cuda/lessons/`, `make run-NN` or
`make watch-NN`) light the SMs the hardware scheduler actually chose; a
per-SM Gantt shows block residency; shift-click two timeline chips to
compare runs; "▶ Guided lessons" plays the narrated, GPU-free tour. Capture
tiers: `twinprobe.cuh` (placement + timing), `twin-sampler` (telemetry;
`--once` for scripts), `twin-run <any-cuda-app>` (CUPTI, timing-only).
Recordings are replayable, downloadable, and deletable;
`scripts/prune_sessions.sh` clears ad-hoc ones.

API (events from `cuda/twinprobe.cuh` and `cuda/twin-sampler`):

- `POST /api/live/ingest` `ProbeEvent` → `LiveState` (auto-starts an ad-hoc session; 409 past the 100k-event cap)
- `GET  /api/live/stream` → Server-Sent Events of `LiveState`; `GET /api/live/latest` → the current frame, SSE-free
- `POST /api/live/session` / `DELETE /api/live/session` — start/stop a named recording
- `GET  /api/live/sessions?limit=N` (newest first) → `SessionInfo[]`; per session: `/trace` (replayed frames), `/summary` (kernel stats), `/download` (raw JSONL), `/events.csv`, `DELETE` (409 while recording), `PATCH {name}` (rename)
- `POST /api/live/import` `{name, jsonl}` — save an uploaded recording (validated by full replay first)
- `GET  /api/measurements` → latest calibration per metric, with history
- `GET  /api/tour` + `/api/tour/recordings/{lessonId}` — the guided lessons (deep link: `#live/tour`)

Replay keyboard shortcuts: **space** pauses/resumes, **←/→** step the cursor;
speed buttons 0.5×–4×. No GPU? `./scripts/demo_feed.py` replays a golden
lesson recording through real ingest so the whole Live tab works untouched.

The original single-file reference implementation is preserved as
[`gpu-sim.html`](gpu-sim.html) (open directly in a browser) and serves as the
behavior oracle.

## Co-browse changelog (specs 07–21)

| Spec | Delivered |
|---|---|
| 07 | RTX 4060 Laptop profile + AD107 data; per-SM density rendering |
| 08 | Live CUDA tab: pure fold + SSE, `twinprobe.cuh` (%smid), `twin-sampler`, replayable sessions |
| 09 | Seven-lesson CUDA curriculum + Makefile + GPU-free probe-contract tests |
| — | Hardening: collision-proof ids, dim validation, truncation flags, SSE drop counts |
| 10 | Per-SM block-residency Gantt with straggler marker |
| 11 | Diff mode (shift-click two chips); frame-key pinning |
| 12 | Device-agnostic sessions via `device_info` |
| 13 | `make watch-NN` — save → see |
| 14 | Mid-kernel streaming (pinned memory, `kernel_progress`) |
| 15 | Measured roofline: lesson 06 calibrates the sim |
| 16 | Declared sampling for huge grids (`~` estimates) |
| 17 | CUPTI injection (`twin-run`, timing-only, labeled) |
| 18 | Guided lesson tours, provenance-labeled, GPU-free |
| 19 | Twenty small wins: latest/delete/download/CSV-less… see `spec_19` |
| 20 | Twenty more: summary/import/rename/history/deltas… see `spec_20` |
| 21 | Round three: sim/anatomy/a11y/robustness… see `spec_21` |
| — | The wider fleet: H100-SXM / B300-Blackwell-Ultra / RTX-5090 / MI300X sim profiles, GB300 + GB202 + MI300X die anatomies, lesson 07 (`07_bigger_dies.cu`, "the die is a parameter") with H100 + Blackwell-Ultra tour recordings |
| 22–31 | The review round, built in dependency order: rectangular M×K×N, occupancy model, `llm_decode` (KV-cache roofline), tensor-core/MMA mode (fp8/fp4), power & energy ledger, two-GPU NVLink scale-up, fleet replay (modeled-placement labels), cross-tab atlas + die compare, reading levels everywhere (registry 8→63), and the `make verify-hardware` campaign tooling |
