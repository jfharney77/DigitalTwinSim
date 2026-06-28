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
    profiles.py  default dies (Generic-128, Generic-512)
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

The original single-file reference implementation is preserved as
[`gpu-sim.html`](gpu-sim.html) (open directly in a browser) and serves as the
behavior oracle.
