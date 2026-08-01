"""spec_07 — the RTX 4060 Laptop profile (the user's real die).

The engine invariants are profile-generic by design; these tests prove they
hold on a die an order of magnitude bigger than the generic profiles, and pin
the numbers that must agree with the hardware (nvidia-smi reports 24 SMs and
8 GB on this machine) so the live CUDA mode (spec_08) lights the right tiles.
"""

from __future__ import annotations

from app.engine import simulate
from app.models import Workload
from app.profiles import PROFILES, RTX_4060_LAPTOP


def test_registered() -> None:
    assert "RTX-4060-Laptop" in PROFILES


def test_geometry_matches_hardware() -> None:
    # AD107: 24 SMs x 128 FP32 cores. If these drift, the live mode's per-SM
    # activity (indexed by the hardware's %smid) no longer maps onto the tiles.
    assert RTX_4060_LAPTOP.sm.rows * RTX_4060_LAPTOP.sm.cols == 24
    cps = RTX_4060_LAPTOP.cores_per_sm
    assert cps.rows * cps.cols == 128
    assert RTX_4060_LAPTOP.total_cores() == 3072


def test_ridge_point_right_of_generic() -> None:
    # The laptop story: narrow bus + strong compute => higher ridge point =>
    # memory-bound at smaller sizes than the generic dies.
    generic = PROFILES["Generic-128"]
    ridge = lambda p: p.bandwidth.macs_per_cycle / p.bandwidth.bytes_per_cycle  # noqa: E731
    assert ridge(RTX_4060_LAPTOP) > ridge(generic)


def test_engine_invariants_hold_on_the_big_die() -> None:
    n = 8
    trace = simulate(RTX_4060_LAPTOP, Workload(n=n))
    total = RTX_4060_LAPTOP.total_cores()
    assert trace, "empty trace"
    prev_mac = 0
    for s in trace:
        assert len(s.core_state) == total
        assert s.active_cores <= total
        assert abs(s.utilization - s.active_cores / total) < 1e-9
        assert s.mac_done >= prev_mac
        prev_mac = s.mac_done
    last = trace[-1]
    assert last.phase == "done"
    assert last.mac_done == last.mac_total == n * n * n


def test_small_matmul_cannot_fill_the_die() -> None:
    # Honest lesson (mirrors spec_09 lesson 02): an 8x8 matmul has 64 cells —
    # utilization on 3072 lanes stays tiny. The die *should* look mostly dark.
    trace = simulate(RTX_4060_LAPTOP, Workload(n=8))
    assert max(s.active_cores for s in trace) <= 64
    assert max(s.utilization for s in trace) <= 64 / 3072 + 1e-9
