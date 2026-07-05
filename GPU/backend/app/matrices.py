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


MatrixF = list[list[float]]


def make_mlp_data(n: int, seed: int = 0) -> tuple[MatrixF, MatrixF, MatrixF, MatrixF]:
    """Deterministic X, Y, W1, W2 for the spec_06 MLP: small centered floats so
    SGD with the fixed eta reliably reduces the loss and the grids stay legible."""

    def gen(off: int) -> MatrixF:
        return [
            [(((i * 3 + j * 5 + off + seed) % 7) - 3) / 4 for j in range(n)]
            for i in range(n)
        ]

    return gen(0), gen(1), gen(2), gen(3)
