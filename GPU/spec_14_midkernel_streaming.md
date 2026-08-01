# spec_14 — mid-kernel streaming (watch the wave, not the report)

**Goal:** today the die updates when a kernel *finishes*. For long kernels
(seconds+), stream partial block records while it runs, so the grid visibly
washes across the die in real time.

## Design

- **Probe.** Records move from `cudaMalloc` to **pinned, mapped host memory**
  (`cudaHostAlloc` with `cudaHostAllocMapped`): device writes land in host-
  visible memory while the kernel runs. `TwinProbe` gains
  `startStreaming(intervalMs = 200)`: a host thread (std::thread) polls the
  buffer, diffs against what it already sent, and POSTs incremental
  `kernel_progress` events `{kernel, blocksSeen: [{smid, started, ended}…]}`
  (counts, not full spans — cheap). `flush()` stops the thread and sends the
  final authoritative `kernel_launch` event exactly as today.
- **Volatile reads, torn-write tolerance:** the poller may read a record
  mid-write; treat `end==0` as "running", ignore garbage smid (>1023), and
  never block the kernel — the poller only reads.
- **Backend.** `kernel_progress` joins the `ProbeEvent` union; fold marks the
  named SMs `busy` and accumulates `blocks_run` monotonically; the closing
  `kernel_launch` **replaces** the accumulated picture (authoritative). New
  invariant: after the final event, the state equals what a non-streaming
  session would show — streaming is presentation, not data.
- **Frontend:** nothing new — busy rings and counts already animate per
  frame. The wave appears for free.
- **Honesty:** progress frames carry `partial: true`; the UI shows "running…"
  instead of elapsed ms until the final event.

## Invariants (tests, fixture-driven — no GPU in CI)

- Fold: progress → progress → launch converges to the launch-only result
  (property test against the same records split at random points).
- `blocks_run` monotonic across progress frames; busy false after final.
- Replay byte-stable with progress events interleaved.

## Files

`cuda/twinprobe.cuh` (mapped buffer, poller thread, `kernel_progress`),
`backend/app/live.py` (+event, fold rules), `tests/test_live.py` (+fixture
with progress events), `frontend/src/types.ts` (partial flag).

**Effort:** L (the probe's threading + tearing rules need care).
**Depends on:** spec_12 recommended first (wire-format churn once, not twice).
