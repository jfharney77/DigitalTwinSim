# DellPowerProtect — data-protection digital twin (twelfth component)

A digital twin of **Dell PowerProtect Data Domain** (the purpose-built
backup appliance, with an all-flash DD9910F model announced in May 2025) and **PowerProtect Cyber
Recovery** — the air-gapped vault architecture with Retention Lock
immutability and CyberSense machine-learning integrity analytics.

The subject is a **data path across two sites**, not a box. Same
architecture as the other twins: a pure-engine FastAPI `backend/`, a
React/Vite `frontend/` in the Dell clean-design skin, and `scripts/` to run
both.

## What it shows

- **Data lifecycle** (`/`) — the life of a backup: first full, weeks of
  dedupe, replication through a briefly-open air gap, Retention Lock,
  CyberSense scan, a ransomware attack that cannot reach the vault, and
  recovery from a provably clean copy.
- **Inside the vault** (`/#anatomy`) — left→right site map: workloads and
  PPDM, the production Data Domain, the air gap, and beyond it the vault
  Data Domain, CyberSense, and the clean room.
- **Components & options** (`/#components`) — appliances (All-Flash, DD9910,
  DD3410), DDOS software and Boost, immutability and hardening, the Cyber
  Recovery vault, CyberSense, backup software, replication and cloud
  tiering, estate integration, services.
- **Use cases** (`/#usecases`) — a hospital ransomware vault, bank
  compliance and cyber resilience, and forty branch offices into one vault.

## Run

```
./DellPowerProtect/scripts/start_all.sh   # backend :8010, frontend :5183
./DellPowerProtect/scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Key invariants (backend/tests/)

- Engine purity (AST-checked); the playback clock lives in `App.tsx`.
- Phase order `idle→backup→dedupe→replicate→airgap→scan→attack→recover→
  restored` never regresses.
- **Dedupe economics**: `storedTb <= logicalTb` always, logical is
  monotonic, and from the dedupe phase on the ratio holds at ≥10:1.
- **Air-gap discipline**: the `gap` region is active only in `replicate` and
  `recover` — both opened from the vault side — and in exactly those two.
- **The attack cannot reach the vault**: at the attack step no vault region
  (`dd-vault`, `cybersense`, `recovery-host`) and no gap is active, while
  production's blast radius is; and the vaulted copy is sealed strictly
  before the attack.
- CyberSense's scan is the single longest stage (max `cycleCost`); recovery
  is driven from the vault side.

## Failure scenario: free space keeps shrinking

`/#scenario=cleaning-gc` (or the Scenario picker on the simulator page) plays
a second pure trace, `backend/app/cleaning.py`, served by
`GET /api/lifecycle?scenario=cleaning-gc`. `GET /api/scenarios` lists both
traces; without the parameter the endpoint returns the happy path,
byte-identical to before. The deep link composes with the cursor links:
`#scenario=cleaning-gc&phase=alert`, `#scenario=cleaning-gc&step=6`.

The story is the one behind a recurring Data Domain support question. Backups
expire by retention and used space does not move, because expiry only
removes files from the namespace. The physical segments come back when the
cleaning (garbage collection) cycle runs, weekly by default. The appliance
passes 95% and raises its space alert; the clean then returns 12 TB where
the "Cleanable" estimate said 21, because a lagging replication context
and a snapshot nobody expired still reference the deleted files. A further
3 TB was never in the estimate: copies under Retention Lock whose delete
the appliance refused, so the catalog calls them expired and the appliance
does not. The recovery action is the real one: let replication catch up,
expire the stale snapshot, clean again (the two cleans together return the
21 TB first estimated). The locked copies wait out their date.

Phase order: `steady→expire→ingest→alert→clean→pinned→release→reclean→settled`.
Invariants (`backend/tests/test_cleaning_scenario.py`):

- The capacity ledger closes on every step:
  `stored = live + reclaimable + held(replication) + held(snapshot) + held(lock)`.
- **Expiry alone never frees space**, and **stored falls only during a clean
  phase**, by exactly what was reclaimable.
- **Locked data is never reclaimed before its lock ends**; releasing a hold
  moves terabytes to reclaimable without freeing any.
- The first clean returns less than the estimate, and the shortfall equals
  what replication and the snapshot still referenced. Locked files are never
  counted as cleanable: their delete was refused.
- A full appliance loses no stored backup, and the air gap keeps its
  discipline throughout.
- The copy-forward pass is the longest stage.

The hero counter is terabytes reclaimed against the cleanable estimate.
The over-threshold appliance is drawn in the error colour. The alert wording,
the default schedule and the pinning behaviours are sourced from Dell KB
articles carried in the scenario data; terabytes, hours, lock days and the
95% alert threshold are illustrative (Dell's documented example threshold is
90%).

This twin closes a loop the PowerMax twin opened — its cyber-resiliency
vault use case is, concretely, this architecture. Capacities, ratios, and
timings are illustrative, anchored to Dell's 2025 PowerProtect
announcements (see anatomy `sources`).
