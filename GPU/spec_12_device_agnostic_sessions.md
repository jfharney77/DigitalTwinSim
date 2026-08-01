# spec_12 — device-agnostic sessions (any GPU, not just the 4060)

**Goal:** the live wire format hardcodes `SM_COUNT = 24`, so every GPU that
isn't this laptop is rejected at ingest. Make device geometry session data:
the probe reports its device, the backend sizes everything from that, the
frontend draws the right grid.

## Design

- **New event** `device_info` (third member of the `ProbeEvent` union):
  `{type, name, smCount (ge=1, le=1024), maxThreadsPerSm, warpSize, vramMb}`
  — the `cudaGetDeviceProperties` subset lesson 00 already prints. Emitted
  once by `TwinProbe`'s constructor (guarded static flag) and by
  `twin-sampler` on startup (from `nvidia-smi --query-gpu=name,...`).
- **Pure layer.** `fold` carries `device: DeviceInfo | None` in `LiveState`;
  `sm_activity` length becomes `device.smCount` (default to the spec_07
  profile's 24 when no device_info has arrived — existing behavior, existing
  fixtures unchanged). The smid range check moves from class-level
  (`lt=SM_COUNT`) to fold-time validation against the session's device:
  a smid ≥ smCount raises `ValueError` → ingest 422.
- **Frontend.** `LiveDieView` derives rows/cols from `smCount` (nearest
  rows×cols grid, cols = ceil(sqrt(n * 1.5))) instead of the profile prop;
  header shows `device.name`. The RTX-4060 profile remains only the default
  before any device reports.
- **Session files** gain the device_info event as their natural first line —
  replay reconstructs geometry with zero extra state.

## Invariants (extend `tests/test_live.py` / `test_live_edges.py`)

- A 24-SM fixture with no device_info replays exactly as before (backward
  compatibility is a test, not a hope).
- After `device_info(smCount=48)`: activity length 48; smid 47 accepted,
  48 rejected.
- device_info mid-session with a *different* smCount is rejected (a device
  cannot change under a running recording).

## Files

`backend/app/live.py`, `tests/`, `cuda/twinprobe.cuh` (one-time emit),
`cuda/twin-sampler`, `frontend/src/{types.ts,components/LivePage.tsx}`.

**Effort:** M–L (wire change touches every layer). **Unblocks:** using the
whole co-browse on any machine — do this before sharing the tool.
