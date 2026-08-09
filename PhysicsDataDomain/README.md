# PhysicsDataDomain — the dedupe deep dive

A physics-grade simulator of **Dell PowerProtect Data Domain**'s soul:
variable-length deduplication. Product #4 of the expansion roster
(`physics_specs/10-additional-products.md`), built on the suite's shared
architecture (`physics_specs/BUILD_PLAN.md`, template
`DellPowerEdgeR760Thermal/`).

**The one idea: the dedupe ratio is emergent, not configured.** Nothing in
the scenario sets a ratio. Backup streams are chunked, fingerprinted, and
only novel chunks are stored; the ratio is the quotient of a capacity
ledger that balances to the terabyte every simulated day
(`physical(t) = physical(t−1) + novel − reclaimed`, asserted in the
tests). It rises with retention, falls with churn, and collapses to ~1:1
the day a source starts encrypting before backup — because session-keyed
ciphertext never matches anything, including itself.

The entropy instrument is the app's bridge to the security twins: the
same randomness that ruins the ratio is the earliest honest signal of
ransomware. In the smoke-alarm scenario the entropy of *today's changed
data* trips within a day or two of the attack, weeks before any capacity
curve bends — the physics Dell Cyber Detect reads from the snapshot side
(`DellCyberDetect/`), seen here from the ingest side. The narrative vault
twin (`DellPowerProtect/`) is the other companion: it shows where the
surviving copy lives; this app shows why thirty copies fit on one shelf.

## Run

```
./PhysicsDataDomain/scripts/start_all.sh   # backend :8042, frontend :5215
./PhysicsDataDomain/scripts/stop_all.sh
```

Backend tests: `cd PhysicsDataDomain/backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd PhysicsDataDomain/frontend && npm run build`

`POST /api/simulate` takes a Scenario (appliance, dataset properties,
retention, timed events — encrypt-the-source, ransomware) and returns
Validation[] + a day-by-day SimState[] trace + LogEntry[] + Summary; GET
runs the default (the "thirty fulls" founding demo). The engine
(`backend/app/engine.py`) is pure — AST-checked, no fastapi/time/random —
and the playback clock lives in the frontend.

## Guided scenarios

1. **Why 30 backups fit in 2×** — generational dedupe emerges live.
2. **The encrypted-source mistake** — day 30: novelty → 100%, the
   capacity curve breaks, the store fills mid-run, the backup window
   explodes.
3. **Entropy as a smoke alarm** — ransomware at day 40; the alarm beats
   the capacity trend-break by weeks (asserted in
   `test_acceptance_entropy_alarm_fires_before_capacity_notices`).
4. **The fingerprint-index knee** — the entry appliance runs out of
   index RAM before it runs out of disk; ingest degrades past the knee.
5. **Retention is the ratio's engine** — the ratio climbs for exactly as
   many days as you keep generations, then GC starts and it plateaus.

## What we don't model

No real hashing, chunk boundaries, or container layout — chunk novelty is
computed **analytically** from change rate, entropy, and encryption state
(an approximation of chunk liveness, not a hash-level simulation). No
replication, Cloud Tier, restore paths, MTrees, or Retention Lock. GC is
instantaneous at generation expiry (real cleaning is scheduled and
throttled). The distinction the model does keep honest: *static*
high-entropy data still dedupes across generations (it just won't
compress); only session-keyed encryption defeats deduplication itself.

Appliance capacities follow the Data Domain family data-sheet classes the
`DellPowerProtect` twin carries; index RAM, chunk size, the compression
curve, and the knee slope are estimates — every constant in
`backend/app/constants.py` carries units and a `source` field, and
estimates say so.
