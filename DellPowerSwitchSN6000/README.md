# DellPowerSwitchSN6000 — AI-fabric digital twin (fourteenth component)

A digital twin of the **Dell PowerSwitch SN6000** series — NVIDIA
Spectrum-6 silicon, 1.6 Tb/s ports, up to 409.6 Tb/s of switching capacity
and 2,048 breakout connections, with liquid cooling and co-packaged optics
options, optimized for NVIDIA Spectrum-X Ethernet. Globally available from
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
  convergence) then a training step's all-reduce, the incast it provokes,
  and adaptive routing clearing it: 98% → 71% on the hot link while total
  throughput *rises* from 24 to 31 Tb/s.
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
