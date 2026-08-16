# spec_28 — fleet replay ("this recording on that die")

**Goal:** the fleet profiles exist (`profiles.py`: H100-SXM 132 SMs,
B300-Blackwell-Ultra 160, RTX-5090 170, MI300X 304) and the lesson-07 tour
recordings already carry H100/B300 `device_info` — but every *captured*
session is welded to the die it ran on. Let any recorded session or tour
recording replay **remapped** onto another fleet member's SM count: the same
24-SM laptop matmul, viewed as-if scheduled on an H100's 132 tiles. The
payoff is comparative — same kernel, two dies, watch the wash spread thinner.

## Design

### The remap is a pure function in the fold layer

- New pure module `backend/app/remap.py` (live.py-adjacent; the same AST
  purity check carries over — no fastapi/time/file imports, ever):
  `remap_events(events: list[StampedEvent], target: GpuProfile) ->
  list[StampedEvent]`. It rewrites the event stream, then the *existing*
  `replay()` folds it — no second render path, no forked `LiveState` logic.
- Rewrite rules: the session's `device_info` is replaced by one built from
  the target profile (`name`, `smCount = rows*cols`; the other fields stay
  `None` — we do not invent `maxThreadsPerSm` for a die we never touched).
  Each `kernel_launch`'s `BlockRecord`s are redistributed **deterministically
  round-robin in launch order**: sort records by `start` (ties broken by
  original `(smid, start)` — total order, so the function is a function),
  then record *i* lands on target SM `i % targetSmCount`. Launch order and
  every `start`/`end` stamp are preserved byte-for-byte; only `smid` changes.
  `kernel_progress` per-SM counts are re-bucketed by the same rule.
- **What stays true under remap** (kept, verbatim): block count, grid and
  block dims, per-block durations and launch order, kernel name, elapsed ms,
  `recordsDropped`, sampling flags, telemetry (`gpu_sample` frames pass
  through untouched — the wattage was measured on the *recorded* die and is
  labeled as such, see below).
- **What is invented**: which SM each block lands on, per-SM `blocksRun`,
  per-SM queue depth and the Gantt's row assignment, occupancy per SM, the
  idle-tile count. Everything downstream of placement is a model.

### The honesty rule dominates everything

- A remapped frame is **modeled, never measured**. `LiveState` gains
  `placement: Literal["measured", "modeled"] = "measured"` and
  `recordedOn: str | None`. `remap_events` injects a marker the fold turns
  into `placement="modeled"`, `recordedOn=<original device name>` on every
  frame — including sample frames, whose telemetry is real but is now
  captioned against a die it did not run on.
- The UI must render the label on every remapped view:
  **"modeled placement (recorded on RTX 4060 Laptop)"** in the die header,
  same load-bearing style as spec_18's provenance captions — `test_tour.py`
  is the enforcement precedent.
- **Mixing modeled frames into a real session's history is forbidden.**
  Remap exists only on the read path; `ingest`/`ingest/batch` never accept a
  modeled event, and nothing remapped is ever written to `sessions/*.jsonl`.
  Test: POSTing an event stream containing the remap marker → 422, and a
  remapped trace request leaves the session file byte-identical.

### API — query param, not a new route

`test_api_surface_snapshot` pins all 23 `/api` routes **by path**, so the
cheap-and-deliberate choice is a query param on the two existing trace
routes: `GET /api/live/sessions/{id}/trace?asProfile=H100-SXM` and
`GET /api/tour/recordings/{lesson_id}?asProfile=...`. No path changes → no
snapshot edit; state that in the PR anyway so the non-edit is visibly
deliberate. `asProfile` must name a profile in `profiles.PROFILES`
(unknown name → 404, same shape as the anatomy lookup); remapping onto the
recording's own device is allowed and is the identity (still labeled
modeled? **no** — identity remap short-circuits to the plain replay, because
labeling measured data modeled is the honesty rule inverted).

### UI

