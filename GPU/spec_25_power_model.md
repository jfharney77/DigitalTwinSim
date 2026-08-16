# spec_25 — per-phase power & energy model (illustrative watts, calibrated by your die)

**Status:** proposed.
**Builds on:** `spec_04_bandwidth_model.md` (cycle_cost/stalled/Summary),
`spec_08_cuda_live_cobrowse.md` (gpu_sample already carries `powerW`),
`spec_15_measured_roofline.md` (the measurement store this spec reuses).
**House rules honored:** engine stays pure (AST-checked), the clock stays in the
frontend, invariants land as pytest, everything is illustrative-not-cycle-accurate,
and every constant is labeled an estimate.

---

## 0. Why this is the right next step

spec_04 taught *time*: a memory-bound workload makes the cores wait. What it never
says is what the waiting *costs*. The missing lesson is energy: **a stalled die is
not a free die.** While a LOAD dwells, the chip still burns its idle floor plus the
memory watts moving the tile — and `macDone` stands perfectly still. That is the
real reason memory-bound is wasteful, and it is one line of arithmetic away from
data the trace already carries. The Live tab has streamed real `powerW` from
`twin-sampler` since spec_08; the simulator has never had a watts number to hold it
against. This spec gives the sim its watt, gives the ledger its joules, and wires
the spec_15 calibration bridge a second metric.

---

## 1. The model (three constants, one line)

Per-profile power constants as **data** (`profiles.py`), a new `Power` block on
`GpuProfile` beside `Bandwidth`:

- `idle_w` — the floor the die burns doing nothing.
- `lane_w` — added watts per active lane during compute.
- `byte_w` — added watts per byte moved per modeled cycle while `mem_active`.

Per state, derived **purely from fields `SimState` already has**:

```
powerWatts = idle_w
           + lane_w * active_cores                      # math costs
           + byte_w * (bytes_this_state / cycle_cost)   # movement costs (0 if !mem_active)
```

Deterministic, no clocks, no randomness — `engine.py` keeps passing its AST purity
test untouched. A stalled LOAD state therefore reads `idle + memory` watts with
zero MAC progress: the wasteful regime is now a *number*, not just a dwell.

**Fleet honesty.** Constants are teaching estimates, but their **ratios are
honest** across the profiles: `RTX-4060-Laptop` tops out near a laptop's ~80 W
envelope, `H100-SXM` near ~700 W, `B300-Blackwell-Ultra` near ~1.4 kW, with idle
floors in believable proportion (a few watts on the laptop, tens on the SXM
parts). Each constant carries a comment in `profiles.py` naming its anchor (vendor
TDP/TGP figure) and stating it is an estimate — the `constants.py` discipline from
`DellPowerEdgeR760Thermal/`, applied at profile scope. `Power` gets a default so
older profiles and tests keep working, exactly as `Bandwidth` did in spec_04.

---

## 2. The energy ledger

Modeled time is `cycle_cost`, so energy is the obvious sum:

```
joules = Σ over trace ( powerWatts * cycle_cost )        # "cycle" as the time unit
```

