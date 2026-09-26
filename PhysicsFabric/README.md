# PhysicsFabric — flow & congestion simulator

Fourth app of the physics suite (`physics_specs/03-networking.md`, plan
in `physics_specs/BUILD_PLAN.md`). One flow-level fluid engine (no
packets), three product personalities, and the two core lessons as
first-class mechanics: **oversubscription** (congestion appears exactly
where the downlink÷uplink ratio predicts) and **congestion →
latency/loss** (the storage app's 1/(1−ρ) knee, per link).

- **E3200 campus** — the same physics at human scale, plus PoE: the
  power budget binds before the ports do; PSU loss halves it and sheds
  devices by priority (Dell rates the E3248P-ON at 1440 W of PoE on two
  PSUs and 713–813 W on one; the sim's 740 W default is illustrative);
  an uplink failure is a ~2 s rapid-STP-class outage (estimate) and
  then a survivor at doubled ρ.
- **SN6000 AI Ethernet** — static-ECMP hash collisions (worst link up
  to +85% over fair share) vs Spectrum-X adaptive routing (~15%
  residual); lossless RoCE swaps drops for spreading pauses; the optics
  ledger (18 W pluggable vs 6 W CPO per port — estimates; Dell's
  datasheet claims 5x better power efficiency for CPO) rivals the ASIC at scale.
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

## Graded labs

Three labs (`#labs`, `#lab=<id>`) follow `docs/LAB_PATTERN.md`: a goal, the
ordinary controls, and a pure grader (`backend/app/labs.py`, routes
`GET /api/labs` and `POST /api/labs/{id}/grade`). Work is a whole-run mean rate
(goodput, effective all-reduce, non-collective goodput), and every constraint
is a criterion measured from the trace. Scores and rates are illustrative.

| Lab | Difficulty | Lesson |
|---|---|---|
| `elephants-on-a-budget` | 1 | A hash collision is a placement problem: adaptive routing and co-packaged optics fix it inside 8,000 W, and buying spines does not. |
| `non-blocking-minus-one` | 2 | Size oversubscription on the surviving spines: 1:1 as built is not 1:1 after a loss, so spread the endpoints over more leaves. |
| `collectives-past-a-liar` | 3 | SHARP makes the all-reduce target reachable on twelve switches, and a gray failure taxes 35% ÷ leaves with every light green, so offer headroom. |

The labs cite two Explain entries added for them, `sharp` and `gray-failure`
(appended at the end of `presets.py`). In a static build the grade route runs
in the browser through the bundled engine, like `POST /api/simulate`.
