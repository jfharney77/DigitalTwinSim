# spec_08 — Live CUDA co-browsing (program on the left, die lights up in the browser)

**Goal:** while the user writes and runs CUDA programs in the terminal/editor,
the browser shows the RTX 4060 Laptop die (spec_07) with its real activity: which
SMs actually ran their blocks, how occupied the device was, kernel timings, VRAM,
power, and temperature. Sessions are recorded and replayable.

**Feasibility on this machine: confirmed.** The GPU is visible from WSL2
(`/usr/lib/wsl/lib/nvidia-smi`, driver 596.36, `libcuda.so` present). `nvcc` is
not yet installed — setup is step 0 of spec_09.

## 1. Reconciling "live" with the repo's core invariant

The engine invariant is *the trace is pure data; the clock lives in the
frontend*. Live mode does not touch the engine. The design:

- **The live path is an adapter, not an engine.** A new `live.py` module holds
  session state and converts incoming probe events into the same wire shapes the
  renderer already consumes (per-SM activity + counters). `engine.py` stays
  pure and untouched; the AST purity test still passes.
- **Every live session is recorded** as an append-only JSONL of events under
  `GPU/backend/sessions/<session-id>.jsonl`. A finished session can be replayed
  through the normal pure pipeline: `replay(session) -> LiveState[]` is a pure
  function with trace tests, exactly like `simulate()`. Live viewing is the
  only impure edge, and it is confined to the transport layer.
- **The frontend still owns its clock.** Live states arrive over SSE and are
  appended to a buffer; the UI renders the newest state (or scrubs back through
  the buffer — pause-the-live-feed comes free from this design).

## 2. Architecture

```
your terminal                        backend (:8000)                 browser (:5173)
─────────────                        ───────────────                 ───────────────
nvcc + twinprobe.cuh  ──POST──►  /api/live/ingest  ──►  live.py ──►  /api/live/stream (SSE)
  (per-block smid/timing)             session JSONL                    Live CUDA tab
twin-sampler (nvidia-smi loop) ──POST──►  (same ingest)                DieView per-SM tiles
                                                                       + counters + timeline
```

Three capture tiers, independent and composable:

- **Tier A — `twinprobe.cuh` (the centerpiece, zero external deps).** A small
  header the CUDA lessons include. Its trick: inside the kernel each block reads
  the **`%smid` special register** (inline PTX, `__twin_smid()`) plus
  `clock64()` on entry/exit of thread 0, writing one record per block to a
  device buffer. After the kernel, `TWIN_FLUSH()` copies records back and POSTs
  one JSON event: kernel name, grid/block dims, per-block `{smid, start, end}`,
  `cudaEvent` elapsed ms, and the occupancy numbers from
  `cudaOccupancyMaxActiveBlocksPerMultiprocessor`. **This is real placement
  data** — the die view lights the SMs the hardware scheduler actually chose,
  which is the whole point (and visibly non-deterministic run to run, an honest
  lesson in itself). Implementation: header-only, C++, POST via a tiny
  `popen("curl ...")` or a bundled `twin_post.c` helper — keep the header
  dependency-free for beginners.
- **Tier B — `twin-sampler` (background truth, no code changes).** A ~40-line
  Python loop polling `nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw,temperature.gpu
  --format=csv,noheader -l 1` (present and working in WSL2) and POSTing each
  sample. Drives the counters strip even for un-instrumented programs.
- **Tier C — CUPTI injection (optional, later).** Zero-code-change capture of
  every kernel via `CUDA_INJECTION64_PATH`. Requires enabling GPU performance
  counters in the Windows driver (NVIDIA Control Panel → Developer). Spec'd as
  a stretch; Tiers A+B deliver the experience without it.

## 3. Backend (`app/live.py` + routes in `main.py`)

- `POST /api/live/ingest` — accepts `ProbeEvent` (tagged union: `kernel_launch`
  with per-block records, or `gpu_sample` from the sampler). Appends to the
  active session JSONL; updates in-memory latest-state.
- `GET /api/live/stream` — SSE; emits `LiveState` on every ingest (coalesced to
  ≤20 Hz).
