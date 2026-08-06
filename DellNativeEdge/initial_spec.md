# DellNativeEdge — edge-orchestration digital twin (spec)

Status: **built** (2026-08-06, post-loop — see `LOOP_LOG.md`). The twin
follows this spec as written; this file is kept as the design record.
Chosen in loop iteration 1 as one of the top three untwinned Dell
products; the Pro Max Plus was built first.

## Subject

**Dell NativeEdge** — Dell's edge operations software platform (2023,
2.0 in 2024, AI updates through 2026; now also marketed as the basis of
Dell Distributed Private Cloud). It manages estates of servers,
workstations, gateways, and desktops deployed *outside* a datacenter:
factory floors, retail branches, substations, ships, hospitals.

## The one idea

**Nobody touches the device.**

Every other twin in this repo assumes a person is present at the moment of
truth — someone presses the power button on the R760, racks the XE9712,
plugs in the Alienware, cables the SN6000. Edge estates break that
assumption at scale: there are four hundred sites, no IT staff at any of
them, and the person who unboxes the machine is a shop manager whose job is
not this.

So NativeEdge inverts the direction of trust. The device is not
provisioned *by* someone; it wakes up, proves cryptographically that it is
the machine Dell built and shipped, and asks a central Orchestrator what it
is supposed to become. The only human action in the entire sequence is
supplying power and a network cable. Everything downstream — validation,
onboarding, OS, workload, policy — is pulled, not pushed.

That inversion is what the trace should make visible, and the invariant
that carries it is: **no state in the trace requires a local operator.**

## Metaphor mapping

Following the CloudIQ twin (software, not a box), both metaphors adapt:

- **"Anatomy"** → a platform architecture diagram, drawn left→right:
  edge endpoints (the far left, many and identical) → secure onboarding /
  device identity → the NativeEdge Orchestrator → the application catalog
  and blueprints → policy, Zero Trust, and observability (the right).
  Geometry should carry the lesson the way Exascale's does: the
  Orchestrator sits *central and singular* against a band of many identical
  endpoints, and a `test_anatomy.py` should pin that the endpoint band is
  uniform (same kind, same size, N ≥ 4) — an estate is one building block
  repeated.
- **"Power-on trace"** → the zero-touch onboarding of one endpoint, from
  a sealed box to a running workload.

## Proposed model shapes

`PlatformMap` / `PlatformRegion` / **`OnboardState`**, wire-compatible with
the other twins.

```
RegionKind = endpoint | identity | orchestrator | blueprint
           | catalog | policy | observability | network
```

`OnboardState` carries:

- `endpoints_online: int` (0 → N) — the counter that matters
- `operator_actions: int` — **exists to be 1** (power and network), and
  never increments again. This twin's `droppedPackets`.
- `progress_percent: int` (0 → 100)
- `trust_established: bool`
- plus the standard `step / phase / label / description / active_regions /
  elapsed_seconds / cycle_cost`

## Proposed phases

`crated → power → attest → onboard → provision → blueprint → workload → managed`

- `crated` — the box arrives at the site; nothing is configured
- `power` — power and network applied; the *only* human action
- `attest` — the device proves hardware integrity and identity against
  what Dell built (secure device onboarding)
- `onboard` — the Orchestrator recognizes it and claims it into the estate
- `provision` — OS and platform software land
- `blueprint` — the declarative description of what this site runs is
  applied
- `workload` — applications from the catalog (or the customer's own) start
- `managed` — steady state: policy enforced, telemetry flowing, lifecycle
  automated

## Signature invariants to enforce (backend/tests/test_engine.py)

1. **`test_exactly_one_human_action`** — `operator_actions` is 0 before the
   `power` phase, becomes 1 there, and is 1 for every subsequent step. The
   twin's reason for existing.
2. **`test_nothing_runs_before_trust_is_established`** — no workload phase
   is reached, and `endpoints_online` stays 0, until `trust_established`
   is true. Zero-touch without attestation is just an unauthenticated
   machine on your network, and the trace should refuse to pretend
   otherwise.
3. **`test_trust_is_never_revoked_mid_sequence`** — once true, stays true.
4. **`test_the_orchestrator_is_never_the_thing_being_onboarded`** — the
   orchestrator region is active during onboarding phases but is never
   counted in `endpoints_online`.
5. **`test_estate_scales_in_lockstep`** — during provisioning, endpoint
   regions light together (an estate is provisioned as a set, not
   individually).
6. **`test_attestation_is_the_longest_stage`** — unique max `cycle_cost`;
   proving integrity is genuinely the slow part, and the UI should dwell
   there rather than skipping the security step as boilerplate.
7. Standard: phase order never regresses, steps sequential, elapsed
   strictly increasing, active regions exist in the anatomy, engine purity
   (AST-checked).

## Catalog (~10 categories, backend data)

Endpoint hardware (PowerEdge XR-series, gateways, workstations,
Precision), device identity and secure onboarding, the Orchestrator
(deployment model, high availability), blueprints and automation,
application catalog and independent-software-vendor workloads, Zero Trust
and security policy, networking and connectivity (intermittent, satellite,
private 5G), observability and CloudIQ/AIOps integration, edge AI
inference, services and validated designs.

## Use cases (3)

1. Four hundred retail branches provisioned by shop managers who are told
   only "plug in the black cable".
2. A manufacturing line running a computer-vision quality-inspection model
   at the edge, updated centrally without a site visit.
3. Distributed private cloud across a utility's substations, where
   connectivity is intermittent by design.

## Cross-references to keep intact

- **DellProMaxPlus** — its third use case (the disconnected field engineer)
  names NativeEdge explicitly as the fleet-management answer for keeping a
  model current on machines that are rarely connected. That laptop is one
  endpoint in this estate.
- **DellCloudIQ** — the observability half; NativeEdge deploys and
  enforces, CloudIQ watches and predicts.
- **DellIDRAC** — the same "the device brings itself up before anyone
  arrives" idea, one machine at a time instead of four hundred.

## Ports

Backend **:8014**, frontend **:5187** (next free after DellProMaxPlus's
8013/5186). Trace endpoint `GET /api/onboard` returning `OnboardResponse`.

## Sources

- <https://www.dell.com/en-us/dt/solutions/edge-computing/edge-platform.htm>
- <https://www.dell.com/en-us/blog/announcing-dell-nativeedge-2-0-reimagining-edge-operations/>
- <https://www.dell.com/en-us/blog/unlocking-the-edge-the-latest-innovations-from-dell-nativeedge/>
- <https://infohub.delltechnologies.com/en-us/l/introduction-to-the-dell-nativeedge-software-platform-white-paper-4/nativeedge-orchestrator-11/>
- <https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2023~05~dell-nativeedge-software-transforms-edge-operations.htm>
