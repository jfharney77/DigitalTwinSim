# PhysicsMX7000 — shared-infrastructure simulator

An interactive, simplified physics model of the **Dell PowerEdge MX7000**,
the 7U modular chassis: up to eight single-width compute or storage sleds
sharing nine chassis fans, up to six pooled 3000 W power supplies, two
fabrics, and two management modules. Built from product #1 of
`physics_specs/10-additional-products.md` on the `DellPowerEdgeR760Thermal/`
template (scenario in → Validation[] + SimState[] trace + LogEntry[] +
Summary out; pure engine, frontend playback clock).

## The one idea: nothing here belongs to a sled

A rack server carries its own fans and PSUs; a modular chassis pools them,
and the pooling is where all the interesting physics lives:

- **The shared fan tax.** The nine-fan wall is controlled on the *hottest*
  sled's temperature. One 100%-load sled sets the rpm — and the cubic fan
  power — for seven innocent neighbors. The noisy-neighbor scenario runs
  the comparison live, and the per-tick power balance (fan watts inside
  the sum) makes it an asserted fact.
- **Pooled redundancy math.** Grid redundancy alternates PSUs across two
  AC feeds and survives losing a whole feed; N+1 covers one PSU dying but
  puts the pool on one feed, so a feed loss is lights-out. Two guided
  scenarios run the same event against each policy.
- **Composability.** A storage sled has no workload of its own — its
  sixteen drives follow the compute sled that owns them, and reassignment
  is a timed config event, not a recable.
- **The chassis power budget** throttles every compute sled together when
  the total crosses the cap — the shared haircut a shared budget implies.

Invariants pinned in `backend/tests/`: per-tick power balance
(Σ sled powers + fabric + management + fans = DC; AC = DC ÷ η(load)),
steady-state heat balance (ΔT = DC/(ṁ·cp)), grid-survives-feed-loss vs
N+1-does-not, the noisy-neighbor tax, storage-follows-owner, engine
purity (AST-checked), and the constants table's honesty rule.

## Run it

```
./PhysicsMX7000/scripts/start_all.sh   # backend :8039 background, frontend :5212 foreground
./PhysicsMX7000/scripts/stop_all.sh
```

Backend tests: `cd PhysicsMX7000/backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd PhysicsMX7000/frontend && npm run build`
Vite proxies `/api` → `http://localhost:8039`. Trace endpoint:
`POST /api/simulate` (scenario-driven); `GET /api/simulate` runs the
default eight-sled steady scenario.

## What we don't model

CFD, per-slot airflow steering, fabric traffic and switching physics,
sled-level BMC behavior, PSU sharing transients, acoustics beyond rpm as
a proxy. Chassis facts (8 bays, 9 fans, up to 6× 3000 W PSUs, grid
redundancy, MX5016s's 16 drives) are from Dell's MX7000 spec sheet and
technical guide; most physics constants are estimates, and every one
carries a source tag in `backend/app/constants.py`, surfaced by the API's
`/api/constants`.

## Companions in this repo

The R760Thermal twin is the same causal chain inside one server; the
IR7000 twin is the same heat balance one level up, at rack scale. The
narrative chassis twins (`DellPowerEdgeR760/`, `DellVxRail/`) tell the
power-on story this simulator deliberately skips.
