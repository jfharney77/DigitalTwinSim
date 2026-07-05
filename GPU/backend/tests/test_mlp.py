"""spec_06 invariants: the MLP training step is five matmuls that learn."""

from __future__ import annotations

import math

import pytest

from app.mlp import ETA, MATMULS_PER_STEP, OPS_PER_STEP, simulate_mlp
from app.models import Workload
from app.profiles import DEFAULT_PROFILE

EXPECTED_OP_NAMES = [
    "Z1 = X·W1",
    "A1 = relu(Z1)",
    "Z2 = A1·W2",
    "δ2 = Z2 − Y",
    "dW2 = A1ᵀ·δ2",
    "δ1 = δ2·W2ᵀ ⊙ relu′",
    "dW1 = Xᵀ·δ1",
    "W ← W − η·dW",
]

MATMUL_POSITIONS = {0, 2, 4, 5, 6}


def run(n: int = 4, steps: int = 1, **kw):
    wl = Workload(kind="mlp_step", N=n, steps=steps, **kw)
    return simulate_mlp(DEFAULT_PROFILE, wl)


def test_mac_total_is_steps_times_five_matmuls():
    for n in (2, 4, 8):
        for steps in (1, 3):
            trace, _ = run(n, steps)
            expected = steps * MATMULS_PER_STEP * n**3
            assert all(s.mac_total == expected for s in trace)
            assert trace[-1].phase == "done"
            assert trace[-1].mac_done == expected


def test_op_order_and_alignment():
    steps = 2
    trace, info = run(4, steps)
    assert info.ops_per_step == OPS_PER_STEP
    assert len(info.ops) == steps * OPS_PER_STEP
    assert [op.name for op in info.ops] == EXPECTED_OP_NAMES * steps
    for i, op in enumerate(info.ops):
        expected_kind = "matmul" if i % OPS_PER_STEP in MATMUL_POSITIONS else "pointwise"
        assert op.kind == expected_kind

    # SimState op context marches through ops in order, never backwards.
    seen = [s.op_index for s in trace if s.op_index is not None]
    assert seen == sorted(seen)
    assert set(seen) == set(range(steps * OPS_PER_STEP))
    for s in trace:
        if s.op_index is not None:
            assert s.op_name == info.ops[s.op_index].name
            assert s.step_index == s.op_index // OPS_PER_STEP


def test_spec01_invariants_hold_inside_ops():
    trace, _ = run(4, 2, tileSize=2, doubleBuffer=True)
    total_cores = DEFAULT_PROFILE.total_cores()
    prev_mac = 0
    for s in trace:
        assert s.active_cores <= total_cores
        assert s.utilization == pytest.approx(s.active_cores / total_cores)
        assert s.mac_done >= prev_mac  # monotonic across the whole chain
        assert s.mac_done <= s.mac_total
        prev_mac = s.mac_done


def test_loss_strictly_falls_for_canned_seed():
    for n in (2, 4, 8):
        _, info = run(n, steps=5, seed=0)
        assert info.eta == ETA
        assert len(info.loss) == 5
        for a, b in zip(info.loss, info.loss[1:]):
            assert b < a, f"loss did not fall at n={n}: {info.loss}"


def test_weights_and_losses_stay_finite():
    _, info = run(8, steps=10)
    assert all(math.isfinite(v) for v in info.loss)
    for op in info.ops:
        for m in (op.a, op.b):
            if m:
                assert all(math.isfinite(v) for row in m for v in row)


def test_matmul_ops_carry_operands_pointwise_do_not():
    _, info = run(4)
    for op in info.ops:
        if op.kind == "matmul":
            assert op.a and op.b and op.a_label and op.b_label and op.c_label
        else:
            assert op.a is None and op.b is None
