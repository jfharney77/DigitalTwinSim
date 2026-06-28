"""Deterministic operand matrices for the visualizer (spec_02 §2).

Values are small single-digit integers so the on-screen grids stay legible --
this is a teaching tool, not a numerics demo. Same (n, seed) -> identical A, B.
"""

from __future__ import annotations

Matrix = list[list[int]]


def make_operands(n: int, seed: int = 0) -> tuple[Matrix, Matrix]:
    """Build A and B for an N x N matmul from a fixed, seeded pattern."""
    a: Matrix = [[((i + j + seed) % 9) + 1 for j in range(n)] for i in range(n)]
    b: Matrix = [[((i * 2 + j + seed) % 9) + 1 for j in range(n)] for i in range(n)]
    return a, b
