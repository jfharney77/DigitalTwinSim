# spec_18 — lesson tours (the curriculum works without a GPU)

**Goal:** fold the CUDA lessons into the repo's narrated tour mode
(`../ACTIVE_TWIN_SPEC.md`): each lesson's canned recording plays as a
captioned tour beat, so the curriculum teaches on any machine — and the Live
tab becomes the tour's closing "now you do it" step.

## Design

- **Recordings as tour data.** Each lesson gets a golden session JSONL in
  `backend/tours/lessons/NN_name.jsonl` — captured once from real hardware
  (first run after the toolkit lands) or, until then, the existing
  representative probe samples wrapped in stamps. Labeled honestly either
  way: `"recorded on RTX 4060 Laptop"` vs `"representative data"` in the
  tour caption — never unlabeled synthetic frames (repo rule).
- **Backend `tour.py`** (pure, per the tour spec's §4 shapes): a `Tour` whose
  steps are `{script, lessonId, traceCursor}` — the tour pins frames of the
  replayed lesson recording exactly the way sim tours pin `SimState`
  indices. `GET /api/tour` serves it. Tests: every `lessonId` resolves to a
  recording; every `traceCursor` is a valid frame; scripts non-empty;
  monotonic cursors (all inherited from the tour spec's invariant list).
- **Frontend.** The Live tab gains a "▶ Guided lessons" button: plays the
  recording through the *existing* replay path (clock already frontend-owned)
  while a caption panel walks the script — camera work is minimal here (the
  die view is one viewport), so this is the cheapest tour in the repo and a
  good second implementation after the PowerStore pilot.
- Each beat ends with the lesson's experiment as a prompt; the final beat of
  every tour is the same: "your GPU can do this live — `make run-NN`" with
  the connection badge visible.

## Invariants

- Tour engine purity + resolvable ids (`tests/test_tour.py`, same harness
  style as the tour spec prescribes).
- Recording provenance label required per step (hardware vs representative)
  — a test asserts the field is set, the UI must render it.
- Replay of every golden recording is 200 and non-empty in CI.

## Files

`backend/app/tour.py` + `backend/tours/lessons/*.jsonl` + `tests/test_tour.py`,
`main.py` (route), `frontend/src/components/{LessonTour.tsx}`,
`LivePage.tsx` (entry button), `cuda/README.md` (mention).

**Effort:** M here, assuming the shared tour player lands first via
`ACTIVE_TWIN_SPEC.md`'s PowerStore pilot; L if this goes first.
**Depends on:** ACTIVE_TWIN_SPEC §4 data model (shared), spec_10 optional.
