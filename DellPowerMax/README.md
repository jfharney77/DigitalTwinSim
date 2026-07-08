# Dell PowerMax — inside the box

A digital-twin web app for the Dell PowerMax 2500/8500 mission-critical NVMe
storage array, following the same pattern as `GPU/`, `DellPowerEdgeR760/`, and
`DellPowerStore/`: a pure FastAPI engine that emits the bring-up sequence as
data, and a React/Vite frontend (Dell clean-design skin) that plays it back.

Written for a technically skilled reader who is new to the product: what's
inside a PowerMax **node pair** (two compute directors, cache, vault-to-flash,
and connectivity joined by a 100 Gb/s InfiniBand Dynamic Fabric) and its
**Dynamic Media Enclosure** (the NVMe drive shelf on the fabric), what happens
between connecting AC and serving I/O — there is no power button — what can be
configured into it, and what real deployments look like.

## Run

```bash
./DellPowerMax/scripts/start_all.sh    # backend :8005 (background) + frontend :5178 (foreground)
./DellPowerMax/scripts/stop_all.sh     # stop both
```

Backend tests: `cd DellPowerMax/backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd DellPowerMax/frontend && npm run build`

Vite proxies `/api` → `http://localhost:8005`, so open http://localhost:5178.
Ports are offset from the GPU app (8000/5173), the R760 (8001/5174),
PowerStore (8002/5175), Alienware (8003/5176), and iDRAC (8004/5177) so all
apps can run at once. If :8005 is taken, run the backend elsewhere and point
Vite at it: `API_TARGET=http://localhost:8015 npm run dev`.

## Pages

- **Power-on** — play the AC-to-serving-I/O trace; engine regions light up per
  step (PSUs → SPS self-test → vault validate → both directors boot PowerMaxOS
  10 → InfiniBand fabric forms → DME NVMe discovery → Flexible RAID pool →
  data services → online). The **fabric** phase comes before drive discovery
  because the drives hang off the fabric, not off a director's bus.
- **Inside the engine** (`#anatomy`) — annotated top-down floorplan of one
  node pair plus its DME; hover/click for what each block does (drive
  enclosure, vault-to-flash, cache, the mirror-image Node A / Node B
  directors, the Dynamic Fabric).
- **Components & options** (`#components`) — the configuration menu: array
  family (2500/8500), node pairs, director CPUs (memory config), cache,
  drives, DME, Flexible RAID, Dynamic Fabric, front-end I/O modules, vault &
  standby power, PowerMaxOS 10 software, management, power & PDUs, cabinet &
  dispersion.
- **Use cases** (`#usecases`) — mainframe + open-systems consolidation,
  mission-critical database with zero-RPO SRDF/Metro, and a cyber-resiliency
  capacity tier with an isolated vault — each with a resolvable build sheet.

See `initial_spec.md` for architecture, data models, and invariants.
