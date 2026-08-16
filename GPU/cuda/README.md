# CUDA lessons — program the GPU, watch the die light up

A progressive curriculum for a CUDA beginner (spec_09), instrumented so every
run shows up on the **Live CUDA** tab of the visualizer as real SM placement,
timing, and occupancy. Each lesson is one commented `.cu` file with a "what
you'll see" block and one experiment.

## One-time setup (WSL2)

The GPU and `libcuda` are already visible in WSL2 through the Windows driver;
only the toolkit is missing. **Install the toolkit only — never a Linux
driver inside WSL** (the Windows driver provides `libcuda` via
`/usr/lib/wsl/lib`):

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update && sudo apt-get install -y cuda-toolkit
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc && source ~/.bashrc
nvcc --version    # sanity check
```

## The loop (how co-browsing feels)

```bash
../scripts/start_all.sh          # backend :8000 + frontend :5173
# browser -> http://localhost:5173/#live
./twin-sampler &                 # counters come alive (util/VRAM/power/temp)
make run-00                      # verify toolchain + hardware vs the twin
make run-01                      # first die lighting
```

Edit a lesson, `make run-NN` again, watch the die change. That loop is the
product. `make watch-NN` (spec_13) collapses it further: the lesson rebuilds
and reruns on every save (inotifywait if installed, 1 s poll otherwise), so
the die reacts to ⌘S. A VS Code task ("watch current lesson") wraps the same
target. The probe needs no backend to work — offline it prints its JSON to
stderr and the lesson still runs as a plain CUDA program.

## Lessons

| # | file | the one idea | on the die |
|---|---|---|---|
| 00 | `00_device_query.cu` | ask the driver what the device is | nothing — verifies the twin's numbers (24 SMs) |
| 01 | `01_hello_thread.cu` | threads exist; blocks land on SMs | one block → exactly one tile lights; rerun → a different one |
| 02 | `02_vector_add.cu` | the grid washes across the die | all 24 SMs, ~170 blocks each; small N leaves tiles dark |
| 03 | `03_block_size.cu` | occupancy is a budget | six timeline entries; occupancy falls at the extremes |
| 04 | `04_matmul_naive.cu` | the simulator's matmul, uncached | looks like 02; note the elapsed ms |
| 05 | `05_matmul_tiled.cu` | shared-memory tiling (spec_03), real | same placement, several times faster — memory, not cores |
| 06 | `06_bandwidth.cu` | find the memory roof | GB/s plateaus near ~256; power climbs toward TGP |
| 07 | `07_bigger_dies.cu` | the die is a parameter | grid sized from the SM count — 48 blocks here, 264 on an H100, 320 on a B300 (guided-tour recordings show both) |

Vocabulary on first use: a **kernel** is a function launched over a **grid**
of **thread blocks**; each block runs entirely on one **SM** (streaming
multiprocessor), which executes its threads in 32-wide **warps**.
**Occupancy** is the share of an SM's thread slots kept busy; a
**grid-stride loop** lets a fixed grid walk an array of any size.

Going deeper: the [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
(programming model chapter first), and the Simulator tab's specs
(`../spec_02` tiling, `../spec_04` bandwidth/roofline) for the mental model
these lessons make physical.

## Beyond the lessons

- **Any CUDA program, zero code changes (spec_17):** build the CUPTI injector
  once (`make -C twininject`, needs the toolkit) and run
  `./twin-run python train.py` — kernels appear as timing-only chips
  (`source: cupti`; no placement data, and the UI says so). If Windows
  restricts perf counters: NVIDIA Control Panel → Developer → allow access
  to GPU performance counters.
- **Long kernels stream (spec_14):** `probe.startStreaming()` posts per-SM
  counts while the kernel runs (records live in pinned mapped memory) — the
  die fills as a visible wave; the closing flush is always authoritative.
  Lesson 06 demonstrates it.
- **Huge grids sample (spec_16):** above `TWIN_MAX_RECORDS` (8,192, env-
  overridable) the probe keeps the first 1,024 blocks plus a deterministic
  stride and declares it (`sampled: true`); the UI shows `~` estimates.
- **Your die calibrates the simulator (spec_15):** lesson 06 posts its
  measured GB/s; the Simulator tab's roofline card shows
  "your die, measured" beside the model.
- **No GPU handy? (spec_18):** the Live tab's "▶ Guided lessons" plays each
  lesson's recording with narration — provenance labeled — ending where you
  start: `make run-01`.
- Note: `twin-sampler` cannot emit `device_info` (nvidia-smi does not expose
  SM counts) — the probe and the injector do that; sampler-only sessions use
  the default 24-SM die.

## How the instrumentation works (`twinprobe.cuh`)

Thread 0 of every block records the SM id it landed on (the `%smid` hardware
register — real placement, different run to run) plus `clock64()` at entry
and exit. After the launch, `probe.flush(name, kernel)` copies the records
back, adds cudaEvent elapsed ms and the occupancy-API figure, and POSTs one
JSON event to `TWIN_URL` (default `http://localhost:8000`). Overhead is one
register read and two global writes per block — negligible at lesson scale,
and stated here because honesty is a repo rule.

## First hardware run — the spec_31 campaign protocol

`nvcc` has never run on this machine, so the first hardware day follows
`../spec_31_hardware_provenance.md` — a repeatable campaign, not a lucky
afternoon. Provenance is a fact, not a grade: nothing is faked upward, and
nothing representative is treated as a defect.

**Phase 0 — toolchain gate.**

