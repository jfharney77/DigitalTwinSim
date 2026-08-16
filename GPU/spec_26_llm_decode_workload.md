# Spec 26 — LLM decode: the matmul that runs out of arithmetic

**Status:** proposed
**Builds on:** `spec_04_bandwidth_model.md` (roofline), `spec_06_neural_network.md`
(op chaining, the template this spec copies deliberately).
**Companion:** the `DellProMaxPlus/` twin teaches prefill vs decode from the
device side; this spec closes the loop from the GPU side — decode *is* the
memory-bound roofline regime that twin keeps pointing at.

---

## 0. Why this, in plain terms

Spec_06 gave the matmul a purpose (training). This spec gives it a *predicament*:
one token step of a toy transformer, where the interesting thing is not the
arithmetic but the **KV cache** — the growing pile of past keys and values that
every new token must re-read in full.

The lesson: as the sequence grows, the bytes grow and the useful MACs barely do.
Arithmetic intensity falls, the roofline dot slides left, and the same die that
was compute-bound at a short context is memory-bound at a long one. Nothing about
the silicon changed; the *workload's shape* changed. That is why decode speed is
quoted in GB/s, not TFLOPs.

## 1. One decode step and its ops

A single transformer block at hidden size N, decoding **one token each for N
independent streams** (a serving batch — the batch is what lets the weight
matmuls stay square and shared, exactly the everything-is-N trick of spec_06 §1).
Each stream owns a private KV cache of length `S = kv_len`, split into
`B = ceil(S/N)` blocks of N tokens for the square engine.

Deterministic data from a seed (extends `matrices.py` with `make_llm_data`):
activations `X` (N×N, one row per stream), six weights `Wq Wk Wv Wo Wup Wdown`
(all N×N), and an initial KV cache built by *really running* the seeded prompt
through Wk/Wv — the cache contents are true arithmetic, not filler.

| # | Op | Computation | Kind |
|---|-----|-------------|------|
| a1–a3 | Q/K/V projection | `Q = X·Wq`, `K = X·Wk`, `V = X·Wv` | 3 matmuls |
| a4 | cache append | new K,V rows join the cache | pointwise |
| a5 | attention scores | `S = Q·K_cacheᵀ / √N`, per cache block | B matmuls |
| a6 | softmax | rows normalized to probabilities | pointwise |
| a7 | weighted values | `A = P·V_cache`, per cache block | B matmuls |
| a8 | output projection | `O = A·Wo` | matmul |
| a9 | residual + norm | `H = norm(X + O)` | pointwise |
| a10 | MLP up | `Z = H·Wup` | matmul |
| a11 | activation | `G = gelu(Z)` | pointwise |
| a12 | MLP down | `M = G·Wdown` | matmul |
| a13 | residual | `X' = H + M` | pointwise |

So `6 + 2B` matmuls and 5 pointwise flashes per token. `Workload.steps` is
reused as **tokens generated**: the cache grows by one row per token
(`S_t = kv_len + t`), so later tokens genuinely cost more than earlier ones.
A `prefill: bool` knob (default false) is the one-knob contrast: prefill runs
the *same op list* for a whole N-token prompt block at once, so the attention
matmuls are ordinary square matmuls with full operand reuse — batch of tokens
vs one token, two regimes from one switch.

The numerics are real, mlp.py-style: softmax is a true exp/normalize (rows sum
to 1), gelu and the residuals are actual arithmetic, and the same seed always
produces the same attention weights. Not an accurate transformer — one block,
one head, tied dims — but never fake numbers.

## 2. What changes in the model

- `Workload.kind` becomes `"matmul" | "mlp_step" | "llm_decode"`; new fields
  `kv_len: int` (8–64, default 8; camelizes cleanly to `kvLen`) and
  `prefill: bool = False`. `steps` doubles as tokens (decode) / blocks (prefill).
