"""Trace-based engine tests. Asserts the invariants from spec §8."""

from __future__ import annotations

import pytest

from app.engine import simulate
from app.models import GpuProfile, Memory, SMGrid, Workload
from app.profiles import GENERIC_128

PHASE_ORDER = ["idle", "load", "compute", "writeback", "done"]


def make_workload(n: int) -> Workload:
    return Workload(N=n)


def test_mac_totals_for_n4():
    trace = simulate(GENERIC_128, make_workload(4))
    final = trace[-1]
    assert final.mac_total == 64  # 4^3
    assert final.mac_done == 64
    assert final.mac_done == final.mac_total


@pytest.mark.parametrize("n", [2, 3, 4, 8])
def test_mac_done_never_exceeds_total(n):
    trace = simulate(GENERIC_128, make_workload(n))
    for s in trace:
        assert s.mac_done <= s.mac_total
    assert trace[-1].mac_done == n**3


@pytest.mark.parametrize("n", [2, 4, 8])
def test_active_cores_within_total(n):
    total = GENERIC_128.total_cores()
    for s in simulate(GENERIC_128, make_workload(n)):
        assert s.active_cores <= total
        assert len(s.core_state) == total


@pytest.mark.parametrize("n", [2, 4, 8])
def test_utilization_matches_active_ratio(n):
    total = GENERIC_128.total_cores()
    for s in simulate(GENERIC_128, make_workload(n)):
        assert s.utilization == pytest.approx(s.active_cores / total)


def test_phases_advance_without_skips():
    trace = simulate(GENERIC_128, make_workload(4))
    seen = [s.phase for s in trace]
    # exactly one idle, one load, N compute, one writeback, one done
    assert seen[0] == "idle"
    assert seen[1] == "load"
    assert seen[-2] == "writeback"
    assert seen[-1] == "done"
    assert seen.count("compute") == 4
    # phase index is monotonically non-decreasing in canonical order
    indices = [PHASE_ORDER.index(p) for p in seen]
    assert indices == sorted(indices)


def test_compute_steps_equal_n():
    for n in (2, 4, 8):
        trace = simulate(GENERIC_128, make_workload(n))
        compute = [s for s in trace if s.phase == "compute"]
        assert len(compute) == n
        assert compute[-1].k == n


def test_cycle_is_monotonic():
    trace = simulate(GENERIC_128, make_workload(5))
    cycles = [s.cycle for s in trace]
    assert cycles == list(range(len(trace)))


@pytest.mark.parametrize("n,t", [(6, 4), (8, 2), (8, 3), (4, 2)])
def test_tile_cells_stay_within_one_sm(n, t):
    # A tile's shared-memory working set lives in one SM, so all of its output
    # cells must map to lanes within a single SM -- never straddle two.
    cores_per_sm = GENERIC_128.cores_per_sm.rows * GENERIC_128.cores_per_sm.cols
    trace = simulate(GENERIC_128, Workload(N=n, tileSize=t))
    for s in trace:
        if s.phase != "compute":
            continue
        active = [i for i, c in enumerate(s.core_state) if c == "computing"]
        sms = {a // cores_per_sm for a in active}
        assert len(sms) <= 1, f"tile ({s.tile_row},{s.tile_col}) straddles SMs {sms}"


def test_oversubscribed_cores_when_n_squared_exceeds_cores():
    # tiny die: 1 SM, 2x2 cores = 4 cores; N=4 -> 16 cells round-robin onto 4
    tiny = GpuProfile(
        name="tiny",
        sm=SMGrid(rows=1, cols=1),
        cores_per_sm=SMGrid(rows=2, cols=2),
        memory=Memory(stacks=1),
    )
    trace = simulate(tiny, make_workload(4))
    compute = [s for s in trace if s.phase == "compute"][0]
    assert compute.active_cores == 4  # all 4 cores used
    assert compute.utilization == pytest.approx(1.0)
