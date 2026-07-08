# iDRAC9 Inside

Interactive web app that visualizes the **iDRAC9 baseboard management
controller** — the always-on service processor embedded in every PowerEdge
server — as a digital twin. It shows what wakes up *before* the server does:
iDRAC's own firmware bring-up, its internal architecture, its licensed
capabilities, and the management scenarios it enables. The fifth component in
the DigitalTwinSim family, alongside the GPU, PowerEdge R760, PowerStore, and
Alienware twins, and the natural companion to the R760 power-on twin (iDRAC is
the "brain" that orchestrates that boot).

## Architecture

Same as the R760 twin: a Python/FastAPI backend owns the **deterministic
bring-up engine** and all content as data; the React frontend fetches the
`BringUpState[]` trace and animates it on its own clock (the UI owns the
clock — a core spec invariant).

```
backend/   FastAPI + pure engine
  app/
    models.py    SubsystemMap, Block, BringUpState (pydantic; camelCase JSON)
    anatomy.py   the iDRAC9 block diagram (blocks in a normalized space)
    engine.py    pure simulate() -> BringUpState[]  (AC → ready controller)
    catalog.py   license tiers + capabilities (Basic/Express/Enterprise/Datacenter)
    usecases.py  management scenarios (lights-out deploy, fleet, telemetry)
    main.py      FastAPI: /api/health, /api/anatomy, /api/bringup, /api/catalog, /api/usecases
  tests/         trace + geometry + catalog invariant tests

frontend/  React + Vite + TypeScript, Dell clean-design skin
  src/
    api.ts, types.ts
    components/  BlockView (SVG), AnatomyPage, CatalogPage, UseCasePage,
                 BringUpControls, BringUpCounters
    App.tsx      composition root; owns the playback clock

scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

## Run it

```bash
./scripts/start_all.sh      # backend :8004 (background) + frontend :5177 (foreground)
./scripts/stop_all.sh       # stop both
```

Open http://localhost:5177. Vite proxies `/api` to the backend on :8004.
Ports are offset from the other twins (GPU 8000/5173, R760 8001/5174,
PowerStore 8002/5175, Alienware 8003/5176) so all five run together.

## Develop

```bash
cd backend && . .venv/bin/activate && python -m pytest -q   # backend tests
cd frontend && npm run build                                 # typecheck / build
```

## Pages

- **Bring-up** — iDRAC's own boot from AC standby to a ready, watching
  controller, animated over the block diagram (the host stays powered off).
- **Inside the controller** — the annotated block diagram: SoC, memory/flash,
  sideband buses, management NIC, remote-presence engines, Root of Trust.
- **Capabilities & options** — the license tiers and what each unlocks.
- **Use cases** — lights-out OS deployment, zero-touch fleet provisioning,
  predictive telemetry at scale.

Content is grounded in Dell's iDRAC9 documentation (see the Sources panel on
the anatomy page); timings and wattages are illustrative, not measured.
