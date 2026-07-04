# Spec 03 — Tiling: stream blocks through shared memory

**Status:** implemented
**Builds on:** `initial_spec.md`, `spec_02_matrix_panels.md`.
**Roadmap ref:** near-term item #3 ("Real tiling: block the matmul, stream tiles
HBM → shared mem → registers, visualize reuse").

---

## 0. Why tiling, in plain terms (read this if GPUs are new to you)

So far the app pretends the whole matrix is available to every core at once: one
big LOAD, then all the MACs, then one writeback. Real GPUs can't do that. Here's
the problem and the fix:

- A GPU has two kinds of memory that matter here:
  - **HBM** (the "HBM" stacks on the die edges) — *big but slow*. Your whole
    matrix lives here. Reaching into it is expensive.
  - **Shared memory** (the "shared mem" strip inside each SM) — *tiny but fast*.
    Only a small block fits.
- If every multiply went back to slow HBM for its two numbers, the cores would sit
  idle waiting for data — the chip would be **memory-bound** (starved), not
  compute-bound (busy).
- **Tiling** is the fix: chop the matrices into small **tiles** (T×T blocks), copy
  one tile of A and one tile of B into fast shared memory *once*, then do *many*
  multiplies out of that fast copy before fetching the next tile. Loading a tile
  once and reusing it many times is **data reuse** — the single most important idea
  in making matmul fast on a GPU.

The teaching goal of this feature: **make the tile you're currently working on
visible** — show which block of A and B is "in fast memory" right now, and watch
the result tile (in C) fill in before the next block streams in.

### The tradeoff this also reveals (bonus lesson)

Smaller tiles need less fast memory but compute fewer output cells at a time — so
**fewer cores light up** and the utilization counter drops. Bigger tiles use more
fast memory but keep more of the chip busy. Slide the tile size and watch
utilization change: that's the real tension GPU programmers tune.

---

## 1. The tiled algorithm (what the engine does)

For an N×N · N×N matmul with tile size T, the output C is split into T×T tiles.
For each output tile we stream the matching strip of A and B through shared memory:

```
for each output tile (ti, tj) of C:          # which block of the result
    for each k-tile (tk) along the shared dimension:
        LOAD     A-tile (ti, tk) and B-tile (tk, tj)  HBM -> shared mem
        COMPUTE  T accumulation steps, MACing those tiles into the C-tile
    WRITEBACK    the finished C-tile  -> HBM
```

The phases are the *same five* as before (`idle/load/compute/writeback/done`) —
they just **repeat per tile** now. Total MACs are unchanged (`N*N*N`); we've only
changed the *order* and *granularity* of the work, which is the whole point.

**Reduces to the old behavior:** with `tileSize >= N` (one tile = the whole
matrix) the trace is byte-for-byte the original single-LOAD trace. So tiling is
opt-in via a smaller `T`, and all existing engine tests stay valid.

---

## 2. Data-model changes (additive)

**Backend:**
- `Workload`: add `tile_size: int = 0` (`0` means "whole matrix" = no tiling).
- `SimState`: add `tile_row`, `tile_col`, `k_tile` (`Optional[int]`, null when not
  inside a tile, e.g. `idle`/`done`; `k_tile` is null during `writeback`).
- `SimulateResponse`: add `tile_size: int` (the effective T after clamping).
- `engine.simulate` rewritten to the tiled loop above. MACs accrue per compute
  step as `len(cells in the current C-tile)`, so small tiles → fewer active cores.

**Frontend:**
- `types.ts`: mirror the new fields.
- Tile-size control in `Controls` (slider 1..N; at N shows "whole matrix").
- `MatrixPanels`: draw tile boundaries; highlight the **active A-tile / B-tile**
  ("in shared memory" — blue while loading, amber while computing) and the
  **active C-tile**. C now fills in **tile by tile** (each cell tracks its own
  accumulation progress), not globally.
- `Counters`: when tiling is on, show **HBM tile-loads so far**, **tiles done /
  total**, alongside utilization (which visibly drops for small tiles).

---

## 3. Visual language (extends spec_02)

| Element                                | Token          | Meaning                          |
|----------------------------------------|----------------|----------------------------------|
| A/B tile streaming HBM → shared mem    | `--mem-active` | block being loaded into fast mem |
| A/B tile resident, feeding MACs        | `--core-on`    | reused out of fast memory        |
| Active C-tile being accumulated        | outline ring   | where results are landing now    |
| C cell finalized                       | `--core-hot`   | result written (matches cores)   |

---

## 4. Non-goals (defer)

- **No separate register-file level.** Spec text says HBM → shared → registers; we
  model two levels (HBM, shared) for clarity. Registers are a later refinement.
- **No bandwidth/latency timing.** LOAD is still one step regardless of tile size;
  making load duration depend on tile bytes is roadmap #5 (a natural spec_04).
- **No non-square dims** (still N×N) and **no tensor cores**.
- Tile sizes that don't divide N are handled by clamping the last tile (partial
  edge tiles), but the UI nudges toward divisors for clean visuals.

---

## 5. Testing

- `tileSize=0`/`>=N` reproduces the spec_01 single-tile trace exactly
  (`idle, load, compute×N, writeback, done`).
- Total `macDone` at `done` equals `N*N*N` for every tile size; `macDone` is
  monotonic non-decreasing.
- Number of LOAD phases equals `rowTiles * colTiles * kTiles`; number of WRITEBACK
  phases equals `rowTiles * colTiles`.
- `activeCores <= totalCores` always; for a tile smaller than the die, utilization
  is strictly lower than the whole-matrix case (the occupancy lesson).
- Every C cell ends fully accumulated (implied MACs per cell == N).

---

## 6. Open questions

- Should the die also animate shared-memory strips filling per SM, or is showing it
  on the matrices enough? (Start with matrices; revisit.)
- Surface a derived "HBM bytes moved" estimate to make the reuse win quantitative?
  That edges into the bandwidth model (spec_04 territory).
