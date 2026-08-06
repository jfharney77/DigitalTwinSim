# DellPowerEdgeXE9680 — 8-GPU HGX server digital twin

Same architecture as the other twins in this repo, applied to the **Dell
PowerEdge XE9680** — Dell's flagship 8-GPU server, and the machine xAI's
Colossus supercluster was first built from (8-GPU HGX servers, 64 GPUs per
liquid-cooled rack, ~1,500 racks, 100,000 GPUs running in 122 days).

The one idea: **NVLink stops at the chassis wall.** Inside the box, an
NVSwitch complex on the HGX baseboard fuses the eight SXM GPUs into a single
NVLink domain — atomically, and never more than eight. Past the sheet metal,
every GPU gets its own dedicated 400 GbE NIC onto the data-center fabric.
The twin's two hero counters carry the whole architecture: `gpusInDomain`
snaps 0 → 8 at the fuse and never grows again, and `nicsUp` climbs to 8 —
one per GPU — because scale past the wall is the network's job. It is the
deliberate counterpoint to the `DellPowerEdgeXE9712/` twin, whose rack fuses
72 GPUs by moving the wall out to the rack itself.

```
backend/   app/{models,anatomy,engine,catalog,usecases,leveling,main}.py + tests/
frontend/  src/{api,types,level}.ts, App.tsx, components/{ChassisView,AnatomyPage,
           CatalogPage,UseCasePage,PowerOnControls,PowerOnCounters,LevelControl}.tsx
scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./scripts/start_all.sh` (backend :8028 background, frontend :5201
  foreground). Stop: `./scripts/stop_all.sh`.
- Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8028`. Trace endpoint is
  `GET /api/poweron` returning `PowerOnResponse` (chassis-twin style).

Key invariants (enforced in `backend/tests/`):

- **The fuse is atomic and the domain stops at eight** — `gpusInDomain` is
  0 through the whole bring-up, exactly 8 from the `fuse` phase on, and
  never more: joining the cluster fabric does not grow the NVLink domain.
- **One NIC per GPU** — eight `network` regions pair 1:1 with the eight
  `gpu` regions by id; `nicsUp` is 0 until the `fabric` phase and exactly 8
  after; the fuse precedes the fabric (NVLink inside, Ethernet beyond).
- **The host boots before any GPU** — a GPU server is still a server.
- **GPU init is the longest stage** (unique max `cycleCost`) — HBM training
  on eight modules, the in-box counterpart of the XE9712's cable training.
- **Fans run whenever GPUs draw power** — air is the coolant; cooling is a
  condition of staying up, not a phase of bring-up.
- **Geometry carries the lesson** — the GPU field out-draws every other
  region kind, and the NVSwitch strip sits strictly between the GPUs and
  the NICs.

Referenced by `CustomerSetup/xAI-Colossus/` as the sourced first-build
compute block. Cross-references: `DellPowerEdgeXE9712/` (the rack that moves
the wall), `DellPowerSwitchSN6000/` (the fabric on the far side of the
NICs), `DellIR7000/` (the loop the liquid-cooled XE9680L variant plugs
into), `DellIDRAC/` (the BMC that sequences the trace), and `GPU/` (what
one die does with a matmul).
