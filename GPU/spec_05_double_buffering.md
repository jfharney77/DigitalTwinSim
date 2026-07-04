# Spec 05 — Double-buffering: hide loads behind compute

**Status:** implemented
**Builds on:** `spec_03_tiling.md`, `spec_04_bandwidth_model.md`.
**Roadmap ref:** the "latency hiding" idea flagged as an open question in spec_04 §6
("Should compute overlap the next tile's load?").

---

## 0. Why this, in plain terms

spec_04 showed the painful case: when loading a tile is slower than computing it,
the cores **stall** — they finish their math and sit idle waiting for the next block
to arrive from slow HBM. spec_05 shows the standard fix GPUs use for this.

The trick is called **double-buffering** (a.k.a. prefetching / software pipelining):

- Keep **two** buffers in fast shared memory instead of one.
- While the cores compute on the tile in **buffer A**, the memory system is already
  streaming the **next** tile into **buffer B** — at the same time.
- When compute finishes, the next tile is already there, so the cores start
  immediately instead of waiting. Then the roles swap (compute B, load into A).

The load is "hidden in the shadow" of the compute. You can't hide the **very first**
load (there's nothing to compute yet — this is the *prologue*), but every load after
that can overlap.

### The lesson it makes visible

- **Compute-bound workloads:** compute is longer than each load, so loads hide
  completely → the stalls vanish → you run at compute speed. Double-buffering is
  "free performance" here.
- **Memory-bound workloads:** loads are longer than compute, so compute hides inside
  the loads instead → you're still limited by memory, but you no longer waste the
  compute-waiting time. Better, but tiling/precision are still what you'd tune.

So the payoff is a concrete before/after: turn double-buffering on and watch the
**"waiting on HBM" stalls disappear** from the middle of the run, and the **total
cycle estimate drop** (shown as a speedup).

---

## 1. What changes in the model

Same five phases; we change the *schedule*, not the math (total MACs unchanged).

- **Serial (spec_03/04):** `load → compute → load → compute → …` — the cores stall
  on every load.
- **Pipelined (this spec):** one prologue `load` (stall), then every `compute`
  step also carries a **background prefetch** of the next tile: the cores are
  computing (amber) *and* HBM is active (blue) at the same time — no stall.

A new `SimState.prefetching` flag marks compute steps that overlap a background
load. Visually, the die shows amber cores + a lit HBM stack simultaneously — that
simultaneity *is* the lesson.

Honest cost accounting (illustrative, per spec_04's fidelity ceiling):

- `serial_cycles   = load_cycles_total + compute_cycles_total`
- `pipelined_cycles = firstLoad + max(compute_cycles_total, load_cycles_total − firstLoad)`

i.e. after the unavoidable prologue load, the smaller of {remaining loads, all
compute} hides behind the larger. The UI reports both and the speedup.

---

## 2. Data-model changes (additive)

**Backend:**
- `Workload`: add `double_buffer: bool = False`.
- `SimState`: add `prefetching: bool = False`.
- `Summary`: add `serial_cycles`, `pipelined_cycles`.
- `engine.simulate`: dispatches to the existing serial builder (default) or a new
  pipelined builder. With a single tile (whole matrix) the two are identical —
  there's nothing to overlap — which keeps all existing traces/tests valid.

**Frontend:**
- A **double-buffering toggle** in `Controls`.
- Phase label notes "· prefetching next tile" during overlapped compute.
- `Counters`: show `serial` vs `pipelined` cycles and the speedup (`×`).
- `DieView` needs no change: it already lights HBM from `mem_active` and cores from
  `coreState`, so overlap renders for free (amber + blue together).

---

## 3. Non-goals (defer)

- **Overlapping writeback** with the next tile's compute (epilogue pipelining) —
  writebacks stay discrete for now.
- **Modeling the two buffers' shared-memory capacity** (double-buffering doubles the
  shared-mem footprint — a real constraint). Left for a shared-memory-capacity spec.
- Tensor-core / systolic-array mode (roadmap #4) remains a separate future spec.

---

## 4. Testing

- `double_buffer=False` reproduces the spec_04 trace exactly (regression guard).
- Single-tile workloads produce identical traces with the flag on or off (nothing to
  hide).
- Pipelined traces: total `macDone == N³`; no `compute` state is `stalled`; exactly
  one `load` state (the prologue) when tiled; `prefetching` is true on overlapped
  compute steps and false on the final tile's compute.
- `analyze`: `pipelined_cycles <= serial_cycles`, with equality only when there's
  nothing to overlap (single tile).

---

## 5. Open questions

- Show the *next* tile highlighting in the B-buffer on the matrix panels during
  prefetch (needs next-tile coords on the state)? Deferred — the die's amber+blue
  overlap already conveys it.
- Expose shared-memory pressure so the "two buffers cost twice the fast memory"
  tradeoff becomes visible? Good candidate for the next spec.
