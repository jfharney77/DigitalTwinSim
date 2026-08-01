# spec_16 — record sampling for huge grids

**Goal:** a 1M-block launch currently means a 24 MB device buffer and a
multi-MB JSON POST (65k blocks measured at ~2.7 MB / 155 ms ingest). Cap the
cost with sampling that stays statistically honest and is *declared* on the
wire.

## Design

- **Probe.** `TWIN_MAX_RECORDS` (default 8,192, env-overridable). Grids at or
  under the cap record every block exactly as today. Above it:
  - Records buffer is allocated at the cap, not the grid size.
  - Blocks self-select by linear id: keep the first 1,024 (the interesting
    startup wave) plus every ⌈grid/(cap−1024)⌉-th block after — deterministic
    striding, not RNG (no device RNG dependency, reproducible layout).
  - The flush JSON adds `"sampled": true, "sampleStride": k` and reports the
    honest full `grid`.
- **Backend.** `KernelLaunchEvent` gains `sampled: bool = False` and
  `sample_stride: int = 1`. The excess-records validator stays; the
  blocks-vs-grid completeness rule becomes: complete when
  `len(blocks) == grid_blocks()`, else `records_dropped()` reports the gap —
  but when `sampled` is true the fold **scales** `blocks_run` estimates:
  `est = count * sample_stride` per SM, and `SmActivity` gains
  `estimated: bool` so the UI renders `~170 blk` with a tilde instead of a
  lie of precision.
- **Frontend.** Tilde prefix + tooltip ("sampled 1 in k blocks") when
  estimated; the partial-frame marker from the defect-3 fix is *not* shown
  for declared sampling — sampling is a contract, truncation is an accident,
  and the UI must distinguish them.

## Invariants

- `sampled=false` events behave byte-identically to today (fixtures prove).
- For sampled events: `sum(count) * stride` within one stride of
  `grid_blocks()`; `estimated` true on every nonzero SM; `records_dropped`
  reports 0 (declared sampling is not data loss).
- Probe-side: a unit-style host test (compiled by `make lint` + run once on
  hardware) asserting stride selection covers every SM given round-robin
  placement.

## Files

`cuda/twinprobe.cuh`, `backend/app/live.py`, `tests/test_live_edges.py`
(+sampled fixtures), `frontend/src/{types.ts,components/LivePage.tsx}`.

**Effort:** M. **Depends on:** defect-3 fix (landed). **Pairs with:**
spec_14 — the same cap bounds the streaming poller's diff cost.
