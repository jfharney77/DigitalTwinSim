# spec_23 — Tensor-core mode: MMA stepping and the moving ridge point

**Status:** proposed.
**Builds on:** `spec_03_tiling.md`, `spec_04_bandwidth_model.md`,
`spec_05_double_buffering.md`, `spec_07_rtx4060_profile.md` (fleet profiles).
**Roadmap ref:** `initial_spec.md` §7 item 4 ("Tensor-core mode: systolic-array
animation ... gated by `dtype`") and open question §"One unified renderer, or
separate scalar/systolic views?" — answered below: one renderer, one new state.

---

## 0. Why this is the right next step

Every trace the app can produce today executes a matmul the way 2006 hardware
did: one k-rank per cycle, one MAC per lane. But the fleet profiles we just
added (H100, B300, RTX 5090, MI300X) are dies whose entire economic argument is
the *other* execution path — matrix-multiply-accumulate (MMA) units that consume
a whole 16×16 tile of ranks per instruction, at multipliers that grow as the
dtype shrinks. The die view draws tensor-core-era silicon; the engine should be
able to run it in tensor-core mode.

The payoff is the spec_04 lesson sharpened to its modern form: **tensor cores
multiply `macs_per_cycle`, not `bytes_per_cycle`, so the ridge point moves
right and the memory wall gets *worse*.** A small-N matmul that was
compute-bound on scalar cores goes memory-bound the moment you switch execution
mode — which is exactly why real kernels fight so hard for reuse (spec_03) and
overlap (spec_05). The feature is the roofline model finally arguing with itself.

---

## 1. `TensorSpec` — data, not code

New optional block on `GpuProfile` (`models.py`), following the `Bandwidth`
pattern:

```python
class TensorSpec(CamelModel):
    """Illustrative MMA capability (spec_23). Absent => no tensor path."""
    units_per_sm: int = Field(ge=1, alias="unitsPerSM")   # drawn, not simulated per-unit
    mma_m: int = 16; mma_n: int = 16; mma_k: int = 16     # tile shape per MMA step
    # dtype -> throughput multiplier over bandwidth.macs_per_cycle. The KEY SET
    # is the supported-dtype declaration: absent dtype == unsupported on this die.
    multipliers: dict[DType, float]
```

`DType` widens to `... | "fp8" | "fp4"`; `DTYPE_BYTES` becomes `DTYPE_BITS`
(fp4 = 4 bits — integer bytes can't express it; keep a `dtype_bytes()` helper
returning float, and compute load bytes as `ceil(cells * bits / 8)`).

Profiles (`profiles.py`) gain honest-ratio entries: the generic dies get no
`tensor` block (scalar teaching dies stay scalar); RTX-4060-Laptop declares
fp16/int8/fp8; H100 adds nothing below fp8; **only B300-Blackwell-Ultra
declares fp4** — that a dtype is a *property of the die* is half the lesson.
Multipliers are illustrative but their ratios follow published dense-throughput
ratios per die (e.g. fp16 ≈ 2× fp8 ≈ 2× fp4 per NVIDIA's own tables, ~1/10
scale like the existing bandwidth constants). Comment each entry with its
anchor source, as the fleet block already does.

**camelCase gotcha:** `units_per_sm` would camelize to `unitsPerSm`; it carries
an explicit `alias="unitsPerSM"` exactly like `cores_per_sm`. Verify the TS
type in `types.ts` by hand. `mma_k` → `mmaK` is fine.

## 2. Workload flag — default off, byte-for-byte

`Workload.execution: Literal["cuda", "tensor"] = "cuda"`. The default means
**every existing trace is unchanged** — not "equivalent", identical, and a test
pins it (§6). An enum, not a bool, so a future sparsity mode is a value, not
another flag.

**Unsupported dtype:** requesting `execution="tensor"` with a dtype missing
from the profile's `multipliers` (or on a profile with no `tensor` block) is a
422 from `main.py` with a message naming the die and its supported set — the
engine stays pure and never sees the invalid pair. The UI disables unsupported
dtype options in `Controls` when tensor mode is selected (fp4 greys out on
everything but B300, with a title-attribute explaining why), so the 422 is a
belt-and-suspenders contract, not a user experience.

## 3. Engine semantics — whole tiles per step

In `_simulate_serial`/`_simulate_pipelined`, tensor mode replaces the inner
`for kk in range(k0, k1)` walk with MMA steps: each step consumes
`min(mma_k, k1 - kk)` ranks at once, so `mac_done += tile_cells * ranks_consumed`
— **macDone jumps by tile-worth amounts, stays monotonic, and the final partial
step lands it on exactly `macTotal`** (edge tiles and `N % mma_k != 0` fold into
`ranks_consumed`, same trick as spec_03's partial edge tiles). Loads are
untouched: the same bytes move at the same `bytes_per_cycle`, which is the
point. `cycle` still increments once per emitted state; `k` advances by
`ranks_consumed`. Purity is preserved — no new imports, AST check unchanged.

`SimState` additions: `mma: bool = False` on tensor compute steps, and
`ranks_per_step: int | None` for the counters. `CoreState` gains `"mma"`.

**Rendering decision: per-SM flash, not per-lane painting.** An MMA is issued
by the SM's tensor units, not by 128 scalar lanes — painting individual lanes
`computing` would draw a falsehood. The engine labels *every lane of the owning
SM* `"mma"`, so `DieView`'s dense mode (spec_07) shows the whole SM tile
flashing a distinct color per step, and per-core zoom shows the SM's lanes lit
as one block with a small `×mma_k` badge. `Counters` shows "ranks/step" and the
effective MACs/cycle next to the scalar figure.

## 4. Roofline consequence — the lesson

`analyze()` computes `effective_macs_per_cycle = macs_per_cycle * multiplier`
when `execution="tensor"`, so `ridge_point` moves right by exactly the dtype
factor while `arithmetic_intensity` is unchanged (same bytes, same MACs). The
regime badge flips workloads memory-bound that scalar mode called
compute-bound; `serial_cycles` shrinks on the compute term only, and
`pipelined_cycles` becomes load-dominated — **double-buffering has less compute
to hide loads behind, so the spec_05 win narrows**. The UI states this in one
sentence next to the badge: "faster math, same memory — feed it or starve it."
Interplay with tiling is untouched mechanically (tiles still map whole to one
SM via `tile_aware_core`) but pedagogically sharpened: the tile-size slider is
now the only lever that moves the dot, because dtype moved the roof.

## 5. Honesty ceiling

Illustrative, not cycle-accurate, per house rule. Multipliers are teaching
constants whose *ratios* track published dense-throughput ratios per die;
no sparsity, no clock effects, no per-unit scheduling (`units_per_sm` is drawn
on the anatomy page, not simulated). fp4 accumulation numerics are not modeled
— operands stay the spec_02 floats; dtype affects bytes and rate only. Say so
in an InfoDot.

## 6. Tests (`tests/test_tensor.py` + touches)

- **Default-off regression:** for every profile × representative workloads,
  `execution="cuda"` (and omitted) yields a trace whose serialized JSON is
  byte-for-byte identical to pre-spec_23 output; `Summary` likewise.
- **MMA stepping invariants:** for tensor runs across N ∈ {4, 8, 16, 17, 64},
  tile sizes {0, 3, 8}, both schedules: `macDone` monotonic non-decreasing,
  `<= macTotal` throughout, `== macTotal == N³` at `done`; compute-state count
  per tile `== ceil(tile_k_span / mma_k)`.
- **Ridge ordering pinned per dtype:** on each tensor-capable profile,
  `ridge(fp4) > ridge(fp8) > ridge(fp16) > ridge(scalar)` where declared, and
  regime flips memory-ward (never compute-ward) as dtype shrinks at fixed N.
- **Unsupported dtype:** 422 for fp4 on H100/RTX-4060, for any tensor request
  on Generic-128; error body names the supported set. Engine never raises.
- **Purity:** existing AST check passes untouched; frontend `npm run build`
  type-checks `TensorSpec`/`execution`/`"mma"`.

## 7. Out of scope

No systolic *data-marching* animation (PE-grid choreography is its own spec if
ever); no sparsity; no per-tensor-unit occupancy; no fp4 numerics in the matrix
panels; no live-mode (spec_08+) changes — real kernels already report what they
report. mlp_step gains tensor mode for free via `engine.simulate()` but its
loss numerics stay fp32 — noted in the UI, not simulated.

---

## Implementation notes (2026-08 — as landed)

Implemented after spec_22 (rectangular matmul), spec_24 (occupancy), and
spec_26 (llm_decode) had already landed, at 261 tests; the suite is 322 with
`tests/test_tensor.py`. Deviations and decisions, all deliberate:

- **Rectangular matmul (spec_22).** MMA chunking keys off the *resolved* K:
  the inner walk consumes `min(mma_k, k1 - kk)` ranks over each k-tile span of
  `_ranges(resolve_dims(workload).K, T)`, so partial edge k-tiles and
  `K % mma_k != 0` both fold into `ranks_consumed` exactly as §3 described for
  square N. `analyze()` likewise scales the compute term of the resolved
  M·K·N total.
- **mlp_step and llm_decode inherit tensor mode for free**, as §7 said for
  mlp_step — both chain `engine.simulate()` and restamp counters, and the
  restamping is chunk-agnostic (offsets, not increments). llm_decode postdates
  this spec; the same rule was extended to it. `analyze_llm`'s decode-side
  compute term uses the new `engine.effective_macs_per_cycle()` so the Summary
  agrees; loss/softmax numerics stay fp32 per the honesty ceiling.
- **`DTYPE_BYTES` became `DTYPE_BITS`** (§1) with a float `dtype_bytes()`
  helper; every byte count is `ceil(cells * bits / 8)`, which is exactly
  `cells * bytes` for all byte-aligned dtypes — `test_bits_generalization_
  keeps_every_byte_count` pins the four pre-spec_23 dtypes to their old
  numbers, and the pinned Generic-128 Summary constants prove nothing moved.
- **"Byte-for-byte" is enforced as omitted == "cuda"** plus the invariant
  checks, not against a frozen pre-spec_23 fixture: `SimState` gained two
  always-default keys (`mma: false`, `ranksPerStep: null`), so serialized
  JSON necessarily has two more fields per state — the same precedent as the
  spec_03/04/05 field additions. All 261 pre-existing tests pass unchanged.
- **The engine never raises on an unsupported pair** — `tensor_multiplier()`
  returns None for a missing TensorSpec *or* an undeclared dtype and the
  builders fall back to the scalar path; `main.py` 422s the pair at the API
  edge (message names the die and its supported set) so the fallback is
  defense in depth, never UX. The UI additionally snaps an invalid
  execution/dtype combination to a valid one before the request leaves the
  browser (die without tensor units → back to "cuda"; undeclared dtype → the
  die's first declared dtype), so the 422 is unreachable from the controls.
- **Multiplier data (illustrative scale, honest ratios):** all five
  tensor-capable dies use fp16 4.0 with int8/fp8 at 8.0 where declared;
  B300-Blackwell-Ultra alone adds fp4 16.0 (and deliberately omits int8 —
  Blackwell Ultra demoted dense int8; fp8 is its quantized path). bf16 = fp16
  on H100/B300/MI300X. RTX-4060-Laptop and RTX-5090 skip bf16 (GeForce
  marketing tables lead with fp16/fp8/int8); fp32 is never declared —
  the scalar path is fp32's home and TF32 stayed out of scope. Generic-128 /
  Generic-512 carry no TensorSpec: the teaching dies stay scalar.
- **`units_per_sm` = 4 everywhere** (4 tensor cores per NVIDIA SM, 4 matrix
  cores per CDNA 3 CU) — carried as data with the `alias="unitsPerSM"`
  camelCase pin, drawn nowhere yet (the anatomy-page rendering §1 mentions is
  future work; nothing consumes it beyond the wire contract today).
- **Rendering** followed §3 exactly: the engine labels every lane of each
  owning SM `"mma"` (`_state` expands the tile's lanes to whole-SM blocks),
  `DieView` paints `--core-mma` in both dense and per-core modes with an
  `MMA ×ranks` badge, the Legend gained the entry, and `Counters` shows
  ranks/step + effective-vs-scalar MACs/cycle plus the one-sentence roofline
  note ("faster math, same memory — feed it or starve it").
- **No new API routes** — the 23-route snapshot in `test_smallwins3.py` is
  untouched; validation rides the existing `POST /api/simulate`.
