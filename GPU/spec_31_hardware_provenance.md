# spec_31 — hardware provenance (the first-hardware-run protocol)

**Goal:** retire the repo's oldest honest caveat — "`nvcc` has never run on
this machine" — with a repeatable campaign, not a lucky afternoon. The output
is not a feeling that it worked: it is every tour step whose recording *can*
be captured here flipped from `provenance="representative"` to
`provenance="hardware"`, a calibration in `measurements.json`, a
`make verify-hardware` target that re-proves it, and the CLAUDE.md caveat
rewritten to its post-hardware truth. Provenance is a fact, not a grade:
nothing is ever faked upward, and nothing representative is treated as a
defect.

## Phase 0 — toolchain gate

- Install the toolkit per `cuda/README.md` (WSL2: toolkit only, never a
  Linux driver — `libcuda` comes from the Windows driver via
  `/usr/lib/wsl/lib`). `nvcc --version` is the entry ticket.
- **First checkpoint is `make lint`**, not `make run-00`: it compile-checks
  all eight lessons against `twinprobe.cuh` with no GPU in the loop, so a
  header bug surfaces before any capture is attempted.
- **Compile-fix budget:** fixes to `twinprobe.cuh`, lessons, or
  `twininject/` are expected (this code has never met a compiler) and are
  in-scope — but the probe-sample fixtures in
  `backend/tests/fixtures/probe_samples/` are the wire contract, and
  `test_live.py::test_probe_samples_ingest` must stay green through every
  fix. If a compile fix genuinely must change the wire shape, the fixtures
  change **in the same commit**, deliberately, with the commit message
  saying so. A fixture edited to make a broken header pass is the one move
  this spec exists to forbid.

## Phase 1 — the capture ladder (lessons 00 → 07)

Run in order; each rung gates the next. For every lesson:

1. Name a session (Live tab or `POST /api/live/sessions`) — hardware
   captures land in a *kept, named* recording, never the anonymous scratch
   session.
