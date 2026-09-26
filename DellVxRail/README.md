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

Fact-checked September 2026 against Dell's 2025 spec sheet (H16763) and
support docs. Points worth knowing before editing copy: per-node memory tops
out at 8 TB on the VE-660/VP-760 (3 TB on the AMD nodes); the VS-760 is a
hybrid hard-drive OSA platform; vSAN ESA needs 16 cores, 128 GB and 10 GbE
per node, and RoCE is optional; VxRail 8.0 removed the automated SmartFabric
switch configuration that 4.7/7.0 first runs had; CloudIQ is now Dell AIOps
and can start VxRail updates; the 25–40 minute cluster build is Dell's
planning-guide figure; "first HCI system fully integrated with VCF" is Dell's
own claim and is worded as such.

## Failure scenario: a node add refused on a version mismatch

The repo's first day-2 trace. It starts where the first run ends: four nodes
serving virtual machines. A fifth node is racked and discovered, the Add
VxRail Hosts compatibility check finds its factory image (7.0.370) older than
the cluster (8.0.300) can take, and the add is refused before the node touches
vSAN. The admin re-images the node with RASR (Rapid Appliance Self Recovery),
the retry passes, the host joins, vSAN claims its drives and rebalances.

- Open it at `/#scenario=node-add-mismatch`, or pick it from the Scenario
  control on the First run page. It composes with the trace deep links:
  `/#scenario=node-add-mismatch&phase=refused`. Changing scenario rewinds
  playback.
- Backend: `app/nodeadd.py` is a second pure engine (same AST purity rule,
  same `FirstRunState`, extended only with optional fields). It is served on
  the existing route as `GET /api/firstrun?scenario=node-add-mismatch`;
  `GET /api/scenarios` lists both traces with their sources, and
  `GET /api/anatomy?scenario=node-add-mismatch` returns the five-node map
  (`NODE_ADD_ANATOMY`, the four-node map plus one more `_node`). With no
  `scenario` parameter every route answers exactly as before.
- Phases: `serving → racked → found → check → refused → reimage → recheck →
  join → rebalance → expanded`.
- Invariants (`tests/test_nodeadd.py`): a mismatched node never joins vSAN
  (`mismatchedNodesInVsan` is 0 on every step, and vSAN stays at four hosts
  while the versions differ); the running cluster is untouched (every original
  node's CPU, memory, NVMe, NIC and power supplies and both switches are lit on every step,
  and the VM count never moves); the datastore grows exactly once, by one
  node's worth, after the recheck passes; the re-image is node-local and the
  unique longest stage; the first-run response is byte-identical to the one
  served before scenarios existed (sha256 pinned at three reading levels).
- The other classic way a node add stops is one step earlier. Discovery uses
  the VMware Loudmouth service over IPv6 multicast on the internal management
  VLAN (3939 by default), so a switch port missing that VLAN, or MLD snooping
  with no querier, hides the node completely. That case is covered in the
  `found` step's prose, not as a second trace.
- What follows the sources (listed in `nodeadd.SOURCES` and under the
  diagram): where the check sits, what a refused node has and has not
  touched, RASR as the recovery, and how discovery works. The version pair,
  terabytes, VM count, watts and timings are illustrative. Recent releases
  upgrade a slightly older node automatically when the pair is inside Dell's
  Node Addition Matrix; this trace assumes a pair outside it (a 7.0.x image
  against an 8.0.x cluster). The matrix PDF could not be fetched during
  review, so the prose points at KB 000012298 and does not quote cells from
  it. The Dell community thread in the sources is an admin asking the
  question, unanswered; it shows people meet the case, not how it resolves.
  vSAN's automatic rebalance is off by default, and the `rebalance` step says
  this cluster has it enabled.
- `mismatchedNodesInVsan` is computed from each step's vSAN host count and
  versions, not typed in, so an engine edit that lets the node in early moves
  the counter and fails `test_a_mismatched_node_never_joins_vsan`.
- An unknown `#scenario=` falls back to the first run.
- The guided tour stays on the first run and the four-node map. Opening it
  from the scenario switches back to the first run.
