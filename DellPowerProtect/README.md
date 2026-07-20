# DellPowerProtect — data-protection digital twin (twelfth component)

A digital twin of **Dell PowerProtect Data Domain** (the purpose-built
backup appliance, all-flash as of September 2025) and **PowerProtect Cyber
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

This twin closes a loop the PowerMax twin opened — its cyber-resiliency
vault use case is, concretely, this architecture. Capacities, ratios, and
timings are illustrative, anchored to Dell's 2025 PowerProtect
announcements (see anatomy `sources`).
