# PhysicsME5 — PowerVault ME5 RAID physics simulator

Product #3 of `physics_specs/10-additional-products.md`: the Dell
PowerVault ME5, the suite's *first* storage sim on purpose. The ME5 is
Dell's entry SAN — dual controllers, classic RAID, no dedupe — and its
simplicity is the pedagogy: learn the ledger here, and the machinery the
bigger arrays add (PowerStore's dedupe, PowerMax's fabric) becomes
legible by contrast.

**The one idea: protection is paid for in writes, and failures turn time
into risk.** Every host write is multiplied by the RAID write penalty
before it touches a drive — ×2 mirrored, ×4 RAID 5 (read data + parity,
write both), ×6 RAID 6 — and every drive failure opens a rebuild window
(capacity ÷ an honest ~50 MB/s) during which one more failure may mean
loss. Two identities are asserted per tick in the tests, house style:

- **IOPS balance** — backend disk I/O = reads × read-cost + writes ×
  penalty, every tick of every scenario.
- **Capacity arithmetic** — raw = usable + protection overhead + spares,
  exactly (the build plan's raw→usable→effective identity).

## Run

```
./PhysicsME5/scripts/start_all.sh    # backend :8041 background, frontend :5214 foreground
./PhysicsME5/scripts/stop_all.sh
```

Backend tests: `cd PhysicsME5/backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd PhysicsME5/frontend && npm run build`
Vite proxies `/api` → `http://localhost:8041`. `POST /api/simulate`
takes a Scenario (array config, workload dials, timed events; ticks are
sim-*minutes*, coarsenable to hours because rebuilds are days) and
returns Validation[] + SimState[] + LogEntry[] + Summary; GET runs the
default scenario.

## Guided scenarios

RAID write penalty (R10 vs R6, exactly 3× apart) · Rebuild a 20 TB drive
(days, and why RAID 6 displaced RAID 5) · Second failure mid-rebuild
(R6 shrugs, R5 dies) · Lose a controller (service survives; write cache
falls to write-through) · Where all-flash hits the ceiling (the
bottleneck moves to the controllers).

## What we don't model

Caching beyond a flat controller overhead, snapshots, thin provisioning,
stripe geometry, SAS topology, multipathing, expansion shelves, and
RAID 10's lucky second failures (the engine deliberately takes the
unlucky mirror and logs that it did). Drive IOPS, rebuild rates, and the
per-controller ceiling are estimates pending calibration against Dell's
ME5 documentation — every constant carries units and a `source` field in
`backend/app/constants.py`, and estimate-derived readouts are labeled in
the UI. The ME5084 (5U84) sibling is mentioned, not modeled.
