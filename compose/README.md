# compose — the twins, coupled

The twins already cross-reference each other in prose. PhysicsCompute's
`data_feed_pct` slider *is* PhysicsStorage's `gpu_idle_due_to_data` gauge; the
XE9712's cold plate *is* the CDU's load. Until now a reader had to carry the
number across by hand.

This package makes the carry a piece of code with a test on it: **one engine's
trace becomes another engine's scenario, and an identity is asserted across the
seam.** A coupling without an identity would be a prose cross-reference with
extra steps, and is not admitted.

Design: [`docs/COMPOSITION_DESIGN.md`](../docs/COMPOSITION_DESIGN.md). Where
the build deviates from it, section "Implementation notes" at the bottom of
this file says so.

```
compose/
  loader.py        load each backend's app package under a private name
  resample.py      hold, mean_pool, steady_window, to_events — pure, integral-conserving
  seam.py          SeamResult, compare, per_tick, assert_seams
  chain.py         Chain, Link, run()
  loop.py          the fixed point that closes C1+C2
  executors.py     one executor per kind of chain
  couplings/       c1…c8: META, adapt(), check(), execute()
  catalog.py       the couplings and preset chains as data, prose at reading levels 1/3/5
  presets.py       the nine preset chains
  constants.py     the numbers neither engine on either side owns
  json_adapter.py  the same couplings over recorded JSON traces
  backend/app/     the only impure edge: FastAPI, :8048
  frontend/        the Couplings page, :5221
  tests/           the seam identities, as pytest
```

## Run it

```
./compose/scripts/start_all.sh        # backend :8048 background, frontend :5221 foreground
./compose/scripts/stop_all.sh
cd compose/backend && . .venv/bin/activate && python -m pytest ../tests -q
cd compose/frontend && npm run build
```

The twins' own servers do **not** need to be running: the engines are imported
and called in-process. Nothing here opens a socket to another app.

From Python:

```python
from compose import run, assert_seams
from compose.presets import chain

trace = run(chain("closed-loop"))
assert_seams(trace)          # raises on a broken seam; run() only reports one
```

## The eight seams

| | Seam | What crosses | Identity |
|---|---|---|---|
| C1 | PhysicsCompute (xe9712) → PhysicsCDU | rack liquid heat → tray-bank utilization | heat out equals heat in, per tick and over the run |
| C2 | PhysicsCDU → PhysicsCompute | supply temperature, IRC cap, pump flow, tripped banks | at the fixed point C1 still holds, supply agrees, and coupling can only cost tokens |
| C3 | PhysicsStorage (exascale) → PhysicsCompute | delivered ÷ demanded read IOPS → `data_feed_pct` | the two engines' "idle because data was late" gauges are the same number |
| C4 | PhysicsFabric → PhysicsAIFactory | gray-vs-healthy flow-completion time → step-time stretch | green in the fabric, lower tokens in the factory — both asserted |
| C5 | R760Thermal / PhysicsCompute → PhysicsRackPower | server wall watts → rack loads | watts are conserved across the seam |
| C6 | PhysicsResilience ⇄ PhysicsDataDomain | spread rate → ransomware event; entropy alarm → detection latency | both engines agree how much is encrypted; the RTO law is unchanged |
| C7 | PhysicsXR → PhysicsFleet | hostile site-days → a deterministic fault schedule | every injected fault is counted, and every admin hour is attributable |
| C8 | C1–C4 → PhysicsAIFactory | the capstone, fed by real engines | fed and aggregate agree, or the gap names a cause from a closed list |

C1 and C2 form the closed loop. The fixed point is over whole runs, not ticks:
fixed damping, a fixed iteration cap, a fixed convergence threshold, no
randomness — the same chain gives the same `CoupledTrace`, byte for byte.

## House rules kept

- **Pure, like the engines.** `compose/` imports no FastAPI, no `time`, no
  `random`, no file or network IO; `tests/test_purity.py` AST-checks every
  module with `twinkit.testing.assert_engine_is_pure`, and pins that only
  `loader.py` touches `importlib`.
- **The clock is in the frontend.** The playback interval lives in `App.tsx`.
- **Engines are not edited to be coupled.** Every adapter uses events and
  fields an engine already has. Where an engine lacks the input a seam wants,
  the chain carries a note saying what the workaround costs (integer
  quantization, cap-as-demand, trace splicing) rather than hiding it.
