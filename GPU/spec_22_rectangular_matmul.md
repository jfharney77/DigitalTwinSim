# Spec 22 — Rectangular matmul: generalize square N to M × K × N

**Status:** proposed
**Builds on:** `initial_spec.md`, `spec_02_matrix_panels.md`, `spec_03_tiling.md`,
`spec_04_bandwidth_model.md`, `spec_05_double_buffering.md`.
**Roadmap ref:** near-term item #1 ("Generalize `Workload` from square `N` to
`M × K × N`") — the oldest unticked box on the roadmap.

---

## 0. Why rectangles, in plain terms

Real matmuls are almost never square. An inference batch is `(batch × hidden) ·
(hidden × vocab)`; an attention score is `(seq × d) · (d × seq)`. The three
dimensions play *different roles*, and the square case hides that:

- **M** — rows of A and of C: how many independent output rows there are.
- **N** — columns of B and of C: how many independent output columns.
- **K** — the shared dimension: how *deep* each output cell's accumulation runs.

M and N size the output (parallelism: how many cells, how many cores light up).
K sizes the work *per cell* (the dot-product length) and never appears in C's
shape at all. With `N` doing all three jobs, a learner can't see that shrinking
K makes each cell cheaper while shrinking M or N makes fewer cells — the tall-
skinny vs short-fat distinction that decides real kernels' regimes. This spec
splits the roles apart. It is a generalization pass, not a new mechanism: every
phase, tile, stall, and prefetch behaves as it does today.

---

## 1. Data model: `n` keeps working (backend `models.py`, exact rule)

`Workload` gains `m: int = 0` and `k_dim: int = 0`. **The rule: a value of `0`
means "= n".** So every existing request, saved localStorage setting, and test
is untouched — `n` alone still describes a square matmul, and `m`/`k_dim` are
opt-in. Effective dims are resolved once, at the top of `simulate`/`analyze`:

```python
M = workload.m or workload.n
K = workload.k_dim or workload.n
N = workload.n            # unchanged; A is M×K, B is K×N, C is M×N
```

Naming and the camelCase gotcha: `n` carries `alias="N"` today, so the new
fields carry `alias="M"` and `alias="K"` for symmetry (`to_camel` would emit
lowercase `m`/`k`, mismatching the TS style). The Python field is `k_dim`, not
`k`, purely to avoid shadowing confusion with `SimState.k` when grepping —
on the wire it is `K`. Verify the JSON keys against `types.ts` by hand, per the
CLAUDE.md rule. Bounds: same `ge=2, le=64` as `n` (0 exempt as the sentinel).
`SimulateResponse` echoes the resolved `m`/`k`/`n` so the frontend never
re-derives the sentinel rule.

---

## 2. Engine semantics (`engine.py`, stays pure)

The tiled loop keeps one square tile size T; what changes is the *grid* of
tiles, now per-axis: `_ranges(M, T)` for rows, `_ranges(N, T)` for cols,
`_ranges(K, T)` for the k-loop (edge tiles stay partial, as today).

```
for each output tile (ti, tj) over ceil(M/T) × ceil(N/T):
    for each k-tile (tk) over ceil(K/T):
        LOAD     A-tile (rows × kspan) + B-tile (kspan × cols)
        COMPUTE  kspan accumulation steps, len(tile cells) MACs each
    WRITEBACK    the finished C-tile
```

- `mac_total = M * K * N`. Each compute step still adds `len(tile_cells)` MACs;
  `SimState.k` now runs 0..K (it is the accumulation depth, so it belongs to K).
- Serial and double-buffered schedules generalize identically — the flattened
  event list just iterates the rectangular grid. `_load_bytes` already takes
  independent row/col/k spans, so tile bytes are correct without change.
- `mapping.tile_aware_core` is **unchanged in spirit and nearly in code**: a
  whole C-tile still lands on one SM (tiles round-robin by linear index over the
  M×N tile grid; `num_tile_cols = ceil(N/T)` instead of one shared count), and
  cells map to lanes within that SM. A tile never straddles two SMs.
- `analyze`: `bytes_moved` sums the rectangular tile loads (A traffic scales
  with M·K·kTiles-reuse, B with K·N — they now genuinely differ, which is the
  roofline payoff: a tall-skinny matmul has low intensity because K is short).
  `arithmetic_intensity = M*K*N / bytes_moved`; ridge point unchanged. As
  today, writeback bytes (M·N) are not counted — note this in the UI footnote
  rather than silently changing the spec_04 numbers.
