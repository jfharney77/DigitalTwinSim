# Dell PowerStore — inside the box

A digital-twin web app for the Dell PowerStore all-NVMe storage appliance,
following the same pattern as `GPU/` and `DellPowerEdgeR760/`: a pure FastAPI
engine that emits the bring-up sequence as data, and a React/Vite frontend
(Dell clean-design skin) that plays it back.

Written for a technically skilled reader who is new to the product: what's
inside the 2U enclosure (two active-active controller nodes sharing a 25-slot
NVMe drive bay), what happens between connecting AC and serving I/O — there is
no power button — what can be configured into it, and what real deployments
look like.

## Run

```bash
./DellPowerStore/scripts/start_all.sh    # backend :8002 (background) + frontend :5175 (foreground)
./DellPowerStore/scripts/stop_all.sh     # stop both
```

Backend tests: `cd DellPowerStore/backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd DellPowerStore/frontend && npm run build`

Vite proxies `/api` → `http://localhost:8002`, so open http://localhost:5175.
Ports are offset from the GPU app (8000/5173) and the R760 app (8001/5174) so
all three can run at once.

## Pages

- **Power-on** — play the AC-to-serving-I/O trace; enclosure regions light up
  per step (PSUs → BBU vault self-test → both nodes boot PowerStoreOS →
  NVMe/NVRAM discovery → cluster handshake → data services → online).
- **Inside the chassis** (`#anatomy`) — annotated top-down floorplan of the
  base enclosure with real product photos; hover/click for what each block
  does (drive bay, NVRAM, the mirror-image Node A / Node B canisters).
- **Components & options** (`#components`) — the configuration menu:
  appliance tiers (500T–9200T), NVMe drives, NVRAM, expansion shelves,
  clustering, I/O modules, mezzanine cards, power, PowerStoreOS software,
  management, protection, rack hardware.
- **Use cases** (`#usecases`) — VMware storage consolidation, database
  consolidation, edge block + file, each with a resolvable build sheet.

See `initial_spec.md` for architecture, data models, and invariants.
