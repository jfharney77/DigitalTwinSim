"""Tests for deterministic operands (spec_02 §6)."""

from __future__ import annotations

import pytest

from app.matrices import make_operands


def matmul(a, b, n):
    return [
        [sum(a[i][k] * b[k][j] for k in range(n)) for j in range(n)]
        for i in range(n)
    ]


@pytest.mark.parametrize("n", [2, 4, 8])
def test_deterministic(n):
    assert make_operands(n, 0) == make_operands(n, 0)


def test_seed_changes_values():
    assert make_operands(4, 0) != make_operands(4, 1)


@pytest.mark.parametrize("n", [2, 4, 8])
def test_shape_and_legible_values(n):
    a, b = make_operands(n, 0)
    assert len(a) == n and all(len(row) == n for row in a)
    assert len(b) == n and all(len(row) == n for row in b)
    # single-digit operands keep the grid readable
    for row in (*a, *b):
        for v in row:
            assert 1 <= v <= 9


def test_partial_c_accumulates_to_full_matmul():
    # Partial sum at k equals sum over first k products; at k=N it's the matmul.
    n = 3
    a, b = make_operands(n, 0)

    def partial(i, j, k):
        return sum(a[i][kk] * b[kk][j] for kk in range(k))

    full = matmul(a, b, n)
    for i in range(n):
        for j in range(n):
            assert partial(i, j, 1) == a[i][0] * b[0][j]
            assert partial(i, j, n) == full[i][j]
