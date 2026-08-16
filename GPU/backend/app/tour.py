"""Lesson tours (spec_18) — pure data.

The CUDA curriculum, playable without a GPU: each step pins a frame of a
golden lesson recording (``backend/tours/lessons/<lessonId>.jsonl``, replayed
through the same pure pipeline as any session) and narrates it. Provenance is
part of the data: every step says whether its recording was captured on real
hardware or is representative — the UI must render that label (repo honesty
rule; ``test_tour.py`` enforces the field, the frontend the rendering).

Like the engines, this module is pure: no IO, no paths — recordings are
resolved by the transport layer. spec_29: the intro, scripts, and experiments
are registered at all five reading levels via ``L(...)`` — which keeps this
module pure (``leveling`` imports nothing but ``typing``) and keeps
resolution in ``main.py``, never here: ``build_tour()`` still returns the
level-3 tour.
"""

from __future__ import annotations

from typing import Literal

from .leveling import L
from .models import CamelModel

Provenance = Literal["hardware", "representative"]

# spec_31: a step claiming provenance="hardware" must carry a real
# driver-reported device name in its recording's device_info frame. These
# markers (plus the simulator's profile labels, checked at the test/tool
# edge where importing profiles is allowed) define "generic". Pure data —
# the campaign tools in GPU/cuda/ mirror this definition; test_tour.py
# enforces it.
GENERIC_DEVICE_MARKERS: tuple[str, ...] = ("representative", "generic")


def device_name_is_generic(name: str | None) -> bool:
    """True when a device_info name could not have come from a real driver:
    empty, or carrying a placeholder marker. Profile-label matching (the
    other half of spec_31's definition) lives with the callers that may
    import ``profiles``."""
    if name is None or not name.strip():
        return True
    lowered = name.strip().lower()
    return any(m in lowered for m in GENERIC_DEVICE_MARKERS)


class TourStep(CamelModel):
    id: str
    title: str
    script: str
    lesson_id: str  # keys tours/lessons/<lesson_id>.jsonl
    cursor: int  # frame of the replayed recording to show
    provenance: Provenance
    experiment: str | None = None  # the "now change something" prompt
    # spec_30: optional hash URL ("#", "#anatomy/gh100", "#anatomy/a/vs/b",
    # "#live") the UI renders as a real button beside the experiment prose.
    # Authored here as data; test_tour.py checks every link resolves.
    link: str | None = None


class LessonTour(CamelModel):
    id: str
    title: str
    intro: str
    steps: list[TourStep]


