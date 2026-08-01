# spec_13 — `make watch` (save → see)

**Goal:** collapse the edit → run → see loop to save → see. A file-watcher
rebuilds and reruns a lesson on every save, so the die reacts to ⌘S.

## Design

- **`make watch-01`** (any lesson prefix): a small POSIX loop in the
  Makefile — prefer `inotifywait -e close_write` when present (package
  `inotify-tools`), fall back to a 1-second mtime poll (`stat -c %Y`) so
  nothing new is required. On change: `make run-NN`; compile errors print and
  the watcher keeps watching (a broken save must not kill the loop).
- Watch set: the lesson file + `twinprobe.cuh`.
- Debounce 300 ms (editors often write twice).
- **Session hygiene:** each watch run POSTs to the same live session, so the
  timeline accumulates one chip per save — that *is* the iteration history.
  Print a hint on start: name a session first if you want the recording kept
  (`curl -X POST localhost:8000/api/live/session -d '{"name":"..."}'` or the
  UI button).
- **VS Code (step two, optional):** `.vscode/tasks.json` with a
  `watch current lesson` task wrapping the same target — no extension, no
  new machinery.

## Invariants

- Watcher never exits on compile failure; Ctrl-C exits cleanly.
- No busy-loop: poll fallback sleeps ≥ 1 s.
- `make lint` still covers everything the watcher builds.

## Files

`cuda/Makefile` (watch-% target + helper script block),
`cuda/README.md` (loop section gains the watch variant),
`.vscode/tasks.json` (optional, step two).

**Effort:** S. **Depends on:** nothing. Highest convenience-per-line in the
whole list — do this one first.
