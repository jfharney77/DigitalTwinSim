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
replication, Cloud Tier, restore paths, MTrees, or Retention Lock. The
"appliance ingest time" instrument is novel-data arithmetic on the appliance
side only: the clients' read-and-fingerprint time over every logical byte
(DD Boost moves that cost, it does not delete it) is not modelled, so it is
a lower bound on a real backup window. Files ransomware has encrypted stop
churning (nobody can edit them), which is why daily novel data falls after
an attack halts. The capacity notice (`Summary.capacityNoticeDay`, a log
line, and the trend strip under the capacity chart) is this simulator's own
rule: physical more than 20% above a straight line fitted to the 10 days
before the first disturbance; both numbers are labeled estimates. GC is
instantaneous at generation expiry (real cleaning is scheduled and
throttled). The distinction the model does keep honest: *static*
high-entropy data still dedupes across generations (it just won't
compress); only session-keyed encryption defeats deduplication itself.

Appliance usable capacities are the maxima in Dell's PowerProtect Data
Domain family spec sheet (DD3410 40 TB, DD9910 2.1 PB, all-flash DD9910F
1.1 PB; checked September 2026); base ingest, index RAM, chunk size, the compression
curve, and the knee slope are estimates — every constant in
`backend/app/constants.py` carries units and a `source` field, and
estimates say so.

## Graded labs

Three labs follow `docs/LAB_PATTERN.md` (`backend/app/labs.py`, `#labs` /
`#lab=<id>` in the UI; `GET /api/labs`, `POST /api/labs/{id}/grade`). Delivered
work is `protectedTbMean`: logical TB under protection averaged over every day
of the run, store-full days counting zero. It is an illustrative proxy. Every
constraint is a criterion measured from the trace, and grading also runs
in the browser on the static build.

| Lab | Difficulty | Lesson |
|---|---|---|
| `branch-box-memory` | 1 | On the DD3410 the fingerprint index outgrows its RAM long before the disks reach 85%, so RAM sets the longest retention. |
| `encrypted-tenant` | 2 | Under host-side encryption, stored data is retention × full size and the index sets ingest, so the box with more index RAM beats the faster one. |
| `late-alarm` | 3 | Heavy honest churn dilutes slow ransomware, the entropy alarm fires about 52 days late, and retention has to outlast that dwell time. |
