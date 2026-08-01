# spec_09 — CUDA hello-world curriculum (lessons that light up the live die)

**Goal:** a progressive set of small CUDA programs for a CUDA beginner, each
designed so the live view (spec_08) shows something specific. Every lesson is a
single `.cu` file + `make run`, includes `twinprobe.cuh`, and states up front
*what you will see on the die and why*.

Directory: `GPU/cuda/` — `lessons/NN_name.cu`, `twinprobe.cuh`, `Makefile`,
`README.md` (the lesson text), `twin-sampler` (the Tier-B script).

## 0. One-time setup (WSL2 — this machine)

The GPU and `libcuda` are already visible in WSL2; only the toolkit is missing.

```bash
# CUDA toolkit for WSL-Ubuntu. CRITICAL: install the *toolkit only* — never a
# Linux driver inside WSL; the Windows driver (596.36, already installed)
# provides libcuda through /usr/lib/wsl/lib.
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update && sudo apt-get install -y cuda-toolkit
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc && source ~/.bashrc
nvcc --version   # sanity
```

Makefile default: `nvcc -arch=sm_89` (Ada). Verify with lesson 00.

## 1. The lessons

Each lesson: ~30 lines of commented code, a "what you'll see" block, and one
experiment (a knob to turn, then rerun).

**00_device_query.cu — "who am I talking to?"**
`cudaGetDeviceProperties`: prints name, SM count (expect 24), warp size, memory.
What you'll see: nothing on the die yet — this lesson verifies the toolchain and
confirms the numbers spec_07 hardcodes. Experiment: compare printout to the
anatomy page stats.

**01_hello_thread.cu — "threads exist."**
`printf` from each thread of a `<<<1, 8>>>` launch, printing
`blockIdx/threadIdx` *and its SM id* via `__twin_smid()`.
What you'll see: exactly **one SM tile lights** — one block runs on one SM,
never split (the same lesson the sim's tile-aware mapping teaches).
Experiment: `<<<8, 8>>>` — eight tiles light, and *which* eight changes run to
run: you don't choose SMs, the hardware scheduler does.

**02_vector_add.cu — "the grid washes across the die."**
Classic `c[i] = a[i] + b[i]`, N = 1M, 256 threads/block → 4,096 blocks on
24 SMs. What you'll see: every SM lights; per-SM `blocks_run` climbs to ~170
each — many more blocks than SMs is *normal and good* (latency hiding).
Experiment: N = 4,096 (16 blocks): a third of the die stays dark — too little
work to fill the machine.

**03_block_size.cu — "occupancy is a budget."**
Same vector add, block size 32 → 1024 sweep, one launch each; the probe posts
the occupancy-API number per launch. What you'll see: the timeline strip shows
elapsed-ms and occupancy per configuration; 32-thread blocks bump into the
24-resident-blocks/SM ceiling (spec_07 §1) and occupancy falls.
Experiment: find the fastest block size on *your* die; note it's not 1024.

**04_matmul_naive.cu vs 05_matmul_tiled.cu — "the sim, for real."**
The exact computation the simulator animates (spec_01–03), first naive
(every thread reads a full row+column from global memory), then tiled with
`__shared__` (the sim's spec_03 tiling made real). What you'll see: same die
lighting, but the timeline shows the tiled kernel several times faster at the
same occupancy — the speedup lives in the memory system the die view *doesn't*
show. The lesson text sends you to the sim's bandwidth model (spec_04) and
roofline read-out, now populated with the 4060's real 256 GB/s (spec_07 §4).
Experiment: tile width 8/16/32 vs the sim's tiling animation side by side.

**06_bandwidth.cu — "find the roof."**
A pure streaming kernel (grid-stride copy) timed to measure achieved GB/s.
What you'll see: util% pinned high while achieved GB/s plateaus near ~220–256 —
the memory roof; the sampler's power number climbs toward TGP.
Experiment: compute the arithmetic intensity where the 4060's ridge point sits;
check it against `analyze()`'s regime verdict in the sim tab.

## 2. `twinprobe.cuh` (contract with spec_08)

Header-only; a lesson uses exactly three things:

```cuda
#include "twinprobe.cuh"
TWIN_KERNEL_PROLOGUE();        // first line inside the kernel: records
                               // {smid, clock64 start/end} for thread 0 of each block
twin_flush("vector_add", grid, block);   // host side, after cudaDeviceSynchronize:
                               // copies records, adds cudaEvent ms + occupancy,
                               // POSTs to /api/live/ingest (env TWIN_URL,
                               // default http://localhost:8000)
```

Degrades gracefully: if the backend is down, `twin_flush` prints the JSON to
stderr and the lesson still works as a plain CUDA program. No exotic
dependencies; POST via a bundled minimal HTTP helper.

## 3. README.md structure (per lesson, beginner-first)

Concept in two sentences → the code (fully commented) → `make run` → what you
saw on the die and why → the experiment → one "going deeper" link (CUDA C++
Programming Guide section). Vocabulary spelled out on first use (kernel, block,
warp, SM, occupancy, grid-stride) per the repo's copy rule — and mirrored into
the glossary endpoint when that lands (TWIN_IMPROVEMENTS repo-wide §6).

## 4. Tests

CUDA can't run in CI here, so testing splits:
- `make lint` compiles every lesson with `nvcc -c` (syntax/arch check) — run
  manually on this machine.
- The probe's JSON output has a checked-in sample per lesson; backend
  `tests/test_live.py` ingests each sample and asserts the resulting
  `LiveState` invariants (spec_08 §3) — so the contract is CI-tested without a
  GPU.
- Lesson 00's expected SM count (24) doubles as the reality-check that profile,
  anatomy, and hardware agree.

## 5. Order of work

Lesson 00 + Makefile + toolkit install first (proves the chain end to end),
then 01 with the probe (first die lighting — the demo moment), then 02–06.
