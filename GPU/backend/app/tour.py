"""Lesson tours (spec_18) — pure data.

The CUDA curriculum, playable without a GPU: each step pins a frame of a
golden lesson recording (``backend/tours/lessons/<lessonId>.jsonl``, replayed
through the same pure pipeline as any session) and narrates it. Provenance is
part of the data: every step says whether its recording was captured on real
hardware or is representative — the UI must render that label (repo honesty
rule; ``test_tour.py`` enforces the field, the frontend the rendering).

Like the engines, this module is pure: no IO, no paths — recordings are
resolved by the transport layer.
"""

from __future__ import annotations

from typing import Literal

from .models import CamelModel

Provenance = Literal["hardware", "representative"]


class TourStep(CamelModel):
    id: str
    title: str
    script: str
    lesson_id: str  # keys tours/lessons/<lesson_id>.jsonl
    cursor: int  # frame of the replayed recording to show
    provenance: Provenance
    experiment: str | None = None  # the "now change something" prompt


class LessonTour(CamelModel):
    id: str
    title: str
    intro: str
    steps: list[TourStep]


TOUR = LessonTour(
    id="cuda-lessons",
    title="CUDA on this die — the guided lessons",
    intro=(
        "Seven small CUDA programs and what each one does to the silicon. "
        "Every frame below is a replayed recording of the real probe events "
        "the lessons emit — play them here, then run them live on your own "
        "GPU from GPU/cuda/."
    ),
    steps=[
        TourStep(
            id="one-block-one-sm",
            title="Threads exist",
            script=(
                "A kernel launch creates a grid of thread blocks. This is "
                "hello_thread: one block of eight threads — and exactly one "
                "SM tile lights, because a block runs entirely on one SM, "
                "never split across two. Which SM? The hardware scheduler "
                "decides; rerun it and a different tile lights."
            ),
            lesson_id="01_hello_thread",
            cursor=2,
            provenance="representative",
            experiment="Change GRID_BLOCKS to 8 and rerun a few times.",
        ),
        TourStep(
            id="grid-washes-die",
            title="The grid washes across the die",
            script=(
                "vector_add over a million elements: 4,096 blocks on 24 SMs "
                "— about 170 each. Far more blocks than SMs is the design, "
                "not a problem: the queue of waiting blocks is how the GPU "
                "hides memory latency."
            ),
            lesson_id="02_vector_add",
            cursor=2,
            provenance="representative",
            experiment="Set N to 4,096 — a third of the die stays dark.",
        ),
        TourStep(
            id="occupancy-budget",
            title="Occupancy is a budget",
            script=(
                "The same add, launched with 32-thread blocks. An SM holds "
                "at most 1,536 threads AND at most 24 blocks — tiny blocks "
                "hit the block ceiling first, and half the thread slots sit "
                "empty. The occupancy figure summarizes which budget ran "
                "out."
            ),
            lesson_id="03_block_size",
            cursor=2,
            provenance="representative",
            experiment="Find the fastest block size on your die — it's rarely 1024.",
        ),
        TourStep(
            id="matmul-uncached",
            title="The simulator's matmul, uncached",
            script=(
                "The exact computation the Simulator tab animates, one "
                "thread per output cell, every operand read straight from "
                "global memory. Note the elapsed time on the chip — the die "
                "picture looks fine; the cost is hiding in the memory "
                "system."
            ),
            lesson_id="04_matmul_naive",
            cursor=2,
            provenance="representative",
        ),
        TourStep(
            id="tiling-for-real",
            title="Tiling, for real",
            script=(
                "Same matmul, but each block stages a tile of A and B in "
                "the SM's shared memory and reuses it — spec_03's animation "
                "made physical. Same placement picture, several times "
                "faster: the speedup lives in traffic the die view doesn't "
                "draw, which is why the simulator's bandwidth model exists."
            ),
            lesson_id="05_matmul_tiled",
            cursor=2,
            provenance="representative",
            experiment="Compare this chip's elapsed ms with the previous step's.",
        ),
        TourStep(
            id="the-roof",
            title="Find the roof",
            script=(
                "A pure copy kernel does almost no math, so its speed IS "
                "the memory system's: throughput plateaus near the 4060's "
                "~256 GB/s while compute sits idle. That plateau is the "
                "roofline's memory roof — and once measured, it calibrates "
                "the Simulator tab's read-out. Your GPU can do all of this "
                "live: make run-01."
            ),
            lesson_id="06_bandwidth",
            cursor=2,
            provenance="representative",
        ),
    ],
)


def build_tour() -> LessonTour:
    return TOUR
