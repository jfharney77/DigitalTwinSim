# PhysicsStorage — capacity & performance simulator

Third app of the physics suite (`physics_specs/02-storage-platforms.md`,
plan in `physics_specs/BUILD_PLAN.md`). One shared Archetype-B engine —
workload generator, the 1/(1−ρ) queueing knee, the raw → usable →
effective capacity ladder, rebuild races — parameterized into six
products. One sim-tick = one hour; capacity stories run for sim-months.

Per-product personalities, each pinned by tests:

- **PowerStore** — dual-controller ceiling; failover halves front-end
  capability and moves the knee left (degradation, never outage).
- **PowerMax** — component failures are decaying latency blips
  (`min_delivered_ratio > 0.99` under repeated kills); sync SRDF adds
  distance × 0.01 ms/km × 2 to writes (speed of light, the app's one
  non-estimate performance constant); async RPO = backlog ÷ link, grows
  under bursts, drains after.
- **PowerScale** — near-linear scale-out with a coordination tax;
  rebuild rate ∝ surviving nodes, so bigger clusters heal faster — the
  inversion of the controller array, asserted directly.
- **ObjectScale** — ms-class floor by design, the small-object metadata
  tax (−45% throughput), and WORM buckets whose delete events bounce.
- **PowerFlex** — aggregate = min(node ceilings, NIC bandwidth): the
  network is the array; rebuilds are minutes-class; add-nodes is a live
  event.
- **Exascale** (built last, composes the others) — partition one node
  pool among Lightning/file/object/block, automatic checkpoint
  stampedes, and the north-star instrument: **GPU idle due to data %**,
  PhysicsCompute's data-feed slider seen from the supply side.

## Run

```
./scripts/start_all.sh     # backend :8033 background, frontend :5206 foreground
./scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Companions

Narrated twins of the same machines: `DellPowerStore/` (:5175),
`DellPowerMax/` (:5178), `DellPowerScale/` (:5196), `DellPowerFlex/`
(:5189), `DellExascale/` (:5184). `PhysicsCompute/` (:5205) is the
demand side of the Exascale meta-sim's GPU-idle gauge.