2. `make run-NN` with `twin-sampler` running; verify the Live tab lights
   (die tiles for 01–07; lesson 00 emits `device_info` only and verifies
   the twin's 24-SM numbers — it has no tour step and nothing to promote).
3. **Promote:** download the session JSONL
   (`GET /api/live/sessions/<id>/download`), replace the representative
   golden recording at `backend/tours/lessons/<lesson_id>.jsonl`, flip that
   tour step's `provenance` to `"hardware"` in `tour.py`, and re-pin
   `cursor` if the frame count changed.
4. Edit the step's `script` **only where it states machine-specific
   numbers** (elapsed ms, GB/s, block counts that fell out of a
   representative run). The teaching prose is about CUDA, not this laptop;
   it survives promotion untouched.

**Promotion rules (each one testable):**

- A hardware recording was captured on the machine it claims — its
  `device_info` frame must carry the real driver-reported name
  (`RTX 4060 Laptop GPU`-class), never a generic placeholder, and its SM
  count must match any SM count the step's narration states (24 here).
- Cursor frames are still kernel frames —
  `test_tour.py::test_cursor_frames_are_kernel_frames` already pins this;
  a promotion that breaks it is reverted, not excused.
- Recordings still open with a `device` frame and replay through the pure
  pipeline (`test_recordings_replay_in_ci`). No hand-editing of JSONL:
  if a capture is bad, capture again.

## Phase 2 — what can NEVER be hardware here

The `07_bigger_dies` (H100) and `07_bigger_dies_blackwell` (B300) steps stay
`representative` **forever on this machine** — it is a 4060, and a recording
claiming 132 or 160 SMs from it would be a lie with a label on it. The
whole point of the provenance field is that both labels are true statements:
a representative recording is not a defect, and the campaign's success is
measured by honesty, not by the count of `"hardware"` strings.

## Phase 3 — calibration refresh

- Lesson 06 posts measured `stream_gbps` → `measurements.json` (spec_15);
  confirm the Simulator tab's roofline card shows "your die, measured".
- Optional: build `twininject/` (`make -C twininject`), run `twin-run` on
  one lesson, confirm timing-only cupti chips with their source label
  (spec_17). Windows perf-counter permission is the known blocker; its
  failure mode must print the documented fix, not crash.
- If spec_25 (power model) has landed, capture its watts hook in the same
  sitting — one hardware day should refresh every calibration the sim
  consumes.

## Phase 4 — CI and docs afterlife

- New target `make verify-hardware`: `lint` + build + `run-all` against a
  live backend, then a small script asserting each lesson 01–07 produced
  ≥1 kernel frame in its session (lesson 00: a `device_info` event). This
  is the rerunnable form of the campaign — driver updates get a one-command
  re-verify.
- Rewrite the CLAUDE.md "honest caveat that outlives this note" to its
  post-hardware truth (date of first verified run, what was promoted, what
  stays representative and why); add the README changelog row.

## Phase 5 — failure playbook

- `nvcc` found but binaries fail at init → `libcuda` path: WSL2 loads it
  from `/usr/lib/wsl/lib`; never install a Linux driver to "fix" this.
- `twin-sampler` silent → it shells the WSL path
  `/usr/lib/wsl/lib/nvidia-smi`; a PATH-only nvidia-smi is not enough.
- Lesson compiles and runs but no events arrive → the probe degrades to
  stderr when offline by design: check the JSON is on stderr (probe fine,
  backend unreachable — check `TWIN_URL`/`:8000`) vs absent (probe broken —
  fix the header, keep the fixtures green per Phase 0).
- Arch mismatch on non-Ada hardware: `make ARCH=-arch=sm_XX`.

## Test plan

- Gates already standing: `test_probe_samples_ingest` (Phase 0, the wire),
  `test_every_step_resolves_and_cursor_is_valid` + 
  `test_cursor_frames_are_kernel_frames` + `test_recordings_replay_in_ci`
  (Phase 1, every promotion), `test_streaming_converges_to_launch_only_result`
  (lesson 06's streaming capture).
- **New test (this spec's one code deliverable besides the Make target):**
  for every tour step with `provenance="hardware"`, load its recording and
  assert the `device_info` name is non-generic (not empty, not the
  simulator's default profile label) — a hardware claim must carry a real
  device's signature. Vacuously green today; load-bearing the day the
  first step flips.

**Effort:** S in code (one test, one Make target, doc edits) wrapped around
one hardware day. **Depends on:** a CUDA toolkit install (step 0 of
`cuda/README.md`); spec_15/17 paths exercised, spec_25 optional.

## Implementation notes (2026-08-16 — software artifacts only)

Built ahead of any hardware day, per the scope boundary: `nvcc` has still
never run on this machine, so nothing was compiled, no capture was made, and
every provenance stays `"representative"`. What exists now:

- **`make verify-hardware`** (`cuda/Makefile`): `lint` + build all +
  `verify_hardware.py --preflight` (backend health check + opens a named
  `verify-hardware` session, so run-all lands in a kept recording, not the
  adhoc scratch session — a small addition to the Phase 4 text, in the
  spirit of Phase 1 rule 1) + `run-all` + the checker.
- **`cuda/verify_hardware.py`** (stdlib only): per-lesson PASS/FAIL against
  the active/newest session's `/api/live/sessions/<id>/summary`; exit 1 on
  any FAIL, exit 2 with an actionable message when the backend is down.
  Deviation worth naming: lessons 02 and 07 both flush a kernel named
  `vector_add`, so a single run-all session cannot tell them apart by name —
  the checker requires ≥2 `vector_add` runs to pass the pair, and says so.
  Lesson 03 matches by `vector_add_bs` prefix (the sweep). Advisory (non-
  gating) lines report a generic-looking device name and the presence or
  absence of the `stream_gbps` calibration (Phase 3).
- **`cuda/promote_recording.py`** (stdlib only; dry-run by default,
  `--write` to install): downloads a session (or takes `--file`) and
  replaces the golden at `backend/tours/lessons/<lesson>.jsonl` only when
  the promotion rules hold — opens with `device_info`, name non-generic
  (markers + live `/api/profiles` labels), ≥1 kernel launch covering the
  lesson, and **SM count equal to the golden it replaces**, which makes the
  Phase 2 "07 stays representative forever here" refusal automatic and
  data-driven rather than hardcoded. It never edits `tour.py`: the
  provenance flip and cursor re-pin are printed as the operator's checklist.
- **The new test**: `test_tour.py::test_hardware_steps_carry_a_real_device_signature`,
  backed by a pure `device_name_is_generic()` predicate added to
  `app/tour.py` (markers only, keeping tour.py's import allowlist intact;
  the profile-label half lives at the test/tool edge where importing
  `profiles` is allowed). Vacuously green today over the hardware loop —
  and deliberately not only vacuous: it exercises the predicate itself on
  fixed examples so it does work before the first flip. Backend suite:
  489 → 490 tests, all green.
- **Docs**: `cuda/README.md` gained the "First hardware run — the spec_31
  campaign protocol" section (Phase 0–4 checklist, promotion rules, the
  forever-representative list, Phase 5 failure playbook); the CLAUDE.md
  caveat now points at this spec and `make verify-hardware` while remaining
  true.

Still owed to a real hardware day (cannot be automated from here): the
captures themselves, every provenance flip, the `measurements.json` refresh,
the CLAUDE.md caveat rewrite to its post-hardware truth, and the README
changelog row for the campaign.