- `matrices.make_operands(m, k, n, seed)`: A is M×K, B is K×N, same seeded
  single-digit pattern (indices, not shape, drive the values, so the square
  call is bit-identical to today's).

**MLP stays square, deliberately.** `mlp.py`'s five chained matmuls share one
shape (X, W1, W2, transposes and gradients all N×N); making them rectangular is
a batch-size/hidden-width story with its own shape-propagation rules and its
own lesson, worth a spec of its own — not a side effect of this one. `mlp_step`
therefore ignores `m`/`k_dim` (validation: reject nonzero values with a 422 so
the limitation is loud, not silent). The spec_06 invariants are untouched.

---

## 3. Frontend

- `types.ts`: `M?: number; K?: number` on `Workload` (optional, mirroring the
  sentinel); resolved `m`/`k`/`n` on the response.
- `Controls`: M and K sliders defaulting to "= N" (a linked state, shown as
  such); a small "square" toggle snaps them back. Settings persist in
  localStorage as today.
- `MatrixPanels`: grids become `rows × cols` per panel — A is M×K, B is K×N, C
  is M×N — with cell size shrinking to keep panels bounded. `tileSpan` takes
  the axis length; `cellDepths` replays the trace exactly as now but caps depth
  at **K**, not n, and indexes the M×N output. Tiling overlays (active A/B/C
  tile, boundary rules) generalize by axis.
- `Counters`/roofline read-out: unchanged shapes; the numbers now move when M,
  K, N move independently — which is the feature.

---

## 4. Invariants (pytest, `GPU/backend/tests/`)

- **Byte-for-byte regression:** for every existing test workload, `m=0, k_dim=0`
  *and* `m=n, k_dim=n` both reproduce today's trace and `Summary` exactly
  (serial and double-buffered, all tile sizes). This is the gate; land it first.
- `mac_done` monotonic, `mac_done <= mac_total`, and at `done` equals
  `M * K * N` — for rectangular cases with M, K, N pairwise distinct.
- Phase order `idle→load→compute→writeback→done` per tile, unchanged; LOAD
  count `== rowTiles * colTiles * kTiles`, WRITEBACK count `== rowTiles *
  colTiles`, with the per-axis tile counts.
- Every C cell ends at accumulation depth exactly K (trace replay, the
  MatrixPanels algorithm run server-side).
- Tile-aware mapping: no tile's cells span two SMs; `active_cores <=
  total_cores`; `utilization == active_cores / total_cores`.
- `analyze`: `arithmetic_intensity == mac_total / bytes_moved`; a fixed-work
  comparison pins the lesson (e.g. 4×16×4 vs 8×8×8 vs 16×4×16 — same or
  comparable MACs, measurably different intensity/regime).
- `mlp_step` with nonzero `m`/`k_dim` is rejected; square MLP traces unchanged.
- Engine purity AST check already covers the touched modules; no new routes, so
  `test_api_surface_snapshot`'s 23 pinned routes stay as they are.

---

## 5. Scope guardrails

Still illustrative, not cycle-accurate (spec §1). Square T×T tiles only —
rectangular *tiles* (T_M×T_K) are a real tuning axis but a separate lesson;
defer. Dims stay capped at 64 per axis: the panels render tens-to-hundreds of
cells, not tensors. Tensor-core/systolic mode (roadmap #4) is untouched and
becomes easier after this, since a systolic array is natively M×K×N. New dies
remain data, not code — nothing here touches `profiles.py`.

---

## Implementation notes

Implemented 2026-08. Two deliberate deviations, both toward code reality:

- **`make_operands` keeps its historical signature.** The spec names it
  `make_operands(m, k, n, seed)`, but existing call sites and
  `tests/test_matrices.py` call it positionally with `n` first
  (`make_operands(4, 0)`). The implemented signature is
  `make_operands(n, seed=0, m=0, k=0)` with the same 0-sentinel — the
  two-argument square call stays bit-identical, and rectangular callers pass
  `m=`/`k=` by keyword.
- **The fixed-work intensity test uses different shapes.** §4's example
  (4×16×4 vs 8×8×8 vs 16×4×16) has unequal MACs (256/512/1024), and any
  M=N=4 tall-skinny variant at 512 MACs lands its untiled intensity exactly
  on the Generic-128 ridge point (0.5), making the regime assertion
  degenerate. `tests/test_rectangular.py::test_fixed_work_intensity_comparison`
  instead pins 2×64×2 vs 4×16×4 vs 8×4×8 — identical 256 MACs each, three
  distinct intensities, and a genuine memory→compute regime flip on shape
  alone.

One clarification, not a deviation: the effective tile size for a rectangular
workload resolves against `max(M, K, N)` (0 or ≥ the largest axis = whole
matrix; `_ranges` handles a T larger than a shorter axis as one partial tile),
which reduces exactly to the old `effective_tile_size(n, t)` when square.
