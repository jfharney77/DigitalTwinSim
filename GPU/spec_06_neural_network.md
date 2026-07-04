# Spec 06 — A tiny neural network: matmuls with a purpose

**Status:** proposed
**Builds on:** `spec_03_tiling.md` (tiling), `spec_04_bandwidth_model.md` (roofline),
`spec_05_double_buffering.md` (pipelining).
**Roadmap ref:** initial_spec §7 "workloads beyond a single matmul"; the M×K×N
generalization is an upgrade path, not a prerequisite (see §2).

---

## 0. Why this, in plain terms

So far the die multiplies two matrices because we told it to. This spec gives the
matmul a *reason to exist*: one training step of the smallest useful neural network,
a two-layer fully connected MLP.

The payoff is seeing that "training a neural network" is not a new kind of
computation — it is the **same matmul, five times in a row, with different
operands**. The forward pass is two matmuls; backpropagation is three more; the
learning itself (the weight update) is a cheap elementwise subtraction. Everything
the previous specs taught — tiling, bandwidth stalls, double-buffering — applies to
each of the five without modification.

### The lessons it makes visible

- **Training ≈ 3× inference.** Inference runs 2 matmuls (one per layer); a full
  training step runs 5 plus pointwise work. Watching the op pipeline fill in makes
  the "training is roughly three times the FLOPs of a forward pass" rule concrete.
- **Backprop is just transposed matmuls.** `dW2 = A1ᵀ·δ2` runs on the exact same
  silicon as `Z1 = X·W1`; only the operands change. There is no separate "backprop
  circuit".
- **Loss goes down.** Run several steps and watch a number improve because of
  arithmetic you just watched happen, MAC by MAC.

---

## 1. The network and its matrix operations

A 2-layer MLP with ReLU, trained on a fixed toy batch by SGD with mean-squared
error. To reuse the existing **square** N×N engine unchanged, every dimension is N:
batch B = input D = hidden H = output C = N (see §2 for the honest caveat).

Deterministic data from a seed (extends `matrices.py`):
input `X` (N×N), target `Y` (N×N), weights `W1`, `W2` (N×N).

**Forward pass — 2 matmuls + 1 pointwise:**

| # | Op | Computation | Kind |
|---|-----|-------------|------|
| f1 | hidden pre-activation | `Z1 = X · W1` | matmul (N×N·N×N) |
| f2 | activation | `A1 = relu(Z1)` | pointwise |
| f3 | output | `Z2 = A1 · W2` | matmul |

**Loss (pointwise):** `L = ½‖Z2 − Y‖²` and its gradient `δ2 = Z2 − Y`.

**Backward pass — 3 matmuls + 1 pointwise:**

| # | Op | Computation | Kind |
|---|-----|-------------|------|
| b1 | output-layer gradient | `dW2 = A1ᵀ · δ2` | matmul |
| b2 | backpropagated error | `δ1 = (δ2 · W2ᵀ) ⊙ relu′(Z1)` | matmul + mask |
| b3 | input-layer gradient | `dW1 = Xᵀ · δ1` | matmul |

**Update (pointwise):** `W1 ← W1 − η·dW1`, `W2 ← W2 − η·dW2`, with a small fixed
learning rate (η = 0.01) so the numbers stay tame.

Note on the transposes: the engine simply multiplies the transposed array. On real
hardware a transpose is usually free — the kernel reads the same memory with
swapped strides — which is worth a ⓘ info-dot in the UI, not extra simulation.

## 2. What changes in the model

- `Workload.kind` becomes `"matmul" | "mlp_step"`. For `mlp_step`, `N` sets every
  dimension; `steps` (default 1, max ~10) repeats the whole 5-matmul sequence.
- The engine gains a pure `simulate_mlp(profile, workload) -> list[SimState]` that
  **chains** the existing per-matmul simulation once per matmul op, exactly as
  `simulate` runs today (tiling, bandwidth costs, and double-buffering all apply
  per op). No timers, no IO — same purity rule as always.
