# DellNativeEdge — edge-orchestration digital twin

Same architecture as the other twins in this repo, applied to **Dell
NativeEdge** — Dell's edge operations software platform (2023; 2.0 in 2024;
renamed Dell Distributed Private Cloud in May 2026). It manages estates
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

- **Exactly one on-site human action** (one site, four devices; central voucher and blueprint work is named, not counted) — `operatorActions` is 0 before the `power`
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

## Failure scenario: one device fails attestation

`GET /api/onboard?scenario=attestation-fails` serves a second pure trace
(`backend/app/scenarios.py`); `GET /api/scenarios` lists what can be
selected. Without the parameter the endpoint returns the happy path, byte
for byte what it returned before (pinned by digest in
`backend/tests/test_scenarios.py`). On the sim page the Scenario picker sits
above the playback buttons, and `#scenario=attestation-fails` deep-links to
it, composing with `&phase=<name>` or `&step=N`, for example
`/#scenario=attestation-fails&phase=quarantine`.

The story: four devices are plugged in and one cannot prove it is the
machine Dell built for this tenant. Its boot measurements are off, or its
ownership voucher names another owner. It is quarantined, drawn in the error
colour, and receives nothing. The other three onboard on the happy path's
schedule. The failed unit is returned and a replacement is plugged in, which
is a second human action and is counted as one (`recoveryActions`), while
`operatorActions` keeps its ceiling of one.

Phase order: `crated → power → attest → quarantine → onboard → provision →
blueprint → workload → managed → replace → recovered`. The state is
`ScenarioState`, an `OnboardState` with four added fields: `endpointTrust`
(a verdict per device), `failedEndpoints`, `deployedTo` and
`recoveryActions`.

What must hold because the failure happened:

- **Nothing is deployed to an unattested device.** Every id in `deployedTo`
  has a true verdict of its own on that step, and the quarantined endpoint
  is never lit during provision, blueprint, workload or managed.
- **One bad device never blocks the estate.** The healthy three reach every
  phase at the same `elapsedSeconds` as on the happy path, and are managed
  before any recovery work starts.
- **Trust is per device.** Every step carries a verdict for all four
  endpoints, healthy trust is never revoked, and the failed hardware is
  never trusted: the slot only turns trusted after a swap.
- **The failure is real.** A test asserts a device is in fact quarantined,
  so the other assertions are not passing on an empty set.

Sourced from Dell documentation (URLs in the scenario data and shown under
the diagram): the voucher mismatch and its event text (KB 000216857, event
0x00301006, "Public Key of the voucher is not matching NativeEdge
Orchestrator"), the endpoint not appearing in the Orchestrator's onboarding
list, the Device Attestation Key in the TPM, the minimal factory OS, and the
central fix for an Orchestrator-side key change (rotate the identifier,
reboot the endpoint), and whole-unit replacement with Dell's voucher system
associating the new unit's voucher with the customer account (NativeEdge
Service Manual). Illustrative: a single device failing on its own (the KB
documents that event only with the Orchestrator-side cause, which would not
single out one box), the tampered-firmware variant, the word "quarantine"
(the twin's, not Dell's), every timing, the three-day replacement, and
recovery compressed into one step. `recoveryActions` counts on-site human
actions; the administrator's support case with Dell is central work and is
described in the prose, not counted.

The guided tour narrates the happy path only. Its steps drive the shared
playback cursor by index, so opening the tour switches the sim back to the
happy-path trace.
