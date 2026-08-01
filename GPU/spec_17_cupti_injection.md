# spec_17 — Tier C: CUPTI injection (zero-code-change capture)

**Goal:** capture *any* CUDA program — PyTorch, a random GitHub repo, no
macros, no recompile — via CUPTI's injection hook, and replace the
theoretical occupancy figure with measured achieved occupancy.

## Design

- **`cuda/twininject/`**: a small shared library (`libtwininject.so`, own
  Makefile — this one links `libcupti`, unlike the header) loaded by the
  CUDA runtime via `CUDA_INJECTION64_PATH=/path/to/libtwininject.so ./app`.
  Provide a wrapper script `twin-run <command…>` that sets the env var and
  execs.
- **What it subscribes to (activity API, buffered):**
  - `CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL` → kernel name (demangled),
    grid/block, start/end ns, per-kernel `kernel_launch` events posted on
    buffer flush. **No smid per block at this tier** — the activity record
    carries timing, not placement; `blocks` stays empty and the event adds
    `"source": "cupti"` so the UI can say "timing only" instead of drawing
    an empty die as if nothing ran. (Placement still needs Tier A or PC
    sampling, out of scope here.)
  - Achieved occupancy via the profiling API where the driver permits →
    `occupancyPct` becomes measured; add `"occupancySource":
    "measured"|"theoretical"` to the event so the counters can label it.
- **Windows/WSL2 prerequisite** (documented in the README section this spec
  adds): NVIDIA Control Panel → Developer → *Allow access to GPU performance
  counters to all users*, or CUPTI returns `CUPTI_ERROR_INSUFFICIENT_
  PRIVILEGES` — the library must detect that exact case and print the fix,
  then degrade to activity-only (timing still works without perf counters).
- **Backend:** accepts the new optional fields; fold treats an empty-blocks
  cupti event as `kind="kernel"` with untouched `sm_activity` (busy=false) —
  timeline chips appear, die stays honest.

## Invariants

- Backend fixtures for cupti-shaped events: timeline entry without die
  lighting; occupancy source label round-trips.
- The injection library never crashes the host app: every CUPTI call
  wrapped, failure → one stderr line and inert behavior.
- `twin-run` on a non-CUDA binary is a no-op passthrough.

## Files

`cuda/twininject/{twininject.cc,Makefile}`, `cuda/twin-run`,
`backend/app/live.py` (optional fields), `tests/test_live.py` (+fixtures),
`cuda/README.md` (Tier C section), `frontend` (source labels).

**Effort:** L (new native component + driver-permission UX).
**Depends on:** spec_12 strongly recommended first (arbitrary apps run on
arbitrary GPUs). This is the step that turns the teaching tool into a
general-purpose visualizer.
