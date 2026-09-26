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
- **Pooled redundancy math.** Grid redundancy splits PSUs across two
  AC feeds (Dell's wiring: slots 1–3 on Grid A, 4–6 on Grid B, populated
  1, 4, 2, 5, 3, 6) and survives losing a whole feed; N+1 (Dell's "PSU
  redundancy" mode) covers one PSU dying, and this model puts its pool
  on one feed, so a feed loss is lights-out. Two guided
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

## Graded labs

Three labs (`#labs`, `#lab=<id>`; recipe in `docs/LAB_PATTERN.md`) turn the
acceptance scenarios into challenges. `backend/app/labs.py` is pure;
`GET /api/labs` serves the labs and `POST /api/labs/{id}/grade` runs the
engine and grades the trace. On the static site the same file grades in the
browser under Pyodide. Delivered work is Σ util × clamp × 2 × TDP over the
compute sleds, averaged over the run with dark ticks at zero — an illustrative
proxy, as are the scores.

| Lab | Difficulty | Lesson |
|---|---|---|
| `spread-the-heat` | 1 | The fans follow the hottest sled and power is convex in load, so the same work spread over eight sleds is cooler and about 300 W cheaper than four sleds flat out. |
| `smallest-pool-that-survives` | 2 | Surviving a feed loss takes the same four PSUs arranged as grid, not more PSUs on N+1 — and a grid pool of two trips its one survivor. |
| `the-budget-is-a-wall` | 3 | Inside a 4000 W circuit with a dead fan, the power-cap dial only throttles; work per watt peaks near half load, so 350 W sleds run gently beat 205 W sleds run hard. |

## What we don't model

CFD, per-slot airflow steering, fabric traffic and switching physics,
sled-level BMC behavior, PSU sharing transients, acoustics beyond rpm as
a proxy. The real chassis splits its nine fans by job (five 80 mm rear
fans cool the sleds, four 60 mm front fans cool the I/O and management
modules) and has six I/O slots across Fabrics A, B and C; the model
folds the fans into one wall and draws one fabric pair. Chassis facts
(8 bays, 9 fans, up to 6× 3000 W Platinum PSUs, Grid A = slots 1–3 /
Grid B = slots 4–6, MX5016s's 16 drives) are from Dell's MX7000 spec
sheet and technical guide; most physics constants are estimates, and every one
carries a source tag in `backend/app/constants.py`, surfaced by the API's
`/api/constants`.

## Companions in this repo

The R760Thermal twin is the same causal chain inside one server; the
IR7000 twin is the same heat balance one level up, at rack scale. The
narrative chassis twins (`DellPowerEdgeR760/`, `DellVxRail/`) tell the
power-on story this simulator deliberately skips.