- **Numbers stay illustrative.** Coupling two illustrative engines gives an
  illustrative result. Every `CoupledTrace` carries `illustrative: true` and
  the union of the estimated constants the seam touched, and the page prints
  them.
- **Reading levels.** Coupling blurbs and chain prose are authored at levels
  1/3/5 through the shared `L(...)` mechanism; the server resolves, as in every
  twin.

## The page

`#chains` (default) draws the chain as a row of engine cards joined by seam
connectors — each connector carries the identity it asserts and a live
`lhs = rhs` readout at the playback cursor, and turns red with the size of the
error when a seam does not hold. Below it the strip charts put the source
series and the target series it became on one time axis, with the seam chart
outlined: two curves that should lie on top of each other. The right-hand
column shows what the adapter wrote into the target's scenario, the target's
own validations (they still run), the divergences a fed chain names, and — for
a closed chain — a residual-per-iteration chart with a scrubber that steps
through the loop settling.

`#seams` is the eight couplings as a reference: fields read, inputs written,
units, time base, identity, tolerance, and the pytest that asserts it, plus the
seam constants with their sources.

| Route | Returns |
|---|---|
| `GET /api/couplings` | the eight couplings as data, reading-leveled |
| `GET /api/chains` | the preset chains, each with the body `POST /api/run/custom` takes |
| `GET /api/run?chain=<id>` | a preset chain's `CoupledTrace` (also the liveness GET) |
| `POST /api/run/custom` | an edited chain |
| `GET /api/constants` | the seam constants with unit, source and `estimated` |
| `GET /api/levels` | the shared reading-level scale |

## Static hosting

`scripts/build_static.py compose --verify` snapshots every GET, including one
file per preset chain (`frontend/static.json` enumerates the ids), so the page
runs from files with no backend — `scripts/build_site.sh compose` then
`scripts/smoke_static.sh compose`. `POST /api/run/custom` is deliberately
skipped: answering an arbitrary chain needs eleven engines in the interpreter,
which is more than the in-browser bundle carries. Hosted, the page serves the
presets and says why a custom chain needs a server.

## PhysicsAIFactory's "fed by engines" mode

The capstone's README always said its `Scenario` shape "is the interface the
per-product engines could later feed". That mode is now a two-position control
on its page: **Aggregate** is the factory's own model (one efficiency number
per block), **Fed by engines** runs the chain `factory-fed` here and reads the
factory trace whose inputs came from Exascale's delivered throughput, the
XE9712's measured GPU watts, the CDU's pump power, and the fabric's
flow-completion time. The factory engine is unchanged in both. When the
composition server is not running, the control disables itself and shows the
start command; the floorplan stays on the aggregate run, because the seams
carry instrument values, not the map.

`compose/tests/test_c8.py` is the agreement test: tokens within 5%, facility MW
within 8%, idle within 2 points, PUE within 0.05 — wide on purpose, because the
job is to catch the two models drifting apart, not to pretend they are the same
model. Any larger gap must name a cause from a closed list (`stall_power`,
`hourly_rounding`, `cap_vs_shed`, `checkpoint_burst`, `gpu_tier_vs_detailed`,
`gray_fabric`), and an unexplained divergence fails the test.

## Implementation notes (deviations from the design)

- **The server lives in `compose/backend/app/`, not `compose/server/.`** Every
  shared script in the repo — `scripts/smoke.sh`, `scripts/build_static.py`,
  `scripts/build_site.sh`, `scripts/gen_components.py` — finds a component's
  server at `<dir>/backend/app/main.py`. Matching that got the smoke harness
  and static hosting for free. `compose/` still holds no `app` package of its
  own to claim in the root suite: the tests import `compose.*`, and
  `tests/test_api_surface.py` loads the server module from its path.
- **The POST route is `/api/run/custom`, not a POST on `/api/run`.** Splitting
  them is what lets a static build snapshot the presets and skip the one route
  a browser cannot answer.
- **No `bake.py`.** The design proposed a separate baker writing
  `frontend/public/baked/`. The repo grew a general snapshot builder in the
  meantime (`docs/STATIC_HOSTING.md`), which does the same job through
  `apiFetch`, keeps one naming contract instead of two, and needs no committed
  generated files.
- **Two extra `Divergence` causes** — `gpu_tier_vs_detailed` and `gray_fabric`
  — were added to the closed list while building C8: the design's four could
  not name gaps the chain actually produces, and an unexplained divergence
  fails the test rather than being rounded away.
