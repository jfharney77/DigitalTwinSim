# spec_10 — per-SM Gantt timeline (block residency over time)

**Goal:** render the data the probe already records and the UI throws away:
per-block `{smid, start, end}` clock64 stamps. A Gantt strip — one lane per
SM, one bar per block — makes load imbalance and the straggler tail visible,
which the heat tiles structurally cannot show.

## Design

- **Backend.** `LiveState` currently discards block records after counting
  them. Add `block_spans: list[BlockSpan] | None` (kernel frames only):
  `{smId, startNorm, endNorm}` with clock64 values normalized to [0, 1] over
  the kernel's span in the pure fold (`live.py`) — raw clock64 stays out of
  the wire format (device-relative, huge, meaningless downstream). Cap spans
  at 2,048 per frame, order-preserving sample beyond that, and set the
  existing `records_dropped`-style honesty flag `spans_sampled: bool`.
- **Frontend.** New `GanttStrip.tsx` under the die view on the Live tab,
  rendered for the shown kernel frame: 24 lanes, bars at
  `x = startNorm * width`. Hover a bar → block index, SM, normalized span.
  The straggler block (latest `endNorm`) gets a labeled marker — the tail is
  the lesson.
- **Replay** works unchanged — spans ride in the recorded frames.

## Invariants (extend `tests/test_live.py`)

- Fold is still pure; spans present iff `kind == "kernel"`.
- `0 <= startNorm <= endNorm <= 1` for every span; span count ≤ 2,048;
  `spansSampled` true iff records exceeded the cap.
- Fixture sessions replay byte-stable with spans included.

## Files

`backend/app/live.py` (+BlockSpan, fold), `tests/test_live.py`,
`frontend/src/types.ts`, `frontend/src/components/GanttStrip.tsx`,
`LivePage.tsx` (mount). Probe unchanged — the data already flows.

**Effort:** M. **Depends on:** nothing. **Best paired with:** spec_11 (the
diff view reuses the strip).
