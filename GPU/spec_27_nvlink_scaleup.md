# Spec 27 — NVLink scale-up: the matmul no longer fits one die

**Status:** proposed
**Builds on:** `spec_03_tiling.md` (output tiles), `spec_04_bandwidth_model.md` (cycle costs
from bytes/rate), `spec_05_double_buffering.md` (the house pattern for an engine-mode spec).
**Meets from above:** the XE9680/XE9712 twins' "GPUs fuse into one domain" story — this spec
is the same idea seen from *inside* one pair of dies.

---

## 0. Why this, in plain terms

Every spec so far assumes one die is enough. Real training matmuls stopped fitting one die
years ago, and the fix is the least glamorous move in parallel computing: split the output,
run the same kernel on each die, then **pay to exchange results over a link**. spec_27 is
the smallest honest model of that — two GPUs, one matmul, one explicit exchange.

The lesson it makes visible:

- **Compute halves, but communication is added, not hidden.** Two dies do half the MACs
  each, then must all-gather C over NVLink. For small N the exchange dominates and 2 GPUs
  are barely faster (sometimes the model shows why people say "don't shard tiny kernels");
  for large N compute dominates and speedup approaches — never reaches — 2×.
- **The link is a *feature of the die*, not of the workload.** H100 has NVLink 4; B300 has
  NVLink 5 at twice the rate; RTX-5090 and the Generic dies have none, and asking them to
  scale up is refused — consumer dies scale out over PCIe or not at all. The refusal is
  itself the lesson.
- **The seam GB200/300 hides, we show.** The anatomy page already draws NV-HBI: two
  reticle-limited Blackwell dies fused at 10 TB/s so software sees one GPU. This mode is
  the opposite teaching move — the same two-die reality with the seam left **visible**, an
  explicit exchange phase you can watch and count.

---

## 1. Data-model changes (additive)

**`GpuProfile`** gains an optional link block (dies are data, not code):

- `link: Link | None = None`, where `Link = {label: str, bytes_per_cycle: int}`.
- Values are illustrative like `Bandwidth`, but the *ratios* are honest:
  H100-SXM → `NVLink4`, `bytes_per_cycle=4`; B300-Blackwell-Ultra → `NVLink5`,
  `bytes_per_cycle=8` (NVLink 5 = 2× NVLink 4, as 1.8 TB/s is 2× 900 GB/s). MI300X may
  carry an Infinity-Fabric link later; RTX-4060, RTX-5090, and both Generics carry `None`.
- Link rate is deliberately much smaller than `bandwidth.bytes_per_cycle` — HBM is on
  package, the link crosses the board. That gap *is* the cost model.