- `SimState` gains op context, mirroring how spec_03 added tile context:
  `op_index`, `op_count`, `op_name` (e.g. `"forward · Z1 = X·W1"`), and
  `step_index` for multi-step runs. Null for plain matmul workloads.
- Pointwise ops (relu, loss/δ2, SGD update) are **one state each**: every mapped
  core flashes `computing` for one cycle with `cycle_cost=1`, memory idle. They
  exist so the pipeline reads honestly, not to model elementwise bandwidth (that
  contrast is spec_07 territory — see §6).
- Numerics switch from display-friendly ints to floats rounded to 2 decimals in
  the panels; operands stay deterministic per seed.
- The response carries per-step `loss: number[]` so the UI can show it falling
  without recomputing anything client-side.

Fidelity ceiling, same spirit as spec_04: this demonstrates *which* matmuls
training runs and *in what order* — it is not a numerics-accurate autograd.

## 3. UI

Extends the simulator page (no new tab); Dell clean-design rules apply.

- **Workload picker**: `Matrix multiply` | `Neural-net training step` in the
  Workload card.
- **Op pipeline strip** above the matrix panels: one tile per op, title only
  (`Z1 = X·W1`, `relu`, `Z2 = A1·W2`, `δ2 = Z2−Y`, `dW2 = A1ᵀ·δ2`, `δ1`, `dW1`,
  `update`) — active tile blue border, done tiles get a check glyph and the blue
  tint fill. **No numbering** (the ordinal is the position).
- **Matrix panels** show the current op's two operands and its output, labels
  switching with `op_name`; the C-panel accumulation visual works unchanged.
- **Counters** add `loss` (current, and per-step history when `steps > 1`) and
  `op` (`3 of 8` style text is banned — use the op name).
- The phase read-out prefixes the op: `dW2 = A1ᵀ·δ2 · MAC accumulate · k=2/4`.

## 4. Invariants (added to the non-negotiables)

Enforced by a new `tests/test_mlp.py`:

- `macTotal = steps × 5 × N³` and `macDone` reaches it exactly at `done`.
- Op order is exactly f1, f2, f3, loss, b1, b2, b3, update, repeated per step;
  phases inside each matmul op follow the spec_01 five-phase order.
- All spec_01–05 invariants hold within every matmul op (utilization, tile-aware
  mapping, monotonic `macDone`, prefetching only when enabled).
- For the canned seed and η = 0.01, `loss[k+1] < loss[k]` for the first 5 steps —
  the network genuinely learns, and the test proves it.
- Weights remain finite (no NaN/inf) for all supported N and steps.

## 5. Scope guardrails

- N stays 2–8; at N=4 one step is 320 MACs — watchable, not GPU-scale.
- One fixed architecture (2 layers, ReLU, MSE). Depth/activation/optimizer
  choices are out of scope; they multiply UI without adding a new lesson.
- No convergence claims beyond the seeded assertion; η is fixed, not a control.
- Square-only dims is a *stated simplification*: real MLP layers are rectangular
  (B×D · D×H). Adopting M×K×N (roadmap) later upgrades this spec without
  changing its op structure.

## 6. Other workloads this opens up (candidate specs 07+)

Each is one more "the GPU is just doing matmuls/moves" lesson, in the same style:

- **spec_07 — Vector add / SAXPY:** the anti-matmul. Intensity ≪ ridge point, so
  it is *always* memory-bound — makes the roofline's other regime visceral, and
  gives pointwise ops the honest bandwidth model §2 skips.
- **spec_08 — One attention head:** `S = Q·Kᵀ`, `P = softmax(S)`, `O = P·V` — the
  transformer kernel is two matmuls around a pointwise op the die already knows
  how to show.
- **spec_09 — Convolution via im2col:** unroll a small image into columns and the
  "different" CNN operation literally becomes the same matmul.
- **spec_10 — Parallel reduction:** summing N² values in a log-depth tree; watch
  active cores halve every step — the utilization decay matmul never shows.
