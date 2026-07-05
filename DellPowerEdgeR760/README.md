# Dell PowerEdge R760 — inside the box

A digital-twin web app for the Dell PowerEdge R760 2U rack server, following
the same pattern as `GPU/`: a pure FastAPI engine that emits the power-on
sequence as data, and a React/Vite frontend (Dell clean-design skin) that
plays it back.

Written for a technically skilled reader who is new to the product: what's
inside the chassis, what happens between plugging in the AC cord and a running
OS, what can be configured into the box, and what real deployments look like.

## Run

```bash
./DellPowerEdgeR760/scripts/start_all.sh    # backend :8001 (background) + frontend :5174 (foreground)
./DellPowerEdgeR760/scripts/stop_all.sh     # stop both
```

Backend tests: `cd DellPowerEdgeR760/backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd DellPowerEdgeR760/frontend && npm run build`

Vite proxies `/api` → `http://localhost:8001`, so open http://localhost:5174.
Ports are offset from the GPU app (8000/5173) so both can run at once.

## Pages

- **Power-on** — play the plug-in-to-OS trace; chassis regions light up per
  step (standby rail → iDRAC boot → fans → POST/memory training → boot → OS).
- **Inside the chassis** (`#anatomy`) — annotated top-down floorplan traced
  from Dell's interior photo; hover/click for what each block does.
- **Components & options** (`#components`) — the configuration menu:
  processors, memory, drive bays, RAID, boot, network, GPUs, power, cooling,
  management, rack hardware.
- **Use cases** (`#usecases`) — virtualization host, AI inference node, OLTP
  database server, each with a resolvable build sheet.

See `initial_spec.md` for architecture, data models, and invariants.