**`Workload`** gains `gpus: int = Field(default=1, ge=1, le=2)`. Default 1 → every
existing trace is byte-identical (regression guard, as `double_buffer=False` was in
spec_05). `gpus=2` against a profile with `link=None` is a **422 validation error** with a
message that teaches ("RTX-5090 has no NVLink; consumer dies scale out over PCIe or not at
all"), not a silent fallback.

**`SimState`** gains one lean field: `gpu: int | None = None` — which die this state's
`core_state[]` describes (`None` for single-GPU traces and for the shared `exchange`/
`done` states). One logical trace, interleaved per-die states; we do **not** double
`core_state`'s width or ship two arrays per state.

**`Summary`** gains `exchange_cycles: int` and `scaleup_speedup: float`
(`serial_1gpu_cycles / pipeline_2gpu_cycles`; `1.0` when `gpus=1`).

---

## 2. The decomposition and the phase order

Data parallel over output tiles, split by rows: die 0 owns C's top `⌈N/2⌉` rows of tiles,
die 1 the rest. Each die runs the **existing engine unchanged** on its half — same tiling,
same bandwidth stalls, same optional double-buffering; `tile_aware_core` still never
straddles an SM, and now a tile never straddles a die either (dies share nothing but the
link, which is the point).

Phase order per die stays `idle → load → compute → writeback` cycles as before; then one
new trailing phase before `done`:

```
idle → [die 0: load→compute→writeback ...] → [die 1: ...] → exchange → done
```

- `exchange` is a single state, `stalled=True`, `mem_active=False`, with
  `cycle_cost = ceil(bytes(C) / link.bytes_per_cycle)` — each die all-gathers the other's
  half of C (`bytes(C) = N² × dtype_bytes`; illustrative, per spec_04's fidelity ceiling).
  The UI dwells on it exactly as it dwells on costly loads.
- **Phase-order invariants extend, not break**: order is monotonic *within each die's
  subsequence* (filter the trace by `gpu`), `exchange` appears iff `gpus=2` and appears
  exactly once, after every writeback and before `done`. With `gpus=1` the trace has no
  `exchange` and no `gpu` values — spec_01–06 tests untouched.

**MAC conservation across dies:** per-die `mac_done` counts only that die's rows; the
trace-level counter stays global and monotonic, and at `done`,
`sum(per-die mac_done) == mac_done == N³ == mac_total` exactly. No MAC is done twice and
none is dropped — the split is a partition, not an approximation.

Cost accounting (illustrative): `two_gpu_cycles ≈ max(die0, die1) + exchange_cycles`, so
speedup = `serial / two_gpu` < 2 always, approaching 2 as N³ compute swamps N² exchange.

---

## 3. Rendering

`DieView` renders **two die schematics side by side** when the response's workload has
`gpus=2`, with a narrow vertical **link strip** between them labeled from `profile.link`
(NVLink4 / NVLink5) — the same visual grammar as the anatomy page's NV-HBI strip, drawn at
board scale instead of package scale. Each die paints only from states carrying its `gpu`
index; the idle die renders its last-known state dimmed (honest: while die 1 streams its
tiles the model runs the dies serially in trace order — a caption says "one logical trace,
two die views; real dies run concurrently, see Summary for the max()-based cost"). During
`exchange` both dies dim and the link strip lights and pulses — the only moment it does.
`Counters` adds exchange cycles and the scale-up speedup (`×1.42`, say) next to the
spec_05 pipeline numbers.

---

## 4. Non-goals (defer)

- More than 2 GPUs, tensor/pipeline parallelism, ring vs tree all-gather — this is the
  smallest honest model, not NCCL.
- Overlapping exchange with compute (the spec_05 trick applied to the link) — a natural
  spec_28, and the caption should not pretend we do it.
- A PCIe fallback path for linkless dies — the refusal teaches more than a slow path.

---

## 5. Testing (pytest, house style)

- **Regression:** `gpus=1` traces byte-identical to today's, all profiles, tiled and not.
- **Validation:** `gpus=2` + `link=None` profiles (RTX-5090, Generic-128) → 422; H100/B300
  accept. Link ratio pinned: `B300.link.bytes_per_cycle == 2 * H100.link.bytes_per_cycle`.
- **Conservation:** at `done`, `mac_done == N³ == mac_total`; per-die partition sums
  exactly; per-die max `mac_done` values are `⌈N/2⌉·N·N` and `⌊N/2⌋·N·N`.
- **Phase order:** monotonic per die; exactly one `exchange`, after all writebacks, before
  `done`; `exchange.cycle_cost == ceil(N² · dtype_bytes / link.bytes_per_cycle)`.
- **The scaling lesson, pinned:** on H100-SXM,
  `speedup(N=8) < speedup(N=64) < 2.0` — small N scales badly, large N scales well,
  nothing reaches 2×. Same shape on B300, and `speedup_B300(N) >= speedup_H100(N)` at
  equal N (the faster link can only help).
- **Purity:** engine stays AST-clean (no fastapi/time/IO); the clock stays in `App.tsx`.

---

## Implementation notes (2026-08, as landed)

The spec was authored before specs 22–26 landed; where the code had moved, the
code won. Deliberate decisions, in the order the spec raises them:

- **Rectangular shapes (spec_22).** "Split C's top ⌈N/2⌉ rows" generalizes to
  the resolved M axis: die 0 owns rows `[0, ⌈M/2⌉)`, die 1 the rest, and
  **each die re-tiles its own row-slice independently** (per-die
  `effective_tile_size`). That keeps "a tile never straddles a die" true by
  construction — including the untiled whole-matrix case, where a naive
  row-*tile* split would have handed die 1 nothing. Consequence: die
  coordinates (`tile_row`, cell rows) are die-local; the per-die engine is
  `_build()`, the old `simulate()` body factored out and reused byte-for-byte.
- **Exchange cost.** `bytes(C) = ceil(M·N·dtype_bits/8)` — the spec's
  `N²·dtype_bytes` generalized through spec_22's M and spec_23's bits era
  (fp4-safe). Cost = `max(1, ceil(bytes / link.bytes_per_cycle))`.
- **Tensor mode (spec_23) composes for free**: each die runs `_build()`
  unchanged, MMA stepping included. No special casing anywhere.
- **Power (spec_25).** The exchange state burns
  `idle_w + byte_w × link.bytes_per_cycle`: lanes are parked (it is stalled,
  like a costly load) and the *link*, not HBM, moves the bytes — so
  `mem_active` stays False per this spec and the per-byte constant is billed
  at the link's own rate. Always under `envelope_watts()` since the link rate
  sits below HBM's. The energy ledger stays an exact Σ power × cycle_cost.
- **mlp_step / llm_decode refuse `gpus=2`** (model-validation 422). The spec
  is silent; sharding a chained workload is pipeline parallelism — §4's
  deferred territory — and sharding only its matmuls would draw a falsehood.
- **MI300X carries no link**, per the spec's own "may carry an Infinity-Fabric
  link later". Until it does, it refuses like the consumer dies.
- **mac accounting**: `mac_done` is globally monotonic across the interleaved
  trace (die 1 continues from die 0's total); each die's subsequence
  contributes exactly its `rows × K × N`, and `mac_total` is global `M·K·N`
  on every state. "Sum of per-die macDone" in §5 is pinned as the sum of
  per-die *contributions*.
- **Summary speedup** uses the workload-independent serial estimate:
  `serial_cycles ÷ (max(die0, die1) serial + exchange)`, per §2's formula.
  The roofline numbers (bytes, intensity, regime) stay the one-die view; the
  scale-up read-outs sit beside them, as spec_05's scheduling numbers do.
- **Rendering**: two `DieView`s side by side (each with a `label`/`dimmed`
  prop) around a vertical `.link-strip` labeled from `profile.link`, pulsing
  only during exchange; captions carry the "one logical trace, two die views"
  honesty. **MatrixPanels are hidden in 2-GPU mode** with a note — die 1's
  tile coordinates are die-local, and repainting them into global C rows
  would be wrong whenever M is odd or tiles don't align. Honest over clever.
- **Regression guard**: `tests/fixtures/pre_spec27_traces.json` was dumped
  from the engine *before* this spec landed (8 profile×workload cases);
  `test_scaleup.py` replays them and requires byte-for-byte equality modulo
  the one additive `gpu: null` key (and the two neutral Summary fields).
- **SimState.gpu** rides every state (`null` off the scale-up path) — the
  lean-wire choice from §1; no doubled `core_state`, no second array.
