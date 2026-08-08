# PhysicsFabric — flow & congestion simulator

Fourth app of the physics suite (`physics_specs/03-networking.md`, plan
in `physics_specs/BUILD_PLAN.md`). One flow-level fluid engine (no
packets), three product personalities, and the two core lessons as
first-class mechanics: **oversubscription** (congestion appears exactly
where the downlink÷uplink ratio predicts) and **congestion →
latency/loss** (the storage app's 1/(1−ρ) knee, per link).

- **E3200 campus** — the same physics at human scale, plus PoE: the
  power budget binds before the ports do; PSU loss halves it and sheds
  devices by priority; a LAG-member failure is a 2 s STP outage and
  then a survivor at doubled ρ.
- **SN6000 AI Ethernet** — static-ECMP hash collisions (worst link up
  to +85% over fair share) vs Spectrum-X adaptive routing (~15%
  residual); lossless RoCE swaps drops for spreading pauses; the optics
  ledger (18 W pluggable vs 6 W CPO per port) rivals the ASIC at scale.
- **Quantum-X800 InfiniBand** — lossless *by construction*: drops are
  structurally zero on every step (tested under stress, not at idle);
  congestion is sender stall-µs; SHARP makes the link-bytes and
  all-reduce-rate counters cross.
- **Gray failure** — the adversarial scenario: 0.1% silent loss leaves
  every status light green while FCT triples; both halves asserted.

## Run

```
./scripts/start_all.sh     # backend :8034 background, frontend :5207 foreground
./scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Companions

Narrated twins: `DellPowerSwitchSN6000/` (:5185), `DellQuantumX800/`
(:5202), `DellPowerSwitchE3200/` (:5178). The endpoints band is
`PhysicsCompute/`'s XE9680s; the incast pattern is `PhysicsStorage/`'s
fan-out reads; the gray-failure payoff is `PhysicsData/`'s anomaly feed.
