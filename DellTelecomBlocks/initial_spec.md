# DellTelecomBlocks — Open RAN / telecom cloud digital twin (spec)

Status: **spec only.** Chosen in loop iteration 2 as one of the top three
untwinned Dell products; PowerFlex was built first. Build this one by
following the pattern in `DellPowerSwitchE3200/` and `DellPowerFlex/`.

## Subject

**Dell Telecom Infrastructure Blocks** (for Red Hat, and the wider Dell
Telecom portfolio / Cloud Core) — pre-integrated hardware, software, and
automation for building a cloud-native 5G network from core to edge to
radio access network (RAN). Built on PowerEdge XR-series servers with a
telecom Kubernetes platform, plus the **Dell Telecom Infrastructure
Automation Suite** for zero-touch RAN deployment.

## The one idea

**The deadline is the product.**

Every other twin in this repo optimizes a rate: bytes per second, tokens
per second, IOPS, watts. A radio access network does not have a rate
target; it has a *deadline*, imposed by physics and by the 3GPP standards
that encode it. A radio frame arrives every millisecond, and the processing
for it must finish before the next one lands. Finish early and nothing is
gained. Finish late and the frame is simply gone — there is no queue, no
retry, no graceful degradation. The subscriber experiences it as a dropped
call.

That is a strange and specific thing to ask of general-purpose servers, and
it is exactly what Open RAN asks. Disaggregation moved signal processing
off purpose-built appliances and onto x86 boxes running Kubernetes, which
means every ordinary cloud-native convenience — a scheduler that migrates
pods, a kernel that preempts, a NIC that buffers, a neighbouring container
that gets busy — becomes a threat to a hard real-time budget.

So this twin's invariant is not throughput. It is: **no step in the trace
ever exceeds its budget**, and the interesting counter is not how fast the
work went but how much margin was left.

## Metaphor mapping

- **"Anatomy"** → a left→right functional split of a disaggregated RAN:
  the radio unit (RU) at the antenna, the fronthaul link, the distributed
  unit (DU) with its real-time signal processing and accelerator, the
  midhaul, the centralized unit (CU), the backhaul, and the 5G core — with
  the orchestration and automation plane drawn beneath. Geometry should
  carry the lesson: each element's horizontal position is its *distance
  from the antenna*, and a `test_anatomy.py` should pin that the DU sits
  strictly closer to the RU than the CU does, because latency budget is
  literally a distance constraint here. Fronthaul is the tightest link and
  should be drawn shortest.
- **"Power-on trace"** → one radio frame's journey and the budget it burns,
  followed by a load spike that must not break it.

## Proposed model shapes

`NetworkAnatomy` / `NetworkRegion` / **`FrameState`**.

```
RegionKind = radio | fronthaul | du | accelerator | midhaul
           | cu | core | orchestration | timing
```

Note `timing` — precision time protocol distribution. Every element must
agree on what time it is to within microseconds, or the radio transmits in
the wrong slot. It deserves its own kind and its own region because it is
the least visible and most disruptive thing in the system.

`FrameState` carries:

- `budget_microseconds: int` — the deadline for this step
- `elapsed_microseconds: int` — what it actually took
- `margin_microseconds: int` — the derived headroom, **never negative**
- `frames_dropped: int` — **exists to be zero**
- `subscribers: int` — load
- plus the standard `step / phase / label / description / active_regions /
  cycle_cost`

## Proposed phases

`idle → sync → uplink → fronthaul → duprocess → midhaul → cuprocess → core → spike → held`

- `sync` — precision timing locks; nothing may transmit before the
  elements agree on the clock
- `uplink` — a subscriber's radio frame arrives at the antenna
- `fronthaul` — digitized samples cross the tightest link in the system
- `duprocess` — the real-time signal processing, offloaded to an
  accelerator; the largest single slice of the budget
