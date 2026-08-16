# spec_24 — occupancy in the simulator's mental model

**Goal:** cuda lesson 03 ("occupancy is a budget") has no simulator-side
counterpart. The Live tab shows a measured/theoretical `occupancy_pct` for real
kernels, but the sim tab — the place a beginner actually forms the mental
model — never mentions occupancy at all, and its one percentage (utilization)
is the number beginners *mistake* for occupancy. Bring the budget arithmetic
into the sim: per-SM residency limits on the profile, a `block_size` knob on
the workload, and a read-out that names which budget ran out first.

## The two percentages (the lesson)

- **Utilization** (exists today): lanes computing *this state* /
  `total_cores`. A moment-by-moment activity number.
- **Occupancy** (this spec): resident warp slots claimed / warp slots the SM
  *could* hold. A static budget set at launch by block size vs two ceilings —
  `maxThreadsPerSm` AND `maxBlocksPerSm` — whichever runs out first wins.
  32-thread blocks on Ada hit the 24-block ceiling at 24×32 = 768 of 1,536
  threads: 50% occupancy while utilization can still read anything.

Conflating them is the most common beginner confusion; the UI must show both,
side by side, labeled as different questions.

## Design

- **Profile** (`models.py`): `GpuProfile` grows `max_threads_per_sm: int =
  1536`, `max_blocks_per_sm: int = 24`, `warp_size: int = 32` (Ada numbers as
  defaults — every existing profile in `profiles.py` stays valid untouched;
  set them explicitly on `RTX_4060_LAPTOP` so lesson 00's device-query
  reality-check has a pinned counterpart). Camelization: plain `to_camel`
  yields `maxThreadsPerSm` etc., matching what `DeviceInfo` in `live.py`
  already serializes — no `PerSM` alias here; verify `types.ts` by hand per
  the CLAUDE.md gotcha.
