# DellNativeEdge — edge-orchestration digital twin

Same architecture as the other twins in this repo, applied to **Dell
NativeEdge** — Dell's edge operations software platform (2023; 2.0 in 2024;
now also the basis of Dell Distributed Private Cloud). It manages estates
of servers, gateways, workstations, and desktops deployed *outside* the
datacenter: factory floors, retail branches, substations, ships, trackside
garages. Built from `initial_spec.md` (loop iteration 1's spec), post-loop.

The one idea: **nobody touches the device.** Every hardware twin in this
repo assumes a person at the moment of truth — someone presses the R760's
power button, racks the XE9712, plugs in the Alienware. Edge estates break
that assumption at scale: four hundred sites, no IT staff at any of them.
NativeEdge inverts the direction of trust — the device wakes, proves
cryptographically that it is the machine Dell built, and asks the central
Orchestrator what it is supposed to become. `operatorActions` is this
twin's `droppedPackets`: it exists to be **1** (power and a network cable)
and never increments again.

Like the CloudIQ twin, the subject is software, so both metaphors adapt:
the "anatomy" is a platform architecture diagram (a uniform band of
identical endpoints → WAN → secure onboarding → the singular Orchestrator →
blueprints, catalog, policy, observability), and the "power-on trace" is
the **zero-touch onboarding of one site** — sealed crate to managed estate.

```
backend/   app/{models,anatomy,engine,catalog,usecases,leveling,main}.py + tests/
frontend/  src/{api,types,level}.ts, App.tsx, components/{PlatformView,ArchitecturePage,
           CatalogPage,UseCasePage,OnboardControls,OnboardCounters,LevelControl}.tsx
scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./scripts/start_all.sh` (backend :8014 background, frontend :5187
  foreground — the ports the spec reserved). Stop: `./scripts/stop_all.sh`.
- Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8014`. Trace endpoint is
  `GET /api/onboard` returning `OnboardResponse`. Pages hash to
  `#architecture` / `#capabilities` / `#usecases` (CloudIQ style).

Key invariants (enforced in `backend/tests/`):

- **Exactly one human action** — `operatorActions` is 0 before the `power`
  phase, 1 there, and 1 forever after. The twin's reason for existing.
- **Nothing runs before trust is established** — no endpoint counts as
  online and no workload phase is reached until attestation passes;
  zero-touch without attestation is just an unauthenticated machine on
  your network.
- **Trust is never revoked mid-sequence** (monotone once established).
- **The Orchestrator is never the thing being onboarded** — it is excluded
  from `endpointsOnline`, which tops out at exactly the anatomy's endpoint
  count.
- **The estate scales in lockstep** — endpoint regions light together; a
  site is provisioned as a set.
- **Attestation is the longest stage** (unique max `cycleCost`) — proving
  integrity is genuinely the slow part, dwelt on rather than skipped.
- **Geometry carries the lesson** — the endpoint band is uniform (N ≥ 4:
  an estate is one building block repeated), the Orchestrator is singular,
  central, and the largest block, and the estate sits strictly left of the
  control plane.

Referenced by `CustomerSetup/McLarenRacing/` as the trackside
edge-management block (representative — McLaren's sources name trackside
operations, not the tooling). Cross-references: `DellProMaxPlus/` (its
disconnected field engineer's laptop is one endpoint in this estate),
`DellCloudIQ/` (NativeEdge deploys and enforces; AIOps watches and
predicts), `DellIDRAC/` (the same "device brings itself up before anyone
arrives" idea, one machine at a time), and `DellFortZero/` (the Zero Trust
argument this platform applies per endpoint).