- Install the toolkit per "One-time setup" above. WSL2 rule: **toolkit only,
  never a Linux driver** — `libcuda` comes from the Windows driver via
  `/usr/lib/wsl/lib`. `nvcc --version` is the entry ticket.
- First checkpoint is `make lint`, not `make run-00`: it compile-checks all
  eight lessons against `twinprobe.cuh` with no GPU in the loop, so a header
  bug surfaces before any capture is attempted.
- Compile fixes to `twinprobe.cuh`, the lessons, or `twininject/` are
  expected and in scope — but the probe-sample fixtures in
  `../backend/tests/fixtures/probe_samples/` are the wire contract, and
  `test_live.py::test_probe_samples_ingest` must stay green through every
  fix. A wire-shape change edits the fixtures **in the same commit**,
  deliberately, with the commit message saying so. Editing a fixture to make
  a broken header pass is the one forbidden move.

**Phase 1 — the capture ladder (lessons 00 → 07, in order; each rung gates
the next).** For every lesson:

1. Name a session (Live tab, or `POST /api/live/sessions`) — hardware
   captures land in a kept, named recording, never the anonymous scratch
   session.
2. `make run-NN` with `./twin-sampler` running; verify the Live tab lights
   (die tiles for 01–07; lesson 00 emits `device_info` only, verifying the
   twin's 24-SM numbers — it has no tour step and nothing to promote).
3. Promote with the helper — it enforces the rules below and is dry-run by
   default:

   ```bash
   python3 promote_recording.py <session_id> <lesson_id>          # check
   python3 promote_recording.py <session_id> <lesson_id> --write  # install
   ```

   Then, by hand: flip that step's `provenance` to `"hardware"` in
   `../backend/app/tour.py`, and re-pin `cursor` if the frame count changed.
4. Edit the step's `script` **only where it states machine-specific numbers**
   (elapsed ms, GB/s, block counts that fell out of a representative run).
   The teaching prose is about CUDA, not this laptop; it survives promotion
   untouched.

**Promotion rules (each one testable, and the helper refuses without them):**

- The `device_info` frame must carry the real driver-reported name
  (`RTX 4060 Laptop GPU`-class) — never empty, a placeholder, or a
  simulator profile label (`test_tour.py::
  test_hardware_steps_carry_a_real_device_signature`).
- Its SM count must match the golden it replaces (which is what any SM count
  in the step's narration states — 24 here).
- Its kernel frames must cover the lesson (≥1 launch of the lesson's kernel).
- Cursor frames are still kernel frames
  (`test_tour.py::test_cursor_frames_are_kernel_frames`); a promotion that
  breaks it is reverted, not excused.
- Recordings still open with a `device` frame and replay through the pure
  pipeline (`test_recordings_replay_in_ci`). **No hand-editing of JSONL** —
  if a capture is bad, capture again.

**What stays representative forever on this machine:** the `07_bigger_dies`
(H100, 132 SMs) and `07_bigger_dies_blackwell` (B300, 160 SMs) steps — this
is a 4060, and a recording claiming 132 or 160 SMs from it would be a lie
with a label on it. The helper's SM-count rule makes this refusal automatic.
Both labels are true statements; the campaign's success is measured by
honesty, not by the count of `"hardware"` strings.

**Phase 3 — calibration refresh (same sitting).** Lesson 06 posts measured
`stream_gbps` → `measurements.json` (spec_15); confirm the Simulator tab's
roofline card shows "your die, measured". Optionally build `twininject/`
(`make -C twininject`), run `./twin-run` on one lesson, and confirm
timing-only cupti chips with their source label (spec_17) — the Windows
perf-counter permission is the known blocker, and its documented fix is in
"Beyond the lessons" above. If the spec_25 watts hook is live, the session
close records `peak_power_w` too — one hardware day should refresh every
calibration the sim consumes.

**Phase 4 — re-verify, any day.**

```bash
make verify-hardware    # lint + build + preflight + run-all + checker
```

The target opens a named `verify-hardware` session, runs the whole
curriculum, then `verify_hardware.py` asserts each lesson 01–07 produced ≥1
kernel frame in the session (lesson 00: a `device_info` event), with
per-lesson PASS/FAIL and a nonzero exit on failure. It needs `nvcc` **and**
a running backend (`:8000`, or `TWIN_URL`); when the backend is down it says
so and how to fix it instead of failing lessons. Driver updates get a
one-command re-verify. After the first verified campaign, rewrite the
CLAUDE.md caveat to its post-hardware truth (date, what was promoted, what
stays representative and why) and add the README changelog row.

**Phase 5 — failure playbook.**

- `nvcc` found but binaries fail at init → `libcuda` path: WSL2 loads it
  from `/usr/lib/wsl/lib`; never install a Linux driver to "fix" this.
- `twin-sampler` silent → it shells the WSL path
  `/usr/lib/wsl/lib/nvidia-smi`; a PATH-only `nvidia-smi` is not enough.
- Lesson compiles and runs but no events arrive → the probe degrades to
  stderr when offline by design. JSON on stderr = probe fine, backend
  unreachable (check `TWIN_URL` / `:8000`). JSON absent = probe broken —
  fix the header, keep the fixtures green per Phase 0.
- Arch mismatch on non-Ada hardware: `make ARCH=-arch=sm_XX`.

## Testing without a GPU

`make lint` compile-checks every lesson (needs `nvcc` only). The probe's wire
format is CI-tested GPU-free: representative per-lesson JSON events live in
`../backend/tests/fixtures/probe_samples/` and
`tests/test_live.py::test_probe_samples_ingest` ingests each one, so the
header ↔ backend contract can't drift silently.
