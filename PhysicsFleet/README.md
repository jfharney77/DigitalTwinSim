# PhysicsFleet — cloud & edge fleet-operations simulator

Fifth app of the physics suite (`physics_specs/04-cloud-edge-automation.md`,
plan in `physics_specs/BUILD_PLAN.md`). One Archetype-D fleet engine —
sites × nodes, N+1 placement math, deterministic wear faults (one per
3,000 node-days), monthly release waves against a 16 h/day ops budget,
config drift — with the **admin-hours ledger** as the teaching
instrument. Tick = one sim-day.

Five personalities, each pinned by tests:

- **VxRail** — the lifecycle bundle: rolling updates under N+1 with
  zero outage minutes vs manual mode's sawtooth version currency;
  the 3-node trap opens an exposure window a fourth node would close.
- **Private Cloud** — two stacks under one control plane ≈ one ops
  bill; catalog (0.25 h) vs artisanal (16 h) deploys.
- **APEX** — pure Archetype F: as-a-service (base + 1.5× overage) vs
  ownership that must buy the demand peak. Spiky demand flips the
  $/VM-hour ranking to as-a-service; steady flips it back — both
  directions asserted. The buffer prices outage-vs-air.
- **NativeEdge / Distributed Private Cloud** — 0.5 h zero-touch vs
  8 h site visits (the 500-store bill ≈ 15×); single-node faults are
  truck-roll days, 2-node HA makes them failovers; WAN outages mean
  autonomy + drift, reconciled on reconnect.
- **Automation Studio** — the same bad change costs 0 minutes gated
  and 240 ungated; pipelines double as drift enforcement.

The automation gap lives in the constants table itself
(`test_the_automation_gap_is_an_order_of_magnitude_in_the_table`).

## Run

```
./scripts/start_all.sh     # backend :8035 background, frontend :5208 foreground
./scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Companions

Narrated twins: `DellVxRail/` (:5179), `DellPrivateCloud/` (:5198),
`DellNativeEdge/` (:5187) — their invariants (controlPlanes==1,
operatorActions≤1) reappear here as line items on the hours ledger.
