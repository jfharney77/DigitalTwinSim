"""Maps output matrix cells onto physical cores.

Currently round-robin: core = (i*N + j) % totalCores. Deliberately naive --
real warp/tile scheduling is roadmap work (spec §4, §7).
"""

from __future__ import annotations


def cell_to_core(i: int, j: int, n: int, total_cores: int) -> int:
    return (i * n + j) % total_cores


def mapped_cores(n: int, total_cores: int) -> list[int]:
    """Distinct physical cores used by an N x N output, sorted."""
    used = {cell_to_core(i, j, n, total_cores) for i in range(n) for j in range(n)}
    return sorted(used)
