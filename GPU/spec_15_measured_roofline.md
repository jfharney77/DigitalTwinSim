# spec_15 — measured roofline (the sim calibrated by your hardware)

**Goal:** lesson 06 measures the die's real streaming bandwidth; the
simulator's roofline read-out runs on illustrative numbers. Connect them:
"model ~256 GB/s · your die measured 241 GB/s" — the twin calibrated by its
physical counterpart.

## Design

- **Probe → backend.** Lesson 06 already computes achieved GB/s; add a
  `measurement` event to the `ProbeEvent` union:
  `{type: "measurement", metric: "stream_gbps", value, kernel}`. Lesson 06
  emits it next to its printf (one extra `twin_post` call — expose
  `twin_post_json(const char*)` from the header for host-side events).
- **Persistence.** `live_store` keeps the latest measurement per metric in a
  tiny `backend/sessions/measurements.json` (not per-session — a calibration
  outlives its run). New route `GET /api/measurements`.
- **Sim tab.** The `Summary`/roofline card fetches measurements and, when
  `stream_gbps` exists, renders a second annotation line and (if a roofline
  chart exists by then) a dashed "measured" roof under the modeled one.
  Copy states the honest relationship: the model's units are illustrative;
  the measured line is real; the *ratio* between them is the calibration.
- **Staleness:** measurement carries an ISO date (stamped at the transport
  edge, like `t_ms`); the UI shows "measured <date>".

## Invariants

- Pure fold untouched by measurements except pass-through (they are not
  frames; they do not enter `LiveState`) — keeps spec_08's model clean.
- `GET /api/measurements` returns `{}` before any run; sim card renders
  identically to today when empty (no fake calibration).
- Ingest validation: known metric names only, value > 0, finite.

## Files

`backend/app/live.py` (event type only), `live_store.py` (measurement store),
`main.py` (route), `cuda/lessons/06_bandwidth.cu` (+emit),
`cuda/twinprobe.cuh` (expose the POST helper),
`frontend/src/{api.ts,components/Counters.tsx}`.

**Effort:** M. **Depends on:** nothing. The single best bridge between the
Live tab and the original simulator.
