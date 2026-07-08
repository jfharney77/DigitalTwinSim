# PowerSwitch E3200-ON Inside

Interactive web app that visualizes the **Dell PowerSwitch E3200-ON Series** —
a 1RU open-networking edge switch — as a digital twin. It shows the switch
booting from AC to line-rate forwarding, its internal architecture, its models
and options, and the deployments it's built for. The sixth component in the
DigitalTwinSim family (GPU, PowerEdge R760, PowerStore, Alienware, iDRAC, and
now this switch).

## Architecture

Same as the R760/PowerStore chassis twins: a Python/FastAPI backend owns the
**deterministic boot engine** and all content as data; the React frontend
fetches the `BootState[]` trace and animates it on its own clock (the UI owns
the clock — a core spec invariant).

```
backend/   FastAPI + pure engine
  app/
    models.py    ChassisAnatomy, ChassisRegion, BootState (pydantic; camelCase JSON)
    anatomy.py   the 1RU switch floorplan (regions in a normalized space)
    engine.py    pure simulate() -> BootState[]  (AC → line-rate forwarding)
    catalog.py   models, NOS, PoE, uplinks, power, cooling, management
    usecases.py  deployment scenarios (Wi-Fi edge, PoE access, fiber distribution)
    main.py      FastAPI: /api/health, /api/anatomy, /api/boot, /api/catalog, /api/usecases
  tests/         trace + geometry + catalog invariant tests

frontend/  React + Vite + TypeScript, Dell clean-design skin
  src/
    api.ts, types.ts
    components/  ChassisView (SVG), AnatomyPage, CatalogPage, UseCasePage,
                 BootControls, BootCounters
    App.tsx      composition root; owns the playback clock

scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

## Run it

```bash
./scripts/start_all.sh      # backend :8005 (background) + frontend :5178 (foreground)
./scripts/stop_all.sh       # stop both
```

Open http://localhost:5178. Vite proxies `/api` to the backend on :8005.
Ports are offset from the other twins (GPU 8000/5173 … iDRAC 8004/5177) so all
six run together.

## Develop

```bash
cd backend && . .venv/bin/activate && python -m pytest -q   # backend tests
cd frontend && npm run build                                 # typecheck / build
```

## Pages

- **Boot** — the switch coming up from AC to forwarding: standby → CPU → ONIE
  → network OS (OS10 / SONiC) → ASIC programming → ports/PoE → line rate,
  animated over the floorplan.
- **Inside the switch** — the annotated top-down floorplan: access ports, PoE
  subsystem, switching ASIC, control-plane CPU, uplinks, fans, PSUs.
- **Components & options** — the three models and their PoE / uplink / power /
  OS / management choices.
- **Use cases** — Wi-Fi 6E/7 campus edge, enterprise PoE access floor, fiber
  branch distribution.

Content is grounded in the Dell PowerSwitch E3200-ON spec sheet (Aug 2024) and
Dell's OS10/SONiC/ONIE docs (see the Sources panel on the anatomy page).
Timings and wattages are illustrative, not measured.
