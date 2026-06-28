# Spec 02 — Show the actual A, B, C matrices

**Status:** proposed (next feature)
**Builds on:** `initial_spec.md` (the foundation), which is now implemented as a FastAPI backend + React frontend.
**Roadmap ref:** this is near-term item #2 ("Show the actual A / B / C matrices beside the die, filling in as MACs complete").

---

## 0. Why this feature, and why first (read this if GPUs are new to you)

Right now the app shows a GPU die with cores lighting up and a counter that says
"MACs done: 16 / 64". That teaches *where* work happens and *how much* is done —
but it never shows *what is actually being computed*. A newcomer is left asking
"what's a MAC, and what are these cores actually multiplying?"

A quick vocabulary primer (everything this feature makes visible):

- **Matrix multiply (matmul)** `C = A × B`. Every cell of the result `C[i][j]` is
  computed by walking across **row `i` of A** and **down **column `j` of B**,
  multiplying the pairs and adding them up:
  `C[i][j] = A[i][0]*B[0][j] + A[i][1]*B[1][j] + ... + A[i][N-1]*B[N-1][j]`.
- **MAC** = "multiply-accumulate" = one `a*b` plus adding it onto a running total.
  It is *the* fundamental operation a GPU does for matmul. For an N×N matmul there
  are `N` MACs per output cell, and `N*N` output cells, so `N*N*N` MACs total —
  exactly the "of total" counter you already see.
- **`k`** (the index in the animation's "MAC accumulate · k=2/4" label) is the
  step *along that row/column*. At each `k`, every output cell does one more MAC
  and gets a little closer to its final value.

So the single biggest "aha" we can give a novice is to **draw A, B, and C as grids
of numbers and fill C in, one `k`-step at a time**, while the matching row of A and
column of B light up. The die animation (cores doing the work) and the math
(numbers appearing in C) become two views of the *same* event. This is more
valuable for understanding than any deeper hardware feature (tiling, tensor cores)
we could build next — those are optimizations of a process you must first *see*.

It's also low-risk: no new hardware concepts, no change to the phase model, and it
reuses the `k` value already present in every `SimState`.

---

## 1. What the user will see

Beside (or below) the die, three labeled grids: **A**, **B**, **C**.

- On **Run**, A and B are shown fully (they're the inputs).
- During **COMPUTE**, as `k` advances `0 → N`:
  - **A column `k`** highlights and **B row `k`** highlights (the operands being
    consumed this step).
  - Every cell of **C** updates to its running partial sum after `k` MACs.
- When a C cell reaches its final value (after the last `k`), it flashes the same
  "result written" color used on the cores (`--core-hot`), tying the two views
  together.
- Hovering a C cell shows its formula expansion, e.g.
  `C[1][2] = A[1][0]·B[0][2] + A[1][1]·B[1][2] + ...` with completed terms bold.

Small-N only (the existing 2–8 slider). These grids are meant to be readable, not
to scale to real tensors — consistent with the spec's "tens to low-hundreds of
elements" guardrail.

---

## 2. Where the numbers come from (determinism)

The matrices must be **deterministic** so the same inputs give the same picture
(core principle from `initial_spec.md` §1). Two options:

- **Recommended:** backend generates A and B from a fixed rule (e.g.
  `A[i][j] = i + j`, `B[i][j] = (i == j) ? 1 : ...`, or a small seeded pattern that
  produces legible 1–2 digit numbers). It returns A and B in the simulate response;
  the frontend computes C's partial sums from `k` itself (it already knows the
  trace). This keeps payloads tiny and the engine pure.
- Alternative: backend precomputes the partial-C at every `k` and ships it in each
  `SimState`. Simpler frontend, but redundant data. Prefer the recommended option
  unless profiling says otherwise.

Keep values small and integer so the grid stays readable; this is a teaching tool,
not a numerics demo.

---

## 3. Data-model changes

Additive only — nothing in `SimState` changes, so existing tests stay green.

**Backend (`backend/app/`):**
- `workload.py` model: add optional `seed: int = 0` (future-proofing; default
  deterministic).
- New `matrices.py`: `make_operands(n, seed) -> (A, B)` returning `list[list[int]]`.
  Pure, unit-testable.
- `SimulateResponse`: add `a: list[list[int]]` and `b: list[list[int]]`.
- (No change to the engine or phases.)

**Frontend (`frontend/src/`):**
- `types.ts`: add `a`/`b` to `SimulateResponse`.
- New `components/MatrixPanels.tsx`: renders A, B, C. Computes partial C from the
  current `SimState.k`:
  `Cpartial[i][j] = sum over kk in [0, k) of A[i][kk] * B[kk][j]`.
  (During `load`/`idle`, C is blank; during `writeback`/`done`, C is full.)
- `App.tsx`: store `a`/`b` from the response; pass them + current `state` to
  `MatrixPanels`.

---

## 4. Visual language (extend, don't replace)

Reuse existing color tokens so the two views read as one system:

| Element                         | Token         | Meaning                          |
|---------------------------------|---------------|----------------------------------|
| A column `k` / B row `k` active | `--core-on`   | operands feeding this MAC step   |
| C cell just finalized           | `--core-hot`  | result written (matches cores)   |
| C cell partial / in progress    | `--core-off`  | accumulating, not done           |

---

## 5. Non-goals (defer to later specs)

- **No tiling yet.** Real GPUs don't load a whole matrix at once; they stream
  *tiles* (small blocks) through fast on-chip memory. That's the *next* spec after
  this one (roadmap #3) and is where memory hierarchy gets taught. Showing the full
  matrices first gives us the baseline to later contrast against tiling.
- **No non-square / M×K×N yet** (roadmap #1). Keep it N×N here; generalizing dims
  is a mechanical follow-up once the panels exist.
- **No tensor-core / systolic view** (roadmap #4) — that's a different animation
  mode entirely.

---

## 6. Testing

- `make_operands` is deterministic: same `(n, seed)` → identical A, B.
- Partial-C helper (wherever it lives): for N=2 with known A, B, the partial sum at
  `k=1` equals `A[i][0]*B[0][j]`, and at `k=N` equals the true matmul `C`.
- Invariant tie-in: the number of finalized C cells at `phase==done` is `N*N`, and
  total MACs implied by the panels equals `macTotal`.

---

## 7. Open questions

- One seeded pattern, or let the user pick (identity / counting / random-seeded)?
  A dropdown of 2–3 "example matrices" could itself be instructive.
- Show C partial sums as numbers the whole time, or only reveal a cell once final
  (less noisy but hides the accumulation)? Recommend showing partials — the
  accumulation *is* the lesson.
- Layout: panels beside the die (wide screens) vs. below it (narrow). Reuse the
  existing responsive breakpoint at 880px.