- **Workload** (`models.py`): `block_size: int = Field(default=0, ge=0,
  le=1024)` — threads per thread-block. `0` means "derived": one output tile
  is one block (today's implicit rule, `T²` cells clamped to 1024), which is
  what makes the default reproduce existing traces exactly. A nonzero value
  overrides for the occupancy read-out only — the cell→lane mapping and the
  trace shape are deliberately untouched (illustrative, not a scheduler).
- **The shared helper** (`app/occupancy.py`, new, pure — importable by
  `engine.py` without breaking the AST purity check): one function,
  `theoretical_occupancy(block_size, *, max_threads_per_sm, max_blocks_per_sm,
  warp_size) -> Occupancy`, returning `{blockSize, warpsPerBlock,
  blocksResident, occupancyPct, limiter}` where

  ```
  warps_per_block = ceil(block_size / warp_size)      # warp-granular, like hardware
  by_threads      = max_warps_per_sm // warps_per_block   # max_warps = threads // warp
  blocks_resident = min(max_blocks_per_sm, by_threads)
  occupancy_pct   = 100 * blocks_resident * warps_per_block / max_warps_per_sm
  limiter         = "blocks" if max_blocks_per_sm < by_threads else "threads"
                    ("none" at exactly 100%)
  ```

  This is the same formula the CUDA occupancy API applies for the
  threads-and-blocks budgets; registers and shared memory (the *other* two
  budgets, which lesson 03's experiment alludes to) are explicitly out of
  scope — say so in the InfoDot copy rather than pretending.
- **Trace exposure:** on `Summary`, not `SimState`. Occupancy is fixed at
  launch — one `block_size` per run — so a per-state field would be 1,000
  copies of a constant. `Summary` grows `occupancy: Occupancy`; `SimState`
  stays lean. (`mlp_step` chains matmuls with one workload → still one
  occupancy for the run.)
- **UI** (`Counters.tsx` + `InfoDot.tsx` + `Controls.tsx`): a block-size
  select (derived/32/64/128/256/512/1024) beside tile size; an occupancy
  read-out beside utilization showing `occupancyPct` and the limiter as prose
  — "block-limited: 24 blocks × 32 threads = 768 of 1,536 slots" — with an
  InfoDot spelling out utilization-vs-occupancy in two sentences. Changing
  block size refetches (it's workload data), like every other knob.
- **Tie to the Live tab:** `LiveState.occupancy_pct` for `occupancy_source ==
  "theoretical"` is this same formula, computed by the CUDA occupancy API on
  real hardware. State it in the UI ("same arithmetic the Live tab shows for
  real kernels") and pin it in tests: run the lesson-03 probe fixtures'
  `{block, occupancy_pct}` pairs through `theoretical_occupancy` with the
  4060's limits and assert agreement — one formula, two sources, cross-tested
  without a GPU.

## Invariants (new `tests/test_occupancy.py` + extend `test_engine.py`)

- **Lesson 03, exactly as narrated:** `block_size=32` on Ada limits →
  `blocks_resident == 24`, `occupancy_pct == 50.0`, `limiter == "blocks"`.
- **The other ceiling:** `block_size=1024` → `blocks_resident == 1`,
  `limiter == "threads"`, occupancy 66.7% (1,024 of 1,536).
- `0 < occupancy_pct <= 100` for every block size 32–1024 on every shipped
  profile; sweep the lesson's sizes {32, 64, 128, 256, 512, 1024}.
- **Defaults change nothing:** `block_size=0` traces are byte-identical to
  today's for the existing test matrix (N, tile, dtype, double-buffer);
  existing profiles deserialize with no new JSON required.
- `engine.py` stays pure (AST check unchanged — `occupancy.py` imports only
  `math`/`models`); the clock stays in `App.tsx`.
- Cross-test: lesson-03 fixture occupancy values match the helper (above).
- API surface: `test_smallwins3.py::test_api_surface_snapshot` — no new
  routes; occupancy rides the existing simulate response.

## Files

`backend/app/occupancy.py` (new), `models.py` (profile fields, `block_size`,
`Summary.occupancy`), `engine.py` (`analyze()` fills it), `profiles.py`
(explicit 4060 limits), `tests/test_occupancy.py`, `frontend/src/types.ts`,
`Controls.tsx`, `Counters.tsx`, `InfoDot.tsx` copy.

**Effort:** M. **Depends on:** nothing. **Best paired with:** lesson 03 — the
sim read-out and the live timeline finally tell one story.

## Implementation notes

Implemented 2026-08 against the post-spec_22 codebase (rectangular matmul).
Deviations from the text above, all deliberate:

- **Rectangular workloads (spec_22, landed after this spec was written):** the
  derived block size uses the engine's single effective tile edge `T` from
  `effective_tile_size(max(M, K, N), tile_size)` — so the derived block is
  `min(1024, T²)` even when partial edge tiles are smaller. One block size per
  run, as specced; the rectangle changes nothing else.
- **`occupancy.py` imports nothing but `models`** — the ceil is integer
  arithmetic (`-(-b // w)`), so not even `math` is needed. The AST purity test
  in `tests/test_occupancy.py` still allows `typing`/`math` should either ever
  be wanted.
- **The lesson-03 probe fixture carries exactly one occupancy-bearing launch**
  (the 32-thread `vector_add_bs32`, `occupancyPct: 50.0`). The cross-test runs
  every occupancy-bearing launch in the fixture through the helper and asserts
  agreement; the 1024-thread half of the narration (≈66.7%, thread-limited) is
  pinned directly on the helper since the fixture never recorded it.
- **`mlp_step`** reaches the same occupancy through `analyze_mlp`'s
  `model_copy` scaling — one workload, one block size, one occupancy per run,
  untouched by the per-op ×k scaling.
- The UI prose counts **thread slots** (`768 of 1,536`) rather than warp
  slots, matching the example in this spec's own Design section; the model
  fields stay warp-granular.
