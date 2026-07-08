# VxRail Inside

Interactive web app that visualizes **Dell VxRail** — Dell's hyperconverged
infrastructure (HCI) system, jointly engineered with VMware — as a digital
twin. The eighth component in the DigitalTwinSim family, alongside the GPU,
PowerEdge R760, PowerStore, Alienware, iDRAC, PowerMax, and PowerSwitch E3200
twins.

The twist versus every earlier twin: the subject is a **cluster**, not a
single box. VxRail is built from identical PowerEdge-based nodes whose local
NVMe drives are pooled by VMware vSAN into one shared datastore, and managed
for their whole life by VxRail Manager. So the shared "anatomy" is a stack of
identical HCI nodes plus the top-of-rack fabric that joins them, and the
"power-on" trace is the cluster's **first run** — several nodes booting in
lockstep, electing a primary that runs VxRail Manager, then fusing their local
NVMe into one vSAN datastore.

## Architecture

Same as the chassis twins: a Python/FastAPI backend owns the **deterministic
first-run engine** and all content as data; the React frontend fetches the
`FirstRunState[]` trace and animates it on its own clock (the UI owns the
clock — a core project invariant).

```
backend/   FastAPI + pure engine
  app/
    models.py    ClusterAnatomy, ClusterRegion, FirstRunState (pydantic; camelCase JSON)
    anatomy.py   a four-node cluster floorplan (regions in a normalized space)
    engine.py    pure simulate() -> FirstRunState[]  (powered-on nodes → serving VMs)
    catalog.py   node platforms, vSAN architecture, fabric, software, topology (14 categories)
    usecases.py  VDI, edge/ROBO, and VMware Cloud Foundation builds
    main.py      FastAPI: /api/health, /api/anatomy, /api/firstrun, /api/catalog, /api/usecases
  tests/         trace + geometry + catalog invariant tests

frontend/  React + Vite + TypeScript, Dell clean-design skin
  src/
    api.ts, types.ts
    components/  ClusterView (SVG), AnatomyPage, CatalogPage, UseCasePage,
                 FirstRunControls, FirstRunCounters
    App.tsx      composition root; owns the playback clock
    public/vxrail-cluster.svg  self-contained schematic (not a Dell product image)

scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

## Run it

- Everything: `./scripts/start_all.sh` (backend :8006 background, frontend :5179 foreground). Stop: `./scripts/stop_all.sh`.
- Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
- Frontend build/typecheck: `cd frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8006`. If :8006 is taken, run the backend elsewhere and point Vite at it: `API_TARGET=http://localhost:8016 npm run dev`.

Ports are offset from the other twins (GPU 8000/5173, R760 8001/5174,
PowerStore 8002/5175, Alienware 8003/5176, iDRAC 8004/5177, PowerMax /
PowerSwitch 8005/5178) so this app runs alongside them.

## The four pages

- **First run** (`/`) — play the cluster bring-up: nodes power on in lockstep,
  boot ESXi from BOSS, discover one another on the private VLAN, elect a
  primary that runs VxRail Manager, build the vSphere cluster, and assemble the
  vSAN datastore. Watts and progress % are illustrative.
- **Inside the cluster** (`#anatomy`) — the four-node floorplan; hover/click any
  block (NVMe, CPU, memory, BOSS, NIC, iDRAC, PSU, or the top-of-rack fabric).
- **Components & options** (`#components`) — the build-to-order menu: node
  platform (VE/VP/VS/VD, Intel & AMD), vSAN ESA vs OSA, drives, networking,
  fabric, GPUs, topology, and the VxRail/VMware software stack.
- **Use cases** (`#usecases`) — worked builds for VDI, edge/ROBO, and a VMware
  Cloud Foundation private cloud, each with a build sheet resolved against the
  catalog.

## Key invariants (enforced by `backend/tests/`)

- **The clock lives in the frontend, never in the engine.** `engine.py` is
  pure (AST-checked: no FastAPI/IO/timers); the `setInterval` is in `App.tsx`.
- Phase order `off→power→esxi→discovery→primary→cluster→vsan→online` never
  regresses; `progressPercent` climbs monotonically 0→100.
- **Nodes boot in lockstep**: in the `power`/`esxi`/`discovery` phases, whatever
  region lights on one node lights on all four.
- **Primary election lights exactly one node**: in the `primary` phase only the
  elected node (n1) is active — the defining HCI beat, breaking lockstep.
- The **VxRail Manager cluster build is the single longest stage** (max
  `cycleCost`; the UI dwells on it, as the R760 twin does on memory training).
- Four-node symmetry: every per-node region has same-kind, same-size twins on
  all four nodes (a cluster is identical building blocks); exactly two fabric
  switches; every `RegionKind` is exercised.

## Scope & sourcing

Timings and wattages are illustrative, not measured; the floorplan is a
stylized mental model, not a rack-accurate drawing (project scope guardrail).
The only shipped visual is a self-contained schematic drawn for this project,
honestly credited as *not* a Dell product image. Copy spells out HCI, Dell,
and VMware vocabulary (vSAN, ESA/OSA, BOSS, RoCE, vMotion, VCF, SmartFabric,
Dynamic Nodes, witness, ROBO) on first use. Grounded in the Dell VxRail
product page, the VxRail spec sheet (H16763), the vSAN ESA Info Hub, and the
VxRail architecture guide (see the anatomy `sources`).