- Replay controls gain a die-picker dropdown ("View on: … recorded device /
  H100-SXM / B300-Blackwell-Ultra / RTX-5090 / MI300X") that refetches the
  trace with `asProfile` and keeps the cursor (frame count is unchanged —
  remap is 1:1 on frames, so `frameKey()` still resolves).
- `ComparePane` learns to play recorded-vs-remapped side by side: pane A the
  recorded trace, pane B the same trace remapped, advancing on one cursor.
  This is the feature's actual argument — 240 blocks washing over 24 tiles
  vs puddling on 132, blocks/SM spread collapsing toward 1-and-0.
- Occupancy/straggler read-outs: durations are kept, so the straggler block
  is still the straggler — which is honest (its work didn't shrink) and also
  the limit of the model: on the real H100 that block would have the SM to
  itself and may not straggle at all. The read-out says so in one line:
  "durations recorded on <device>; a bigger die changes queueing, not the
  work". Occupancy stays `theoretical` and is recomputed against the target
  SM count; measured occupancy (spec_15) is never shown on a modeled frame.

## Invariants (tests)

`tests/test_remap.py` + extensions to `test_live.py`/`test_tour.py`:

- **Purity:** `remap.py` passes the same AST check as `live.py`.
- **Conservation:** for every fixture × every fleet profile, total blocks,
  grid, kernel names, elapsed ms, and frame count are identical pre/post.
- **Determinism:** remapping twice is byte-identical; identity remap
  (target == recorded device) returns the unremapped trace.
- **Provenance:** every remapped frame has `placement == "modeled"` and a
  non-empty `recordedOn`; no unremapped frame ever does; the frontend
  renders the label (grep-level check in the component, spec_18 style).
- **Isolation:** ingest rejects modeled events (422); session files
  untouched by remapped reads.
- **API edges:** unknown `asProfile` → 404; malformed → 422;
  `test_api_surface_snapshot` unchanged — assert that in the PR, not in code.
- **Queue shape:** on a target with `smCount >= blockCount`, every SM runs
  ≤1 block (the spread-thinner claim, pinned).

## Files

`backend/app/remap.py` (new), `live.py` (two `LiveState` fields, fold marker),
`main.py` (two query params), `tests/test_remap.py`,
`frontend/src/{types.ts,api.ts}`, `components/{LivePage.tsx,ComparePane.tsx,
LiveViz.tsx}` (die picker, modeled banner, side-by-side).

**Effort:** M. **Depends on:** spec_11 (ComparePane), spec_12 (device_info),
spec_18 (provenance-label precedent); fleet profiles already landed.

## Implementation notes

Implemented 2026-08 against the post-spec_27 tree (415 backend tests → 470).
Where code reality differed from the text above:

- **The marker is a field, not a new event.** ``DeviceInfoEvent`` gains
  ``modeledFrom: str | None`` — it has to ride an ingestable event type so
  the "POSTing the remap marker → 422" test is expressible on the real wire.
  ``remap_events`` sets it on every (replaced or inserted) device_info; the
  fold turns it into ``placement="modeled"`` / ``recordedOn`` and carries
  both forward on every downstream frame. Rejection happens at the impure
  edge (``live_store._reject_modeled``) for ``ingest``, ``ingest/batch``,
  **and ``import``** — a remapped download can't be smuggled back in as a
  recording either.
- **Frame count is 1:1 with one documented exception.** A recording that
  never declared a ``device_info`` (the ``live_session.jsonl`` fixture is
  one) gains exactly one leading marked device frame — the fold must size
  the target die before the first remapped smid arrives, or every launch
  would violate the 24-SM default limit. ``test_conservation`` pins both
  cases.
- **Identity is an exact profile-name match** against the recording's
  device_info name. Real captures carry driver strings ("NVIDIA GeForce RTX
  4060 Laptop GPU", "NVIDIA H100 80GB HBM3") that never equal a profile
  name, so in practice the UI reaches the identity view by omitting
  ``asProfile`` ("View on: recorded device"); the short-circuit itself is
  pinned with a synthetic recording whose device is named ``H100-SXM``.
  A device-less recording's identity target is the spec_07 default profile.
- **Occupancy is kept, not recomputed.** Theoretical occupancy is per-SM
  residency (threads/blocks against the SM's own ceilings) and does not
  depend on how many SMs the die has, so the recorded theoretical value
  passes through verbatim. Measured occupancy (spec_15) is stripped on
  remap — ``occupancySource`` flips to ``theoretical`` and the percentage
  is nulled — per the honesty rule.
- **``test_api_surface_snapshot`` passes unmodified.** No route path was
  added or renamed; ``asProfile`` is a query param on the two existing
  trace routes exactly as designed. Unknown profile → 404, empty → 422.
- **UI scope.** The die picker lists every ``/api/profiles`` entry (the
  generic teaching dies are legitimate remap targets, not just the four
  fleet parts). Recorded-vs-remapped reuses the existing ComparePane —
  A = recorded, B = modeled, one cursor, per-pane SM counts for the Gantt
  strips (swap is a no-op for this pairing). The mandatory label renders in
  the die header inside ``LiveDieView`` — so ComparePane, LessonTour, and
  the SVG download all inherit it — plus a one-line caption under the die
  ("durations recorded on <device>; a bigger die changes queueing, not the
  work"). ``tests/test_remap.py`` greps the component for the label,
  spec_18 style.
