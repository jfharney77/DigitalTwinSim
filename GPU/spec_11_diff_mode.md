# spec_11 — diff mode (pin two kernel runs side by side)

**Goal:** the curriculum's core moments are comparisons — naive vs tiled
(lessons 04/05), block-size sweep entries (lesson 03). Let the user pin two
timeline chips and see two dies, two counter columns, and a delta row.

## Design

- **Frontend only.** No backend change: both frames are already in the buffer
  or a replayed trace. `LivePage` gains a compare state
  `{a: number | null, b: number | null}` (frame indices). Timeline chips get
  a small "pin A / pin B" affordance (shift-click = pin B). When both are
  set, the stage renders `ComparePane.tsx`: two `LiveDieView`s at half width,
  a counters table with columns A, B, and Δ (elapsed ms, occupancy,
  blocks/SM spread — max−min block count across SMs), and the Gantt strips
  (spec_10) stacked if available.
- **Frame identity, not index.** Pins must reference `tMs + kernel` keys, not
  raw buffer indices — the buffer trims at its cap and indices shift (the
  latent bug found in the 2026-07 review; fix it here for the plain timeline
  too by keying pins the same way).
- Delta copy stays neutral and honest: faster/slower in ms and %, never
  "better/worse" — occupancy up is not always speed up, which is lesson 03's
  entire point.

## Invariants

- Frontend-only: `npm run build` plus a pure helper `frameKey(state)` with a
  unit test if a test runner exists; otherwise the helper stays trivial
  enough to review by eye.
- Pinning survives buffer trimming (pin two frames, ingest past the cap,
  assert both still resolve — manual QA script in the PR description).

## Files

`frontend/src/components/ComparePane.tsx` (new), `LivePage.tsx` (pin state,
chip affordance, frame-key lookup), `types.ts` (no wire change).

**Effort:** M. **Depends on:** nothing (richer with spec_10).
