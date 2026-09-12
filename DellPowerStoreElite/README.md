# DellPowerStoreElite — mixed-generation modernization digital twin

The twenty-sixth component: **Dell PowerStore Elite**, announced at Dell
Technologies World 2026 (May 19) and globally available from July 2026 — a
3U appliance on Intel Xeon Scalable (up to 50% more cores than the
3200T/5500 class), DDR5, a PCIe Gen 5 fabric, 40 low-profile E3 NVMe slots
(QLC/TLC), up to 5.8 PB effective behind a 6:1 data reduction guarantee,
up to 40 front-end ports (64 Gb FC / 100 GbE), and a 200 Gb RDMA node
interconnect.

**The one idea: modernization without migration.** Every prior storage twin
here boots a box; this one refuses to. The trace is a *cluster join* — an
existing prior-generation PowerStore serving the estate, the Elite waking
beside it, mixed-generation clustering fusing them into one system, volumes
rebalancing live over the RDMA mesh, cutover by multipathing, and the old
array repurposed rather than retired. The hero counter is
**`downtimeSeconds`, which exists to be 0** on every step; its companions
are `generationsInCluster` (1 → 2, exactly once, at the join) and
`iopsThousands`, which triples only *after* cutover — the 3x claim is
earned by the sequence, not asserted at the unboxing.

## Layout & commands

```
backend/   app/{models,anatomy,engine,catalog,usecases,leveling,main}.py + tests/
frontend/  src/{api,types,level}.ts, App.tsx, components/{ChassisView,AnatomyPage,
           CatalogPage,UseCasePage,JoinControls,JoinCounters,LevelControl}.tsx
scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./scripts/start_all.sh` (backend :8047 background, frontend :5220
  foreground). Stop: `./scripts/stop_all.sh`.
- Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8047`. The trace endpoint is
  `GET /api/join` returning `JoinResponse` (not `/api/poweron`).

## Signature invariants (backend/tests/test_engine.py)

- **Downtime is identically zero** on every step — the twin's reason for
  existing.
- **Service never pauses**: IOPS > 0 always and ≥85% of the starting
  baseline even at the rebalance peak.
- **The join happens exactly once**: `generations_in_cluster` is monotone
  1 → 2 with its single increment in the `join` phase; mixed-generation
  membership is the *end state*, not a transition, and the final step still
  lights prior-generation hardware (`test_the_prior_generation_is_never_evicted`).
- **The live rebalance is the unique longest stage** — the honest location
  of the cost of "no migration project" is duration, never availability.
- **3x only after cutover**: pre-cutover steps are pinned ≤1.2x baseline,
  post-cutover ≥3x — the performance claim is realized by the sequence.
- **The mesh carries the migration**: `cluster-mesh` never lights before
  the `mesh` phase and is active on every `rebalance` step.
- **Effective capacity jumps exactly once, at the join** (the Elite pool:
  5.8 PB effective at 6:1), and is otherwise monotone.
- Elite nodes wake in `-a`/`-b` lockstep (inherited from the PowerStore
  twin); phase order `steady→power→join→mesh→rebalance→cutover→repurpose→elite`
  never regresses; the engine is pure (AST-checked).

## Geometry carries the lesson (backend/tests/test_anatomy.py)

The map is deliberately **two appliances, not one**: the prior-generation
2U array as the top band, the Elite 3U as the bottom band, and the 200 Gb
RDMA interconnect drawn strictly between them.
`test_the_generations_are_drawn_as_peers` pins both bands to the same width
(neither is a satellite of the other) with the Elite's 40-slot E3 bay drawn
larger than the prior 25-slot bay;
`test_the_mesh_sits_between_the_generations` pins the interconnect's
placement and span. No product photos ship (Elite imagery is too new for
clean licensing) — the `photo` fields are `None`, and tests require credit
only when a photo exists.

## Sources

Facts and figures follow Dell's DTW 2026 launch materials and press
coverage, carried in the anatomy's `sources`: Dell's May 19, 2026 press
release, TechTarget's in-place-upgrades analysis, StorageNewsletter's
launch summary, and DCD's announcement coverage. IOPS, capacities and
timings in the trace are illustrative, shaped by the vendor's claims (3x
performance on a 70/30 mix, 6:1 guaranteed reduction, 5.8 PB effective per
3U, reads up to 70% faster via Metadata Acceleration, up to 95% less
manual effort) and labeled as the vendor's own where it matters.

## Relations to other twins

- `DellPowerStore/` — the prior generation this twin joins to; its power-on
  trace is the uncompressed version of this trace's two `power` steps.
- `DellPowerScale/` / `DellPowerFlex/` — the other "growth without
  migration" arguments (no volumes / no controller); Elite is the midrange
  array's version: no forklift.
- `DellCyberDetect/` — Cyber Detect reaches PowerStore in Q3 2026; the
  catalog's resilience category points there.
- `DellCloudIQ/` — the AIOps pipeline behind the autonomous-operations
  category.