`Summary` (spec_04's block) grows three fields: `energy_joules`,
`avg_power_watts` (energy ÷ Σ cycle_cost), and the teaching number
**`joules_per_mac`** (energy ÷ macTotal) — this sim's tokens-per-joule. The
payoff mirrors spec_04's regime flip: shrink the tile and watch `joules_per_mac`
climb even though `macTotal` is identical — same math, more energy, because the
die idled hot through more dwelling loads. For `mlp_step`, energy-per-training-step
is the same quotient over the per-step slice; no new machinery.

Units stay frankly modeled: a "cycle" here is spec_04's illustrative cycle, so
joules are illustrative joules. The *comparisons* (tile A vs tile B, fp32 vs fp16,
serial vs double-buffered) are the product; the absolute magnitudes are not.

---

## 3. Invariants (pytest, house style)

New `tests/test_power.py`, in the conservation-identity idiom:

- **The ledger closes exactly:** `summary.energy_joules == Σ state.powerWatts *
  state.cycle_cost` over the full trace — no tolerance, every workload, every tile
  size, both workload kinds.
- **Power lives in the envelope:** `idle_w <= powerWatts <= envelope_w` on every
  state, where `envelope_w = idle_w + lane_w * total_cores + byte_w *
  bytes_per_cycle` (the profile's derived ceiling).
- **Stalls burn without progressing:** on every `stalled` state, `powerWatts >
  idle_w` while `mac_done` is unchanged from the previous state — the lesson as an
  assertion.
- **Reuse saves energy:** for a fixed N, the whole-matrix trace's
  `joules_per_mac` ≤ the smallest-tile trace's; `double_buffer=True` never costs
  more joules than serial for the same workload.
- **Fleet ratios hold:** H100 `envelope_w` > 5× the 4060's; B300 > H100; every
  profile's `idle_w < envelope_w`. Determinism: same inputs → same joules.
- Purity: the existing AST check keeps covering `engine.py`; power adds no import.

---

## 4. Calibration hook (spec_15's bridge, second metric)

`twin-sampler` already streams `gpu_sample.powerW` into live sessions. Add a
`peak_power_w` metric to the spec_15 measurement path: when a lesson kernel runs
under sampling, the max sampled watts over the kernel window is emitted as a
`measurement` event (transport edge, not the pure fold — same rule as
`stream_gbps`) and lands in `backend/sessions/measurements.json`. The sim's power
read-out then renders both lines, spec_15's exact copy pattern:

> model ~80 W (illustrative) · your die measured 67 W (2026-08-15)

Sim watts are always labeled **illustrative**; measured watts are **your die**,
dated. The measurement never alters the trace or the constants — it annotates,
as the measured roofline does. `GET /api/measurements` needs no new route.

---

## 5. UI — no dashboard creep

`Counters.tsx` only: a **watts read-out** (current state's `powerWatts`, envelope
alongside) and an **energy counter** (joules so far at the cursor, computed by the
same replay-to-cursor walk `MatrixPanels` already does; `joules_per_mac` appears in
the Summary card next to the regime badge). The calibration line renders only when
a measurement exists — identical to today when empty, per spec_15. No charts, no
gauges, no new panel; the power story is three numbers and one honest label.

---

## 6. Test plan

1. `test_power.py` invariants of §3 (ledger identity, envelope bounds, stall
   burn, reuse ordering, fleet ratios, determinism).
2. Existing suites untouched and green — `Power` is additive with a default, so
   spec_01–06 traces are byte-identical apart from the new fields.
3. Measurement ingest: `peak_power_w` accepted (finite, > 0), persisted, returned
   by `/api/measurements`; unknown metrics still rejected. Pure fold untouched —
   extend the spec_15 pass-through test, not the fold.
4. Frontend: `npm run build`; Counters render with and without a measurement.

## 7. Open questions

- Should `dtype` scale `lane_w` (fp16 MACs are cheaper)? Defer — spec_04 already
  rewards low precision through fewer bytes; a second lever can wait for the
  tensor-core spec.
- Report `mlp_step` per-op energy in `MlpInfo`? Cheap, but the Summary quotient
  teaches the same thing; add only if the op strip grows a read-out organically.

---

## Implementation notes (2026-08 — as landed)

The code had moved since this spec was written: spec_22 (rectangular matmul),
spec_23 (tensor mode), spec_24 (occupancy on Summary), and spec_26 (llm_decode)
all landed first. Where this file and the code disagreed, the code won; the
deliberate decisions are recorded here.

**The per-state formula, as shipped.** `SimState` carries no `bytes_this_state`
field, and the hard rule was to derive watts purely from fields the state
already has. So:

```
powerWatts = idle_w
           + (0 if stalled else lane_w * active_cores)
           + (byte_w * bandwidth.bytes_per_cycle if mem_active and not prefetching else 0)
```

- The `bytes/cycle_cost` quotient of §1 is `bytes_per_cycle` to within the
  final partial memory beat (`cycle_cost = ceil(bytes/bpc)`), so foreground
  memory states charge `byte_w · bytes_per_cycle` flat. Deterministic, bounded
  by the envelope, and the stalled-LOAD state reads exactly the promised
  `idle + memory` — stalled lanes are parked, so they burn no `lane_w` (this
  is also what keeps the formula consistent with §1's own worked example).
- **Prefetching compute states (spec_05) burn lane watts but no memory
  watts.** Charging `byte_w · bpc` for every overlapped compute state would
  bill by *duration*, not by *bytes*, and for cheap-load/long-compute corners
  (e.g. fp4 tiles on the B300's 24 B/cycle bus) it would make double-buffering
  read as costing *more* energy than serial — reversing the lesson. The
  simplest honest state-local rule undercounts the hidden loads' bytes
  instead; `test_double_buffering_never_costs_more_joules` pins the ordering,
  fp4/tensor corner included.
- **Tensor mode (spec_23):** an `mma` state's lanes are active lanes and burn
  `lane_w` like any others — no per-dtype `lane_w` scaling (§7's deferral
  stands; spec_04 already rewards low precision through fewer bytes). The
  energy win shows up exactly where it should: tensor mode finishes the same
  MACs in fewer compute states, so `energy_joules` and `joules_per_mac` fall.

**The ledger.** `engine.attach_energy(summary, trace)` closes the ledger —
`Σ powerWatts × cycle_cost`, plain sum, no tolerance — and `main.py` stamps it
onto every kind's Summary (matmul, mlp_step, llm_decode) after the trace
exists. `analyze()` alone is trace-free and leaves the three fields at their
0.0 defaults; that is deliberate, not a gap. `mlp.py`/`llm.py` sub-trace
states keep their engine-stamped watts through `model_copy` restamping
(restamped fields don't feed the formula), and their bookend/pointwise states
stamp power through the same shared `models.state_power_watts`.

**Calibration.** No new route — `test_api_surface_snapshot`'s 23 routes are
untouched. `MeasurementMetric` grew `"peak_power_w"`, fed from
`gpu_sample.powerW` two ways: tooling may POST the measurement directly
(lesson-06 style), and `live_store` derives it at the transport edge — the
max sampled watts seen after the session's first `kernel_launch`, recorded to
`measurements.json` when the session stops. The pure fold is untouched.

**Constants, as landed** (all labeled estimates in `profiles.py`; anchors are
public TDP/TGP figures): 4060-Laptop 5/0.02/3.0 → ~78 W envelope; H100-SXM
60/0.13/6.0 → ~705 W; B300 90/0.22/8.0 → ~1408 W; RTX-5090 30/0.093/5.0 →
~576 W; MI300X 65/0.121/6.0 → ~750 W; generic dies keep the `Power` model
defaults (10/0.5/2.0), as they keep `Bandwidth`'s.

**UI.** Confined to `Counters.tsx` as specced: a watts read-out with the
envelope alongside, an energy-so-far counter (replay-to-cursor sum — the
component now takes `trace`/`cursor` props for that walk), `joules/MAC` in
the Summary card beside the regime badge, and the `peak_power_w` calibration
line rendered only when a measurement exists.

**Regression.** Byte-for-byte trace identity is impossible (SimState gained a
field), so the spec_22 method was used instead: `model_dump` of eight canned
workloads (whole/tiled/double-buffered/rectangular/tensor/mlp/llm, several
profiles) captured before the change and compared after with the new keys
stripped — byte-identical. Suite: 322 → 358, all green.