- A pure `llm.py` built **exactly like `mlp.py`**: chains `engine.simulate()`
  once per matmul op (tiling, bandwidth stalls, and double-buffering apply per
  op unchanged), strips per-op idle/done bookends, restamps cycle/mac counters
  onto one continuous trace, stamps `op_index`/`op_count`/`op_name`/`step_index`
  onto every state, and emits pointwise ops as one flash state each. No timers,
  no IO — the AST purity check extends to `llm.py`.
- The response carries `LlmInfo`: the op list (reusing the `MlpOp` wire shape),
  `kv_len` per token, per-token `intensity: number[]` (the number to watch, as
  `loss` was for spec_06), and the final softmax row for display.
- **`analyze_llm` owns the roofline arithmetic**, the way `analyze_mlp` does.
  Per token at cache length S, dtype width b bytes:
  - `MACs = N²·(6N + 2S)` — six shared weight matmuls plus the two attention
    sweeps over the cache.
  - `bytes = b·N²·(12 + 2S)` — the six weight matmuls at the engine's standard
    2N²b each, plus the per-stream K and V caches read once, unshared.
  - `intensity(S) = (6N + 2S) / (b·(12 + 2S))` — starts at the plain matmul's
    N/2b when S→0, falls monotonically for every N > 2, floors at 1/b.
  Honesty note (spec_06's fidelity-ceiling clause, sharpened): the *drawn*
  attention matmuls share their cache-block operand across rows, which
  under-charges KV traffic — real streams do not share caches. The trace is the
  drawing; the Summary is the accounting; the spec says so out loud with a ⓘ.
- Prefill's Summary uses the engine's ordinary per-matmul accounting (full
  reuse), so prefill vs decode differ in the books exactly where they differ in
  reality: the attention ops.

## 3. UI

Extends the simulator page (no new tab); Dell clean-design rules apply.

- Workload picker gains `LLM token decode`; a `KV cache length` slider and the
  `Prefill` toggle appear only for it.
- **`OpPipeline.tsx` is reused as-is** — the op tiles are `MlpOp`-shaped, so the
  strip renders `Q = X·Wq`, `softmax`, `A = P·V (block 2/8)`, … with no new
  component. Cache-block matmuls show their block ordinal in the name, never a
  separate numbering row.
- Matrix panels show the current op's operands; during attention the B operand
  is the cache block, labeled `K-cache 2/8` so the re-reading is visible.
- Counters add `KV length` (live, growing per token), `intensity` (falling per
  token), and the regime badge — watching it flip from `compute` to `memory` as
  the slider grows is the whole demo. The roofline read-out draws the dot per
  token so the leftward slide is a trail, not a claim.

## 4. Invariants (added to the non-negotiables)

Enforced by a new `tests/test_llm.py`:

- `macTotal = Σ_t (6 + 2·ceil((kv_len + t)/N))·N³` over tokens t, reached
  exactly at `done`; prefill: `steps × 8N³`.
- Op order per token is exactly a1…a13 (with a5/a7 expanded to their B blocks
  in cache order), pinned by name.
- Every spec_01–05 invariant holds inside each matmul op (five-phase order,
  monotonic `macDone`, tile-aware mapping, utilization arithmetic,
  prefetching only when enabled).
- **`intensity(kv_len=64) < intensity(kv_len=8)`** at N=8, fp32 — the pinned
  fall (0.314 < 0.571 by the §2 formula), plus strict monotone decrease across
  kv_len for all N ≥ 4.
- **Regime flips**: at N=8, fp32, `analyze_llm(kv_len=8).regime == "compute"`
  and `analyze_llm(kv_len=64).regime == "memory"` against the ridge point 0.5;
  prefill at the same N and kv_len stays `"compute"`.
- Softmax rows sum to 1 (±1e-9); all values finite; same seed, same trace.

## 5. Scope guardrails and the spec_22 upgrade

- One block, one head, hidden = head = batch = N: square-N is a *stated
  simplification*, as in spec_06 §5. When rectangular M×K×N work (a future
  spec_22-style generalization — not landed as of this writing) arrives, the op
  list survives verbatim: scores become a true 1×N·N×S per stream, the MLP
  widens to 4N, and only §2's shape column and constants change.
- kv_len caps at 64 and N at 8 for this workload — at N=8, kv_len=64 a token is
  22 matmuls, watchable but honest about being a toy.
- No sampling, no logits, no multi-layer stacks: the produced token is not the
  point; the traffic to produce it is.
- Timings and byte counts stay illustrative (spec §1): favor the correct mental
  model — *decode starves for bandwidth as context grows* — over correct
  numbers.

## Implementation notes

Implemented 2026-08 as the SQUARE version specced above, against a codebase
where spec_22 (rectangular matmul) and spec_24 (occupancy on Summary) had
already landed. Where the wiring assumptions above differ from the code as
built, the code wins; the deltas:

- **spec_22 interaction.** §5's "not landed as of this writing" is stale —
  rectangular matmul exists. `llm_decode` stays square anyway (as this spec
  intends): nonzero `M`/`K` on an `llm_decode` workload is rejected 422 via
  the same model validator `mlp_step` uses, and the §5 N-cap (N ≤ 8) is
  enforced there too. `kv_len`/`prefill` on non-llm kinds are **ignored**,
  not rejected — they carry harmless defaults, so every persisted request
  stays valid (the same reasoning spec_24 used for the residency fields);
  a regression test pins that a decorated matmul trace is byte-identical.
- **Token indexing.** "S_t = kv_len + t" is read with t = 1..steps and the
  cache append (a4) preceding the attention sweep, so token 1 attends over
  kv_len + 1 entries. The §4 macTotal sum is pinned in `test_llm.py` under
  exactly that reading.
- **`LlmInfo` carries one extra field**, `ops_per_token: int[]` (Σ = ops
  length), because ops per token vary (11 + 2B) and the frontend needs the
  token boundaries to slice the strip; `MlpInfo.ops_per_step` has no analogue
  here. `OpPipeline.tsx` is reused unmodified: `App.tsx` hands it a per-token
  `MlpInfo` view (the current token's ops, `opsPerStep` = that token's count).
- **Shared-cache numerics.** The drawn model shares one KV cache across the
  N streams (the honesty-note simplification, taken literally in the
  arithmetic too): a4 appends stream 0's new K,V row, so the cache grows by
  one row per token as §1 states. Softmax runs over the true S positions —
  partial cache blocks are zero-padded only in the *drawn* N×N operands,
  never in the math — and is max-subtracted for stability; rows sum to 1
  within 1e-9. Weights are 1/N-scaled so repeated blocks stay O(1).
- **Prefill** starts from an empty cache (the prefill *is* the prompt run)
  and reuses the same seeded X per block; attention runs over the current
  block only (`S = Q·Kᵀ/√N`, `A = P·V`, no ordinals), cache length grows N
  per step, and its per-step intensity is the full-reuse N/2b. Its Summary
  scales the engine's per-matmul accounting by steps × 8, exactly as
  `analyze_mlp` scales by steps × 5.
- **`analyze_llm`** builds on `engine.analyze` of a matmul copy so the
  spec_24 occupancy and the ridge point ride through unchanged, then
  replaces the byte/MAC books with the §2 per-token formulas. Aggregate
  intensity over the run (S_t = kv_len + t) differs slightly from the
  single-shot `llm_intensity(N, kv_len, b)` the §4 numbers pin; both are
  tested, and the regime flip holds either way at N=8/fp32.
- **UI**: no roofline *plot* exists on the simulator page, so "the leftward
  slide is a trail, not a claim" is rendered as the Counters' per-token
  intensity list with a falling sparkline (the same idiom as spec_06's loss
  trail), plus live KV length and a per-token regime read-out beside the
  run-level badge.
- No new API routes; `/api/simulate` branches on `kind` and the 23-route
  snapshot test is untouched. Suite went from 246 to 261 tests.
