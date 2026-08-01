# spec_21 — twenty more small wins (round three: beyond the Live tab)

Twenty S-sized improvements. Rounds one and two polished the Live tab; this
round spreads across the simulator, the anatomy page, robustness, and
accessibility, so the whole app benefits.

## Simulator tab

1. **Keyboard shortcuts** — space runs/pauses, → steps, R resets; parity
   with the replay controls the Live tab already has.
2. **Settings persist** — N, workload, tile size, dtype, double-buffer,
   speed survive a reload (localStorage); re-dialing the same experiment
   every session is friction.
3. **Die SVG export** — the Live tab's "Download die SVG" helper becomes a
   shared util and the simulator gets the same button.
4. **Loss sparkline** — the MLP per-step losses render as a tiny trend line
   next to the text values; "is it learning" at a glance.
5. **Legend completes and explains** — the stall color (waiting on HBM) was
   missing from the legend; add it, plus hover tooltips for every swatch.

## Anatomy tab

6. **Region deep links** — `#anatomy/<die>/<region>` pins a region on load;
   the existing die-level deep link goes one level deeper.
7. **Region search** — a filter box listing regions whose label or
   description matches; click selects. Six dies × dozens of regions now
   navigable by text.

## Robustness / accessibility (frontend)

8. **Error boundary** — a crash in one tab's rendering shows a contained
   error card instead of blanking the whole app.
9. **Backend-down banner** — the Live tab distinguishes "backend
   unreachable (start it with …)" from the generic reconnecting badge, via
   a health probe on mount.
10. **Page titles** — `document.title` follows the tab; three identical
    "GPU Die" tabs in a browser are unfindable.
11. **ARIA pass on the Live tab** — the connection badge becomes a
    `role="status"` live region; timeline chips get descriptive
    `aria-label`s.

## Backend / API

12. **`GET /api/live/config`** — the caps (max session events, max smid,
    span cap, default SM count) as data, so tools and UI stop hardcoding
    what the backend already knows.
13. **Trace pagination** — `?from=&limit=` on the trace endpoint plus a
    `total` field; a 100k-event recording shouldn't require a 100k-frame
    response.
14. **Batched ingest** — `POST /api/live/ingest/batch` (list of events, one
    request); lesson 03's six launches or a sweep script stop paying six
    round-trips.
15. **Health reports tours** — `toursAvailable` count in `/api/health`; a
    missing golden-recordings directory becomes visible before a user
    clicks the tour button.
16. **Sessions dir ignores itself** — a `.gitignore` written into
    `backend/sessions/` on creation; recordings are user data and must
    never land in version control if this repo is ever git-initialized.
17. **API-surface snapshot test** — one test asserting the exact route set;
    an accidental rename or lost route fails CI by name.

## Capture tools

18. **Probe politeness** — `TWIN_QUIET=1` silences offline stderr (watch
    mode with the backend down currently spams); trailing-slash-tolerant
    `TWIN_URL`.
19. **Sampler backoff** — exponential (up to 30 s) while the backend is
    away, reset on success; a background sampler shouldn't hammer a dead
    port every second.
20. **`demo_feed.py --all` + changelog** — the whole curriculum as a
    GPU-free demo reel, and a spec_07–21 changelog table in
    `GPU/README.md` so the co-browse's history is one screen.
