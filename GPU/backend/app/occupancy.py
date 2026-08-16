"""Theoretical occupancy — the resident-warp budget arithmetic (spec_24).

Pure like the engine: no FastAPI, no IO, no time. This is the same formula
the CUDA occupancy API applies for the threads-and-blocks budgets (registers
and shared memory, the other two budgets, are out of scope here — the InfoDot
copy says so instead of pretending). The Live tab's ``occupancy_pct`` for
``occupancy_source == "theoretical"`` is this arithmetic run on real hardware;
``tests/test_occupancy.py`` cross-checks the lesson-03 probe fixture against
this helper so the two tabs provably tell one story.
"""

from __future__ import annotations

from .models import Occupancy


def theoretical_occupancy(
    block_size: int,
    *,
    max_threads_per_sm: int,
    max_blocks_per_sm: int,
    warp_size: int,
) -> Occupancy:
    """Occupancy for one launch configuration against one SM's two ceilings.

    Warp-granular, like hardware: a 33-thread block claims 2 warp slots. The
    limiter names which budget ran out first — ``"blocks"`` when the block
    ceiling binds before the thread ceiling, ``"threads"`` otherwise, and
    ``"none"`` at exactly 100%.
    """
    if block_size < 1:
        raise ValueError("block_size must be >= 1")
    warps_per_block = -(-block_size // warp_size)  # ceil, without math
    max_warps_per_sm = max_threads_per_sm // warp_size
    by_threads = max_warps_per_sm // warps_per_block
    blocks_resident = min(max_blocks_per_sm, by_threads)
    occupancy_pct = 100.0 * blocks_resident * warps_per_block / max_warps_per_sm
    if occupancy_pct == 100.0:
        limiter = "none"
    elif max_blocks_per_sm < by_threads:
        limiter = "blocks"
    else:
        limiter = "threads"
    return Occupancy(
        block_size=block_size,
        warps_per_block=warps_per_block,
        blocks_resident=blocks_resident,
        occupancy_pct=occupancy_pct,
        limiter=limiter,  # type: ignore[arg-type]
    )
