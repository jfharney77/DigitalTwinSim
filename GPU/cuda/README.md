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

## Testing without a GPU

`make lint` compile-checks every lesson (needs `nvcc` only). The probe's wire
format is CI-tested GPU-free: representative per-lesson JSON events live in
`../backend/tests/fixtures/probe_samples/` and
`tests/test_live.py::test_probe_samples_ingest` ingests each one, so the
header ↔ backend contract can't drift silently.
