"""Deterministic operand matrices for the visualizer (spec_02 §2).

Values are small single-digit integers so the on-screen grids stay legible --
this is a teaching tool, not a numerics demo. Same (n, seed) -> identical A, B.
"""

from __future__ import annotations

Matrix = list[list[int]]


def make_operands(
    n: int, seed: int = 0, m: int = 0, k: int = 0
) -> tuple[Matrix, Matrix]:
    """Build A (M×K) and B (K×N) from a fixed, seeded pattern (spec_22).

    m/k follow the sentinel rule (0 = "= n"), so the historical two-argument
    call is bit-identical to before: indices, not shape, drive the values.
    """
    m = m or n
    k = k or n
    a: Matrix = [[((i + j + seed) % 9) + 1 for j in range(k)] for i in range(m)]
    b: Matrix = [[((i * 2 + j + seed) % 9) + 1 for j in range(n)] for i in range(k)]
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


def make_llm_data(
    n: int, kv_len: int, seed: int = 0
) -> tuple[MatrixF, tuple[MatrixF, ...], MatrixF]:
    """Deterministic data for the spec_26 LLM decode step: activations X
    (N×N, one row per stream), the six weights (Wq Wk Wv Wo Wup Wdown, all
    N×N, 1/N-scaled so repeated blocks stay O(1) and softmax stays spread),
    and the seeded prompt (kv_len×N) the initial KV cache is really run from.
    """

    def gen_rows(rows: int, off: int, scale: float = 1.0) -> MatrixF:
        return [
            [scale * (((i * 3 + j * 5 + off + seed) % 7) - 3) / 4 for j in range(n)]
            for i in range(rows)
        ]

    x = gen_rows(n, 0)
    weights = tuple(gen_rows(n, off, scale=1.0 / n) for off in range(1, 7))
    prompt = gen_rows(kv_len, 7)
    return x, weights, prompt
