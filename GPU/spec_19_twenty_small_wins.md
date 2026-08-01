# spec_19 — twenty small wins (co-browse polish batch)

Twenty deliberately S-sized improvements, spec'd together because each is a
few edits; the invariant bar stays the usual one (tests where behavior
changes, honesty rules everywhere). Grouped by layer.

## Backend / API

1. **`GET /api/live/latest`** — the current frame without SSE, for scripts
   and quick checks (`curl | jq .kernel`). 404 when no session has produced
   a frame.
2. **`DELETE /api/live/sessions/{id}`** — recordings are user data; let the
   user delete them. Refuses the active session (409).
3. **`GET /api/live/sessions/{id}/download`** — raw JSONL as an attachment;
   a recording you can keep, share, or re-ingest is worth more than one
   locked in the UI.
4. **Session list `?limit=N`** — newest first, default 50: kernel-heavy days
   should not make the list unbounded.
5. **Richer `/api/health`** — adds app version, session count, active
   session id; the first thing a debugging user curls should answer more.
6. **Elapsed-ms sanity cap** — `elapsedMs` over one hour is a corrupt event,
   not a kernel; reject at validation (le=3.6e6).
7. **Tour-recording completeness test** — every golden recording's kernel
   frame must account for its whole grid (sum(blocksRun) == grid product);
   pins the fixtures to the same honesty as live ingest.

## Frontend — Live tab

8. **Delete buttons on recordings** (uses #2), with the active session's
   delete disabled.
9. **Download link on recordings** (uses #3).
10. **Newest-first session list** — matches #4's ordering; the recording you
    just made is the one you want.
11. **Remembered session name** — localStorage; naming a session "sweep-"
    every day is friction.
12. **Keyboard shortcuts in replay** — space pauses/resumes the replay
    clock, arrow keys step the cursor; scrubbing by mouse only is clumsy.
13. **Skipped-frames badge resets on click** — the count is a notification,
    not a permanent stain; click acknowledges it.
14. **Timeline chip cap** — render the latest 50 chips with a "show all (N)"
    expander; a 1,000-launch session must not render 1,000 buttons.
15. **Kernel-time sparkline** — a tiny inline SVG of recent kernel elapsed
    times next to the timeline header; trend at a glance, which is what the
    watch loop (spec_13) produces.
16. **Low-occupancy tint** — the occupancy counter turns amber under 50%;
    the number the curriculum teaches most deserves the one splash of color.
17. **Quick-start box in the empty state** — the exact three commands
    (start_all, twin-sampler, make run-01), copy-pasteable, where today
    there is only prose.
18. **"Download die SVG"** — serialize the current die view to a standalone
    .svg; the community research found real demand for stencil exports.

## Tooling / docs

19. **`twin-sampler --once`** and **`make run-all`** — one sample then exit
    (scriptable), and the whole curriculum as a demo reel.
20. **Ops affordances** — `scripts/prune_sessions.sh` (delete ad-hoc
    recordings, keep named ones) and a Live CUDA section in `GPU/README.md`
    (the root README predates the third tab).
