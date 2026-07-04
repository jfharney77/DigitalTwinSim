# Spec 04 — Memory-bandwidth model: memory-bound vs compute-bound

**Status:** implemented — with one deliberate change from §3/§6: rather than
emitting one trace state per load cycle ("explicit states"), each LOAD stays a
single state carrying `cycle_cost` + `stalled`, and the **UI dwells** on it (up to
a cap) so slow loads are visibly longer. This keeps the spec_03 "load count == tile
grid" tests valid and avoids bloating the per-state `core_state` arrays on large
dies. The analytical regime lives in a separate `summary` (see `engine.analyze`),
so the badge/counters are exact even though on-screen dwell is capped for pacing.
**Builds on:** `initial_spec.md`, `spec_02_matrix_panels.md`, `spec_03_tiling.md`.
**Roadmap ref:** mid-term item #5 ("Memory-bandwidth model: make LOAD duration
depend on tile size / dtype to show memory-bound vs. compute-bound regimes").

---

## 0. Why this is the right next step

spec_03 introduced tiling and made one cost visible (occupancy: small tiles light
up fewer cores). But it left LOAD as a single free step regardless of how much data
moves — so the app still can't show the *other* half of GPU performance: **moving
data is slow, and sometimes the cores sit idle waiting for it.**

This is the single most important performance idea for a beginner to internalize:

- **Compute-bound:** the cores are the bottleneck — there's plenty of data on hand,
  the chip is busy doing math. Adding more math capacity would help.
- **Memory-bound:** the cores are *starved* — they finish their math and wait for
  the next tile to arrive from slow HBM. Adding more math capacity wouldn't help;
  you need more memory bandwidth or better reuse.

Tiling (spec_03) is precisely the lever that moves a matmul from memory-bound toward
compute-bound (load a tile once, reuse it many times). So the natural payoff of the
tiling feature is to **show the regime it's fighting** — making the reuse win
quantitative instead of just "fewer trips to HBM." This is the foundation of the
"roofline" mental model in roadmap #7, taught gently and visually.

It's also a small, contained change: we already emit `load` phases and tile context;
we just give LOAD a *duration* and let COMPUTE *wait* on it.

---

## 1. The idea (kept deliberately simple)

Give the model two illustrative rates (NOT real hardware numbers — see §4):

- **Memory:** moving one tile of A or B from HBM costs `loadCycles = ceil(bytes /
  bytesPerCycle)`, where `bytes = tileCells * dtypeBytes`.
- **Compute:** one accumulation step over a tile costs a fixed `computeCycles` (the
  cores do `tileCells` MACs in lockstep, as today).

For each tile we conceptually need: load A-tile + B-tile, then do the MAC steps. The
**regime** falls out of comparing the two:

- if `loadCycles > computeCyclesForTile` → **memory-bound** (cores idle part of the
  time, waiting on the load).
- else → **compute-bound** (the load is hidden behind the math).

`dtype` feeds this directly: fp32 = 4 bytes, fp16/bf16 = 2, int8 = 1. Smaller dtype
= fewer bytes to move = less likely memory-bound — which is *why* GPUs offer lower
precisions for throughput. Wiring `dtype` in here gives the existing (currently
fp32-only) field its first real effect, and sets up the tensor-core path (roadmap #4).

---

## 2. What the user will see

- A **stall visualization**: during a LOAD that is slower than the compute it feeds,
  the cores show an `idle`/`stalled` state and a "waiting on HBM" label for the
  extra cycles — you literally watch the chip wait.
- A **regime badge**: "MEMORY-BOUND" / "COMPUTE-BOUND" for the current workload,
  with the limiting resource highlighted.
- Counters: **cycles spent loading vs computing**, and an **arithmetic intensity**
  read-out (MACs per byte moved) — the x-axis of a roofline.
- A `dtype` selector (fp32 / fp16 / int8). Switching to a smaller dtype visibly
  shortens loads and can flip a memory-bound workload to compute-bound.
- Bonus: a tiny **roofline-style readout** — a single dot positioned by arithmetic
  intensity against a "ridge point", labeling which side you're on. (Optional; the
  badge alone delivers the lesson.)

The reuse lesson from spec_03 now has teeth: shrink the tile and watch arithmetic
intensity drop and the badge flip to MEMORY-BOUND; grow it (or lower dtype) and watch
it go COMPUTE-BOUND.

---

## 3. Data-model changes (additive)

**Backend:**
- `GpuProfile`: add an optional `bandwidth` block, e.g.
  `{ bytes_per_cycle: int, compute_cycles_per_step: int }` (data, not code — new
  dies tune these). Provide sane illustrative defaults so older profiles still work.
- `Workload.dtype`: widen to `fp32 | fp16 | bf16 | int8`; add a `dtype_bytes` helper.
- `SimState`: add `cycle` semantics note — LOAD phases may now span multiple cycles.
  Add `stalled: bool` (cores waiting) and keep `mem_active` as-is. Consider
  `load_cycles` / `compute_cycles` on the relevant states for the counters.
- `SimulateResponse`: add a `summary` block: `load_cycles_total`,
  `compute_cycles_total`, `arithmetic_intensity`, `regime: "memory" | "compute"`.
- `engine`: when emitting a LOAD, emit `loadCycles` worth of progression (or a single
  state annotated with its duration — pick one and keep the trace replayable). The
  frontend clock already advances per state; if a load takes K cycles, either emit K
  states or let the UI dwell — prefer emitting explicit states so the trace stays the
  single source of truth.

**Frontend:**
- `dtype` selector in `Controls`; regime badge + new counters.
- `DieView`: render a `stalled` core state (e.g. dim/pulsing) distinct from `idle`.
- Roofline mini-readout component (optional).

---

## 4. Honesty / fidelity ceiling (important)

This stays **illustrative, not cycle-accurate** — consistent with
`initial_spec.md` §1 and the project's guiding principle "correct mental model over
correct numbers". The two rates are made-up teaching constants, surfaced in the UI as
such (e.g. a "this is a teaching model, not real latencies" note). The goal is for a
novice to correctly answer "is this workload limited by math or by memory, and what
would help?" — not to predict real runtimes. Document the chosen ceiling in the UI
and in `CLAUDE.md`.

---

## 5. Testing

- Determinism preserved: same inputs → same trace and same `summary`.
- `arithmetic_intensity == macTotal / bytesMoved`; bytesMoved scales with `dtypeBytes`
  and with the number of tile loads from spec_03.
- Regime flips as expected: for a fixed workload, shrinking the tile lowers intensity
  toward memory-bound; lowering dtype bytes raises it toward compute-bound.
- Existing invariants still hold (`macDone` totals, `activeCores <= totalCores`).
- With bandwidth set so loads are "free" (or absent), the trace reduces to spec_03's.

---

## 6. Open questions

- Emit explicit per-cycle states for long loads (simpler renderer, longer traces) vs.
  annotate a load state with a duration the UI dwells on (shorter trace, clock logic
  in UI)? Recommend explicit states to keep "the trace is the source of truth".
- Should compute overlap the *next* tile's load (double-buffering / latency hiding)?
  That's a great advanced lesson but adds scheduling complexity — defer to a later
  spec and start with the simple serial load-then-compute model.
- How many dtypes to expose now? fp32 + one half precision is enough to teach the
  effect; int8 can come with the tensor-core spec.
