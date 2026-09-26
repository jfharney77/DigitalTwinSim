# DellPowerSwitchSN6000 — AI-fabric digital twin (fourteenth component)

A digital twin of the **Dell PowerSwitch SN6000** series — NVIDIA
Spectrum-6 silicon, 800 Gb/s ports (two per 1.6 Tb/s cage; Dell's
announcement headlines the series as 1.6 Tb/s), 102.4 Tb/s per ASIC and up to
409.6 Tb/s of switching capacity and 2,048 breakout connections in the
four-ASIC SN6800-LD, with liquid cooling and co-packaged optics options, optimized for NVIDIA Spectrum-X Ethernet. Globally available from
July 2026.

The **fabric** pillar of the AI Factory quartet in this repo — compute
(XE9712), cooling (IR7000), data (Exascale), fabric (this). Unlike the
E3200 twin (one campus switch booting), the subject here is the *fabric*
several switches form.

## The one idea

An AI fabric's product is **what it refuses to do**. Ordinary Ethernet
drops packets when a buffer fills and lets senders retransmit. In
distributed training, where every GPU must finish the same all-reduce
before any can start the next step, one retransmission stalls the entire
fleet — so this fabric signals congestion early (ECN), pauses selectively
(PFC), and spreads flows across the alternate paths leaf/spine holds in
reserve. `droppedPackets` is zero on every step of the trace, including at
98% link utilization, and `test_engine.py` asserts it.

## What it shows

- **Fabric in motion** (`/`) — bring-up (power, link training, routing
  convergence) then a training step's all-reduce, the many-to-one traffic
  that overloads one spine downlink (a link with an alternate path, which is
  why routing can help; a last-hop incast is left to congestion control), and
  adaptive routing clearing it: 98% → 71% on the hot link while total
  throughput rises from 24 to 31 Tb/s. The panel shows what zero drops costs:
  ECN-marked packets and PFC pauses.
- **Inside the fabric** (`/#anatomy`) — leaf/spine topology with the mesh
  drawn from the region data: spines, leaves, GPU racks, optics, congestion
  control, cooling, management.
- **Components & options** (`/#components`) — switch platform, topology and
  oversubscription, lossless/congestion control, optics (CPO vs pluggable),
  endpoints and SuperNICs, collective acceleration, cooling, management,
  services.
- **Use cases** (`/#usecases`) — scale-out fabric for an eight-rack
  training cluster, storage fabric for a parallel file system, multi-tenant
  AI cloud.

## Run

```
./DellPowerSwitchSN6000/scripts/start_all.sh   # backend :8012, frontend :5185
./DellPowerSwitchSN6000/scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Key invariants (backend/tests/)

- Engine purity (AST-checked); the playback clock lives in `App.tsx`.
- Phase order `off→power→linktrain→topology→ready→collective→congestion→
  reroute→steady` never regresses.
- **Zero packet loss on every step** — the defining property.
- **Congestion is real**: the congestion step must drive the busiest link
  to ≥95%, so the lossless claim is actually tested.
- **Adaptive routing relieves without losing work**: after the reroute the
  hot link is cooler *and* total throughput has not fallen.
- No traffic before links train and routing converges; spine and leaf tiers
  light in lockstep during bring-up; any traffic crosses both tiers (two
  hops); link training is the longest stage.
- Anatomy: tiers vertically ordered (spines above leaves above endpoints),
  uniform sizing within each tier, matched leaf/endpoint counts.

Capacities and timings are illustrative, anchored to Dell's SN6000 spec
sheet and the 2026 AI Factory announcements (see anatomy `sources`).

## Failure scenario: the gray link

The healthy trace proves the fabric never discards a packet for want of
buffer. The second trace, `GET /api/fabric?scenario=gray-link` (listed by
`GET /api/scenarios`, deep link `/#scenario=gray-link`, which composes as
`/#scenario=gray-link&phase=blind`), is the failure that guarantee does not
cover. One leaf-to-spine optic degrades. Forward error correction hides the
first errors; then bursts outrun it, corrupt frames fail the frame check at
the receiving port, and the NICs retransmit. The link never goes down, so
link state reads 8 of 8 up while the all-reduce stretches from 120 ms to
205 ms. Per-link error counters (NIC RoCE retransmits, switch symbol errors)
name the port, an operator withdraws routing from the link so it leaves the
equal-cost group adaptive routing sprays across (the link stays up), then
shuts the port, the optic is replaced, and the link retrains.

Phases: `steady→degrade→blind→telemetry→steer→drain→replace→restored`. The
hero number is `collectiveMs`. `FabricState` gained only defaulted fields
(`sickLink`, `sickLinkStatus`, `sickLinkLocated`, `trafficSteered`,
`symbolErrorsPerSec`, `retransmitsPerSec`, `collectiveMs`), and
`tests/test_gray_link.py` pins the healthy trace to its earlier hash.

What the tests hold, because the failure happened:

- `droppedPackets` is still zero. It counts congestion loss; corruption loss
  is counted separately as retransmits, because the cure is different.
- The sick link reports `up` and is unlocated on every blind step, while the
  damage is demonstrably present (all-reduce ≥1.5× baseline, retransmits
  nonzero, no link saturated). Both halves are asserted.
- Finding the link fixes nothing: throughput on the telemetry step equals
  the blind steps. It recovers at `steer` and not before.
- Steer precedes drain, so the shutdown costs no work, and the link's status
  sequence is exactly `up → admin-down → training → up` — it never goes down by
  itself.
- Seven uplinks are not eight: throughput stays below healthy until the
  repair, and never exceeds healthy capacity.
- The blind hunt is the unique longest stage.
- Symbol errors need a live link and retransmits need job traffic on it;
  the steer and drain steps show the management plane acting, because
  adaptive routing never leaves a corrupting link unprompted.

`FabricView.tsx` draws the sick link like the other seven until
`sickLinkLocated` is true, then in the diagram's error colour (`--core-hot`).
Keep that if you touch the component; marking the link early undoes the
lesson. Adaptive routing does not rescue the fabric unaided here, and the
prose says why: it selects paths by congestion, a corrupting link is not
congested, and per-packet spraying puts every flow through that leaf across
it.

Behaviour follows NVIDIA's Spectrum-X telemetry write-up (symbol errors
pinpointed on one spine port of Israel-1; disabling the port restored
bandwidth), NVIDIA's fabric-resiliency write-up (NCCL has no heavy error
recovery) and the SprayCheck paper on gray failures under adaptive routing.
NVIDIA's account disables the port directly; splitting the recovery into
"withdraw routing, then shut the port" is ordinary operator practice (RFC
8326), not something that write-up describes. Disabling adaptive routing on
the port would not drain it, since the port stays an equal-cost next hop
(Cumulus Linux ECMP documentation). A link that errs badly enough is taken
down by its own physical layer; the gray window modelled here sits below
that threshold. Each drawn uplink stands for a bundle of eight 800 Gb/s
links, so the gray optic is one member of leaf 2's bundle to spine 1: the
corruption behaves as drawn, but the recovery drains the whole drawn uplink
where an operator would shut the one erring port, which makes the capacity
dip from `steer` on a worst case. Step 0's text says so. The URLs ride on the scenario data. Rates, error counts and times are
illustrative. `PhysicsFabric/` has the same fault as a toggle with a dial.
The guided tour stays on the healthy trace.