TOUR = LessonTour(
    id="cuda-lessons",
    title="CUDA on this die — the guided lessons",
    intro=L(
        novice=(
            "This is a guided tour of eight small programs written in CUDA — "
            "the language used to program NVIDIA graphics chips (GPUs). Each "
            "step shows what one program does to the chip itself: which parts "
            "light up, and why. You do not need a GPU to follow along — every "
            "picture is a replay of a recording made when the lessons ran for "
            "real. When you are done, the same programs live in GPU/cuda/, "
            "ready to run on your own machine."
        ),
        plain=(
            "Eight small CUDA programs, each shown through a recording of the "
            "probe events it emitted while running — the same events a live "
            "session would stream. Play the recordings here to see what each "
            "program does to the silicon, then run the lessons on your own "
            "GPU from GPU/cuda/."
        ),
        standard=(
            "Eight small CUDA programs and what each one does to the silicon. "
            "Every frame below is a replayed recording of the real probe events "
            "the lessons emit — play them here, then run them live on your own "
            "GPU from GPU/cuda/."
        ),
        technical=(
            "Eight CUDA lessons, each pinned to a replayed probe recording — "
            "the same event pipeline as a live session. Step through here; "
            "run them for real from GPU/cuda/."
        ),
        expert=(
            "Eight CUDA lessons as replayed probe recordings; live "
            "equivalents in GPU/cuda/."
        ),
    ),
    steps=[
        TourStep(
            id="one-block-one-sm",
            title="Threads exist",
            script=L(
                novice=(
                    "When a GPU program starts, it launches a kernel — a "
                    "function that many threads run at once. Those threads "
                    "are grouped into blocks, and the set of blocks is called "
                    "the grid. This program, hello_thread, launches the "
                    "smallest grid there is: one block of eight threads. "
                    "Watch the picture: exactly one tile lights up. Each tile "
                    "is an SM — a streaming multiprocessor, one of the GPU's "
                    "independent processing engines — and a block always runs "
                    "entirely inside one SM, never split across two. Which SM "
                    "gets the block? The chip's own scheduler picks; run the "
                    "program again and a different tile lights."
                ),
                plain=(
                    "Launching a kernel — the function a GPU runs — creates a "
                    "grid of thread blocks. hello_thread launches one block "
                    "of eight threads, and exactly one SM (streaming "
                    "multiprocessor) tile lights, because a block runs "
                    "entirely on one SM, never split across two. The hardware "
                    "scheduler picks which one; rerun it and a different tile "
                    "lights."
                ),
                standard=(
                    "A kernel launch creates a grid of thread blocks. This is "
                    "hello_thread: one block of eight threads — and exactly one "
                    "SM tile lights, because a block runs entirely on one SM, "
                    "never split across two. Which SM? The hardware scheduler "
                    "decides; rerun it and a different tile lights."
                ),
                technical=(
                    "hello_thread: a one-block, eight-thread launch. One SM "
                    "tile lights — blocks never split across SMs — and the "
                    "block scheduler picks which, so reruns move the tile."
                ),
                expert=(
                    "1×8 launch → one SM. Blocks never split; placement is "
                    "the scheduler's, nondeterministic across runs."
                ),
            ),
            lesson_id="01_hello_thread",
            cursor=2,
            provenance="representative",
            experiment=L(
                novice=(
                    "Open the lesson source and change GRID_BLOCKS from 1 to "
                    "8, then run it a few times. Eight blocks means eight "
                    "tiles light — and they land on different SMs each run, "
                    "because placement is the scheduler's choice, not the "
                    "program's."
                ),
                plain=(
                    "Change GRID_BLOCKS to 8 and rerun a few times — eight "
                    "tiles light, on different SMs each run."
                ),
                standard="Change GRID_BLOCKS to 8 and rerun a few times.",
                technical="GRID_BLOCKS=8, rerun: eight tiles, fresh placement each run.",
                expert="GRID_BLOCKS=8 ×N runs: placement shuffles.",
            ),
        ),
        TourStep(
            id="grid-washes-die",
            title="The grid washes across the die",
            script=L(
                novice=(
                    "vector_add adds two lists of a million numbers each. "
                    "That takes 4,096 blocks of threads — far more than the "
                    "24 SMs (streaming multiprocessors, the GPU's processing "
                    "engines) this laptop die has, so each SM works through "
                    "about 170 blocks, one after another. That imbalance is "
                    "deliberate. Whenever a block stalls waiting on memory — "
                    "and memory is slow compared to arithmetic — the SM swaps "
                    "in another block from the queue and keeps busy. The "
                    "oversupply of blocks is the GPU's trick for hiding "
                    "memory latency."
                ),
                plain=(
                    "vector_add over a million elements needs 4,096 blocks, "
                    "spread over 24 SMs — about 170 each. Having far more "
                    "blocks than SMs is the design, not a problem: when one "
                    "block stalls on a memory read, the SM runs another from "
                    "the queue, which is how the GPU hides memory latency."
                ),
                standard=(
                    "vector_add over a million elements: 4,096 blocks on 24 SMs "
                    "— about 170 each. Far more blocks than SMs is the design, "
                    "not a problem: the queue of waiting blocks is how the GPU "
                    "hides memory latency."
                ),
                technical=(
                    "vector_add, 1M elements: 4,096 blocks over 24 SMs, ~170 "
                    "per SM. Oversubscription is the point — the block queue "
                    "covers memory stalls."
                ),
                expert=(
                    "4,096 blocks / 24 SMs ≈ 170:1. Oversubscription hides "
                    "DRAM latency."
                ),
            ),
            lesson_id="02_vector_add",
            cursor=2,
            provenance="representative",
            experiment=L(
                novice=(
                    "Set N — the number of elements — down to 4,096 and "
                    "rerun. Now there are only 16 blocks for 24 SMs, so a "
                    "third of the die never gets a block at all and stays "
                    "dark. A GPU needs enough work to fill itself."
                ),
                plain=(
                    "Set N to 4,096 — only 16 blocks for 24 SMs, so a third "
                    "of the die stays dark."
                ),
                standard="Set N to 4,096 — a third of the die stays dark.",
                technical="N=4,096 → 16 blocks < 24 SMs: a third of the die idles.",
                expert="N=4,096: 16 blocks, 8 SMs dark.",
            ),
        ),
        TourStep(
            id="occupancy-budget",
            title="Occupancy is a budget",
            script=L(
                novice=(
                    "The same addition, but now each block holds only 32 "
                    "threads. An SM (streaming multiprocessor) can host at "
                    "most 1,536 threads at once — but also at most 24 blocks "
                    "at once, whichever limit is reached first. Twenty-four "
                    "blocks of 32 threads is only 768 threads, so half the "
                    "thread slots sit empty: the tiny blocks ran out of the "
                    "block budget before the thread budget. Occupancy is the "
                    "name for how full an SM's thread slots are, and the "
                    "figure tells you which budget ran out."
                ),
                plain=(
                    "The same add, launched with 32-thread blocks. An SM can "
                    "hold at most 1,536 resident threads AND at most 24 "
                    "resident blocks — tiny blocks hit the block ceiling "
                    "first, leaving half the thread slots empty. Occupancy is "
                    "the measure of how full those slots are, and it "
                    "summarizes which budget ran out."
                ),
                standard=(
                    "The same add, launched with 32-thread blocks. An SM holds "
                    "at most 1,536 threads AND at most 24 blocks — tiny blocks "
                    "hit the block ceiling first, and half the thread slots sit "
                    "empty. The occupancy figure summarizes which budget ran "
                    "out."
                ),
                technical=(
                    "Same add, 32-thread blocks. Residency caps: 1,536 "
                    "threads AND 24 blocks per SM — 24×32 = 768 threads, so "
                    "occupancy tops out at 50%, block-limited."
                ),
                expert=(
                    "32-thread blocks: 24-block cap × 32 = 768/1,536 → 50% "
                    "occupancy, block-limited."
                ),
            ),
            lesson_id="03_block_size",
            cursor=2,
            provenance="representative",
            experiment=L(
                novice=(
                    "Try several block sizes — 64, 128, 256, 512, 1024 — and "
                    "time each one on your own GPU. The fastest is rarely the "
                    "biggest: very large blocks are clumsy to schedule, very "
                    "small ones hit the block ceiling. Somewhere in the "
                    "middle wins."
                ),
                plain=(
                    "Time a few block sizes on your die and find the fastest "
                    "— it's rarely 1024."
                ),
                standard="Find the fastest block size on your die — it's rarely 1024.",
                technical="Sweep block sizes; the optimum is mid-range, not 1024.",
                expert="Sweep sizes; optimum ≠ 1024.",
            ),
        ),
        TourStep(
            id="matmul-uncached",
            title="The simulator's matmul, uncached",
            script=L(
                novice=(
                    "This is a matrix multiplication — the exact computation "
                    "the Simulator tab animates — written the simplest "
                    "possible way: one thread per output cell, and every "
                    "number fetched straight from the GPU's main memory "
                    "(called global memory) each time it is needed. The die "
                    "picture looks perfectly healthy: every SM is busy. But "
                    "note the elapsed time printed on the chip. The cost of "
                    "this version is invisible here, because it hides in the "
                    "memory system — the same values being fetched again and "
                    "again."
                ),
                plain=(
                    "The exact computation the Simulator tab animates, one "
                    "thread per output cell, with every operand read straight "
                    "from global memory each time it's needed. The die "
                    "picture looks fine — every SM busy — but note the "
                    "elapsed time: the cost hides in the memory system."
                ),
                standard=(
                    "The exact computation the Simulator tab animates, one "
                    "thread per output cell, every operand read straight from "
                    "global memory. Note the elapsed time on the chip — the die "
                    "picture looks fine; the cost is hiding in the memory "
                    "system."
                ),
                technical=(
                    "The simulator's matmul, naive: one thread per output "
                    "cell, all operands from global memory. Placement looks "
                    "healthy; the elapsed time says otherwise — the cost is "
                    "memory traffic."
                ),
                expert=(
                    "Naive matmul: per-cell threads, all traffic to DRAM. "
                    "Die view clean; time isn't."
                ),
            ),
            lesson_id="04_matmul_naive",
            cursor=2,
            provenance="representative",
        ),
        TourStep(
            id="tiling-for-real",
            title="Tiling, for real",
            script=L(
                novice=(
                    "The same matrix multiplication, one change: each block "
                    "first copies a small square tile of each input matrix "
                    "into shared memory — a fast scratchpad inside the SM — "
                    "and then reuses those numbers many times before fetching "
                    "more. This is the tiling idea the simulator animates, "
                    "made physical. The placement picture looks identical to "
                    "the previous step, yet the program runs several times "
                    "faster. The speedup lives entirely in memory traffic the "
                    "die view cannot draw — which is exactly why the "
                    "simulator has a bandwidth model."
                ),
                plain=(
                    "Same matmul, but each block stages a tile of A and B in "
                    "the SM's shared memory — a fast on-chip scratchpad — and "
                    "reuses it, spec_03's animation made physical. The "
                    "placement picture is identical yet the run is several "
                    "times faster: the speedup lives in traffic the die view "
                    "doesn't draw, which is why the simulator's bandwidth "
                    "model exists."
                ),
                standard=(
                    "Same matmul, but each block stages a tile of A and B in "
                    "the SM's shared memory and reuses it — spec_03's animation "
                    "made physical. Same placement picture, several times "
                    "faster: the speedup lives in traffic the die view doesn't "
                    "draw, which is why the simulator's bandwidth model exists."
                ),
                technical=(
                    "Tiled matmul: blocks stage A/B tiles in shared memory "
                    "and reuse them. Identical placement, several-times "
                    "speedup — all in DRAM traffic the die view doesn't "
                    "render."
                ),
                expert=(
                    "Shared-memory tiling: same placement, several× faster; "
                    "the win is DRAM traffic, invisible here."
                ),
            ),
            lesson_id="05_matmul_tiled",
            cursor=2,
            provenance="representative",
            experiment=L(
                novice=(
                    "Look at the elapsed milliseconds printed on this chip, "
                    "then flip back to the previous step and compare. Same "
                    "computation, same placement picture — the difference is "
                    "the tiles being reused instead of re-fetched."
                ),
                plain=(
                    "Compare this chip's elapsed ms with the previous step's "
                    "— same picture, very different time."
                ),
                standard="Compare this chip's elapsed ms with the previous step's.",
                technical="Diff the elapsed ms against step 4's.",
                expert="ms here vs step 4.",
            ),
        ),
        TourStep(
            id="the-roof",
            title="Find the roof",
            script=L(
                novice=(
                    "This kernel simply copies data — almost no arithmetic at "
                    "all — so how fast it runs is really a measurement of the "
                    "memory system itself. Watch the throughput climb and "
                    "then flatten near 256 gigabytes per second: that is this "
                    "laptop GPU's memory at full speed, with the arithmetic "
                    "units idle. The flat ceiling is called the memory roof "
                    "in the roofline model of performance, and once measured "
                    "it calibrates the read-out on the Simulator tab. "
                    "Everything in this tour can also run live on your own "
                    "GPU: type make run-01 in GPU/cuda/."
                ),
                plain=(
                    "A pure copy kernel does almost no math, so its speed is "
                    "really the memory system's: throughput plateaus near the "
                    "4060's ~256 GB/s while the compute units sit idle. That "
                    "plateau is the roofline model's memory roof, and once "
                    "measured it calibrates the Simulator tab's read-out. "
                    "Your GPU can do all of this live: make run-01."
                ),
                standard=(
                    "A pure copy kernel does almost no math, so its speed IS "
                    "the memory system's: throughput plateaus near the 4060's "
                    "~256 GB/s while compute sits idle. That plateau is the "
                    "roofline's memory roof — and once measured, it calibrates "
                    "the Simulator tab's read-out. Your GPU can do all of this "
                    "live: make run-01."
                ),
                technical=(
                    "Copy kernel ≈ zero arithmetic intensity: throughput "
                    "saturates at the 4060's ~256 GB/s, compute idle. That is "
                    "the roofline's memory roof; the measurement calibrates "
                    "the simulator. Live: make run-01."
                ),
                expert=(
                    "Copy kernel → BW ceiling ~256 GB/s = memory roof; "
                    "calibrates the sim roofline. make run-01."
                ),
            ),
            lesson_id="06_bandwidth",
            cursor=2,
            provenance="representative",
            # spec_30: the roofline read-out this measurement calibrates lives
            # on the simulator tab.
            link="#",
        ),
        TourStep(
            id="the-die-is-a-parameter",
            title="The die is a parameter",
            script=L(
                novice=(
                    "Lesson 07 is written to run on any NVIDIA GPU: instead "
                    "of assuming a chip, it asks the driver software how many "
                    "SMs (streaming multiprocessors — the GPU's processing "
                    "engines) the die has, and launches two blocks for each. "
                    "This frame shows that same program on an H100, a "
                    "data-centre GPU: 264 blocks spread evenly over 132 "
                    "tiles, where a laptop die would light just 24. The "
                    "picture resized itself because the recording carries a "
                    "description of the device it was made on. The program "
                    "didn't change — the silicon did."
                ),
                plain=(
                    "Lesson 07 never names its GPU: it asks the driver how "
                    "many SMs the die has and launches two blocks per SM. "
                    "This frame is that same binary on an H100 SXM, a "
                    "data-centre part — 264 blocks over 132 tiles, where your "
                    "laptop would light 24. The die view resizes because "
                    "device_info travels with the recording; the program "
                    "didn't change, the silicon did."
                ),
                standard=(
                    "Lesson 07 never names its GPU: it asks the driver how many "
                    "SMs the die has and launches two blocks per SM. This frame "
                    "is that binary on an H100 SXM — 264 blocks washing evenly "
                    "over 132 tiles, where your laptop would light 24. The die "
                    "view resizes itself because device_info travels with the "
                    "recording; the program didn't change, the silicon did."
                ),
                technical=(
                    "Lesson 07 queries SM count and launches 2 blocks/SM. "
                    "Shown here on H100 SXM: 264 blocks over 132 tiles vs a "
                    "laptop's 24. device_info in the recording resizes the "
                    "die view — same binary, different silicon."
                ),
                expert=(
                    "2 blocks/SM off a device query: H100 SXM → 264 blocks / "
                    "132 tiles vs 24. device_info scales the view."
                ),
            ),
            lesson_id="07_bigger_dies",
            cursor=2,
            provenance="representative",
            experiment=L(
                novice=(
                    "On the Simulator tab, switch the GPU profile to H100-SXM "
                    "and run the matmul again. The whole animation rescales "
                    "to the bigger die — the simulator's selectable profiles "
                    "are the same write-once-run-anywhere idea, seen from the "
                    "software side."
                ),
                plain=(
                    "Switch the Simulator tab's profile to H100-SXM and rerun "
                    "the matmul — the selectable profiles are the same idea "
                    "from the software side."
                ),
                standard=(
                    "Switch the Simulator tab's profile to H100-SXM and rerun "
                    "the matmul — the fleet profiles are the same idea from the "
                    "software side."
                ),
                technical=(
                    "Sim tab → H100-SXM profile, rerun the matmul: the same "
                    "device-parameterization, software side."
                ),
                expert="Sim profile → H100-SXM; rerun.",
            ),
            link="#anatomy/gh100",  # spec_30: the H100's die, annotated
        ),
        TourStep(
            id="blackwell-two-dies-one-gpu",
            title="Blackwell: two dies, one GPU",
            script=L(
                novice=(
                    "The same lesson once more, now on a Blackwell Ultra B300 "
                    "— NVIDIA's newest data-centre GPU: 320 blocks over 160 "
                    "SM tiles. Physically, this chip is two chips, each as "
                    "large as manufacturing allows, fused by an extremely "
                    "fast link down the middle. But watch the SM identifiers "
                    "the recording reports: they run 0 to 159 in one unbroken "
                    "sequence. The fusing link is fast enough that software "
                    "sees a single GPU, seam and all invisible. The Anatomy "
                    "tab's B300 entry draws the seam this picture can't see — "
                    "and elsewhere in this repo, the XE9712 rack twin shows "
                    "the same trick fusing 72 of these into one unit."
                ),
                plain=(
                    "The same lesson on a Blackwell Ultra B300: 320 blocks "
                    "over 160 SM tiles. Physically that's two maximum-size "
                    "dies fused by a 10 TB/s link down the middle — but the "
                    "reported smids run 0 to 159 with no seam, because the "
                    "NV-HBI link presents one logical GPU. The Anatomy tab's "
                    "B300 entry draws the seam this picture can't see; the "
                    "XE9712 twin plays the same trick at rack scale with 72 "
                    "of them."
                ),
                standard=(
                    "The same lesson on a Blackwell Ultra B300: 320 blocks over "
                    "160 SM tiles. Physically that's two reticle-limited dies "
                    "fused by a 10 TB/s link — but watch the smids: they run 0 "
                    "to 159 with no seam, because NV-HBI presents one logical "
                    "GPU. The Anatomy tab's B300 entry draws the seam this "
                    "picture can't see; the XE9712 twin plays the same trick at "
                    "rack scale, fusing 72 of these into one domain."
                ),
                technical=(
                    "Same binary on B300: 320 blocks, 160 SMs, smids 0–159 "
                    "seamless across two reticle-limited dies — NV-HBI "
                    "presents one logical GPU. The Anatomy tab draws the "
                    "seam; XE9712 repeats the move at rack scale, 72 GPUs to "
                    "a domain."
                ),
                expert=(
                    "B300: 320 blocks, 160 SMs, smids 0–159, no seam — "
                    "NV-HBI, one logical GPU. Anatomy draws the seam; XE9712 "
                    "= same trick ×72."
                ),
            ),
            lesson_id="07_bigger_dies_blackwell",
            cursor=2,
            provenance="representative",
            experiment=L(
                novice=(
                    "Open the Anatomy tab and pick the B300 (Blackwell Ultra) "
                    "die. Look for the thin vertical strip labelled NV-HBI "
                    "down the middle of the floorplan — that is the "
                    "die-to-die link these 160 seamless tiles are hiding."
                ),
                plain=(
                    "Open the Anatomy tab's B300 die and find the NV-HBI "
                    "strip down the middle — the link these 160 tiles hide."
                ),
                standard=(
                    "Open the Anatomy tab's B300 (Blackwell Ultra) die and find "
                    "the NV-HBI strip these 160 tiles hide."
                ),
                technical="Anatomy → B300: locate the NV-HBI strip the smids hide.",
                expert="Anatomy/B300 → NV-HBI strip.",
            ),
            # spec_30: the Blackwell refresh side by side — same floorplan,
            # more HBM — via the compare deep link.
            link="#anatomy/gb300/vs/gb200",
        ),
    ],
)


def build_tour() -> LessonTour:
    return TOUR