- `POST /api/live/session` / `DELETE` — start/stop a named session.
- `GET /api/live/sessions` / `GET /api/live/sessions/{id}/trace` — list, and
  replay a finished session as a pure `LiveState[]` (this endpoint calls the
  pure `replay()`).

`LiveState` (pydantic, camelCase like everything else):

```python
class SmActivity(CamelModel):
    sm_id: int
    blocks_run: int          # cumulative this kernel
    busy: bool               # any block resident in the last window

class LiveState(CamelModel):
    session_id: str
    t_ms: float                       # ms since session start (stamped at ingest)
    kernel: str | None                # active/last kernel name
    grid: tuple[int, int, int] | None
    block: tuple[int, int, int] | None
    sm_activity: list[SmActivity]     # length == profile SM count (24)
    occupancy_pct: float | None       # from the occupancy API
    elapsed_ms: float | None          # cudaEvent timing of last kernel
    util_pct: float | None            # Tier B
    vram_mb: float | None
    power_w: float | None
    temp_c: float | None
```

Invariant tests (`tests/test_live.py`): `replay()` is pure (AST-checked, same
harness as the engine); `t_ms` monotonic; every `sm_id` < profile SM count;
`blocks_run` totals equal the kernel's grid size once the kernel completes;
sm_activity length always 24 for the 4060 profile; a canned session fixture
(checked in) replays to a byte-stable trace.

## 4. Frontend — "Live CUDA" tab (third tab beside sim and anatomy)

- **Die view:** the spec_07 per-SM tile renderer, colored by `sm_activity`:
  cold → warm by `blocks_run`, pulse on `busy`. Deep-linkable `/#live`.
- **Counters strip:** occupancy %, util %, VRAM, power, temp, last-kernel time.
  All values real; label the source tier on hover (probe vs sampler).
- **Kernel timeline:** horizontal strip of kernel launches this session
  (name, grid×block, elapsed ms); clicking one shows its final per-SM block
  distribution — run-to-run scheduler variation becomes visible and discussable.
- **Session controls:** start/stop/name a session; picker to replay past
  sessions through the same components (replay uses the ordinary
  frontend-owned clock — live and replay share the renderer, which is the
  design's proof that the adapter stayed thin).
- **Connection state:** an honest badge — Live (SSE open) / Reconnecting /
  Replaying. No fake data ever; empty die + "waiting for events" when idle.
- Dell clean-design chrome; the die stays dark (it is the diagram).

## 5. The "co-browsing" loop (how it feels)

1. Terminal: `./scripts/start_all.sh`, browser on the Live CUDA tab.
2. Terminal: `twin-sampler &` — counters come alive with idle-desktop truth.
3. Terminal: edit `lessons/01_hello_thread.cu` (spec_09), `make run` — the
   POST fires on flush; the die lights the SMs your blocks landed on within a
   frame; the timeline grows one entry.
4. Change block size, rerun, watch placement and occupancy change. That loop —
   edit, run, see — is the product.

## 6. Scope guardrails

- Not a profiler: no per-instruction data, no memory-transaction tracing —
  Nsight exists; this is a *mental-model* instrument (same honesty rule as the
  sim: correct mental model over correct numbers).
- Per-block smid/clock sampling from thread 0 only; overhead is negligible for
  lesson-scale kernels and stated on the page.
- WSL2 note shown in the UI footer: sampler figures come from the Windows
  driver across the WSL boundary; sub-second spikes may be smoothed.
- Single-user, localhost only; no auth (matches the rest of the repo).

## 7. Build order

1. `live.py` + ingest/stream + JSONL sessions + `replay()` + tests.
2. Frontend Live tab with per-SM tiles fed by a canned replayed session
   (no CUDA needed — unblocks UI work immediately, and the fixture doubles as
   the test's byte-stable trace).
3. `twin-sampler` (Tier B) — first real data on screen.
4. `twinprobe.cuh` (Tier A) against spec_09's lesson 01.
5. Polish: timeline, session picker, connection badge.