- `midhaul` / `cuprocess` — less latency-critical layers
- `core` — the packet reaches the 5G core
- `spike` — a load surge (a stadium emptying); the budget does not move
- `held` — the deadline is still met under load, with less margin

## Signature invariants to enforce (backend/tests/test_engine.py)

1. **`test_no_step_ever_misses_its_deadline`** — for every state,
   `elapsed_microseconds <= budget_microseconds`, and
   `margin_microseconds == budget - elapsed` and is `>= 0`. The twin's
   reason for existing.
2. **`test_frames_are_never_dropped`** — `frames_dropped == 0` on every
   step, including under the load spike. A missed frame is not recoverable,
   so the system's job is to never be late rather than to catch up.
3. **`test_the_spike_actually_consumes_margin`** — the claim is only
   interesting if it is tested: the spike step must reduce margin to below
   some fraction (say 25%) of the idle margin, so "meets the deadline" is
   demonstrated under stress rather than asserted at rest.
4. **`test_nothing_transmits_before_timing_locks`** — no phase after `sync`
   may be reached with the timing region inactive during `sync`; and no
   frame processing occurs before the sync phase. Clock discipline is not
   optional here.
5. **`test_fronthaul_is_the_tightest_budget`** — the fronthaul step has the
   smallest `budget_microseconds` of any transport step, which is why it
   constrains where a DU can physically sit.
6. **`test_du_processing_is_the_largest_slice`** — unique max
   `cycle_cost`; the UI dwells where the budget actually goes.
7. **`test_margin_never_increases_under_load`** — from the spike onward,
   margin does not recover within the trace; the system holds, it does not
   magically improve.
8. Standard: phase order never regresses, steps sequential, active regions
   exist, engine purity (AST-checked).

## Catalog (~10 categories, backend data)

Server platform (PowerEdge XR8000 and rugged edge SKUs), RAN
disaggregation split (which functions sit in RU / DU / CU), acceleration
(inline vs lookaside accelerators for layer-1 processing), the telecom
Kubernetes platform (Red Hat OpenShift and Advanced Cluster Management),
timing and synchronization (precision time protocol, GNSS), fronthaul
transport, automation (Telecom Infrastructure Automation Suite, zero-touch
RAN deployment), the 5G core, energy efficiency (RAN is a large share of an
operator's power bill), and validated designs and support.

## Use cases (3)

1. A national operator deploying thousands of cell sites with zero-touch
   provisioning, because sending an engineer to each is impossible.
2. A private 5G network inside a factory, where the latency budget serves
   robots rather than phones.
3. RAN energy optimization — powering down capacity layers overnight
   without breaking the deadline for the traffic that remains.

## Cross-references to keep intact

- **DellNativeEdge** (spec, iteration 1) — zero-touch deployment at scale
  is the same instinct; a cell site is an edge site with a harder clock.
  Both specs should point at each other.
- **DellPowerSwitchE3200** — the ONIE/disaggregated-network-OS story;
  Open RAN is that idea applied to radio instead of switching.
- **DellPowerSwitchSN6000** — losslessness under bursty load, with the
  difference that a fabric can pause and a radio frame cannot.
- **DellProMaxPlus** — the other twin about a deadline the user can feel,
  reached from the opposite direction (sustained rate rather than hard
  real time).

## Ports

Backend **:8017**, frontend **:5190** (after DellPowerFlex's 8016/5189).
Trace endpoint `GET /api/frame` returning `FrameResponse`.

## Sources

- <https://www.dell.com/en-us/lp/dt/industry-telecom-infrastructure-blocks>
- <https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2024~02~dell-technologies-telecom-solutions-accelerate-network-cloud-transformation.htm>
- <https://www.delltechnologies.com/asset/en-us/solutions/service-provider-solutions/technical-support/telecom-multi-cloud-foundation-with-telecom-infrastructure-blocks-for-red-hat-spec-sheet.pdf>
- <https://www.rcrwireless.com/20250424/telco-cloud/dell-cloud-core>
