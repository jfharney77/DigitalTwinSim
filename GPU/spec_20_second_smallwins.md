# spec_20 — twenty more small wins (co-browse polish, round two)

Twenty S-sized improvements, disjoint from spec_19's. Grouped by layer.

## Backend / API

1. **Pure `summarize()`** — `SessionSummary` (frames, device, duration,
   per-kernel run count + best/worst ms) computed in `live.py` from a
   replayed trace; the fold's counterpart for whole-session questions.
2. **`GET /api/live/sessions/{id}/summary`** — #1 over HTTP; feeds the UI's
   recording detail.
3. **`POST /api/live/import`** — upload a downloaded JSONL (name + text),
   validated by full replay before a file is written; closes the loop that
   spec_19's download opened. Invalid recordings are rejected whole.
4. **`GET /api/live/sessions/{id}/events.csv`** — kernel frames as CSV
   (kernel, tMs, elapsedMs, occupancyPct, source) for spreadsheets.
5. **`PATCH /api/live/sessions/{id}`** — rename a recording (new slug, file
   renamed); refuses the active session.
6. **Session event cap** — 100,000 events per recording; ingest past it is
   409 "recording full", not an unbounded disk write.
7. **Measurement history** — the store keeps the last 20 values per metric
   alongside the latest; calibration drift becomes visible data.

## Frontend — Live tab

8. **Recording summary on demand** — an "ⓘ" per recording fetches #2 and
   shows "12 kernels · fastest 0.31 ms · RTX 4060".
9. **Import button** — file picker feeding #3.
10. **CSV link** per recording (#4).
11. **"SMs busy" counter** — busy/total in the counters strip; the single
    number that says how full the die is right now.
12. **Replay speed control** — 0.5×/1×/2×/4× on the replay clock.
13. **"Live moved on" hint** — while pinned, new kernel arrivals show
    "live moved on (N new) →" instead of silently accumulating.
14. **Tour deep link** — `#live/tour` opens the guided lessons directly;
    shareable, bookmarkable.
15. **Gantt idle-lane toggle** — hide SM lanes with no blocks (default on
    for sparse kernels); a 1-block kernel shouldn't render 23 empty lanes.
16. **Occupancy InfoDot** — the two-budget explanation (threads AND blocks
    per SM) on hover, where the number lives.
17. **Compare swap (A↔B)** — one click instead of re-pinning both.
18. **Chip delta vs previous same-kernel run** — "▼0.12ms" on each chip;
    the save→see loop's feedback, quantified.

## Tooling / docs

19. **`scripts/demo_feed.py`** — replays a golden lesson recording through
    real ingest at watchable speed: the full live UI demo with no GPU and
    no CUDA toolkit.
20. **Docs refresh** — the new endpoints and the replay keyboard shortcuts
    land in `GPU/README.md`'s API section.
