"""Tiling engine tests (spec_03 §5)."""

from __future__ import annotations

import math

import pytest

from app.engine import simulate
from app.models import Workload
from app.profiles import GENERIC_128


def wl(n: int, tile: int = 0) -> Workload:
    return Workload(N=n, tile_size=tile)


def phases(trace):
    return [s.phase for s in trace]


def test_whole_matrix_reduces_to_single_tile_trace():
    # tile_size 0 and tile_size >= N both mean one tile = original trace
    for tile in (0, 4, 99):
        seen = phases(simulate(GENERIC_128, wl(4, tile)))
        assert seen == ["idle", "load", "compute", "compute", "compute", "compute", "writeback", "done"]


@pytest.mark.parametrize("n,tile", [(4, 2), (6, 2), (6, 3), (8, 2), (8, 4)])
def test_total_macs_invariant_under_tiling(n, tile):
    trace = simulate(GENERIC_128, wl(n, tile))
    assert trace[-1].mac_done == n**3 == trace[-1].mac_total
    macs = [s.mac_done for s in trace]
    assert macs == sorted(macs)  # monotonic non-decreasing
    for s in trace:
        assert s.mac_done <= s.mac_total


@pytest.mark.parametrize("n,tile", [(4, 2), (6, 2), (6, 3), (8, 4)])
def test_phase_counts_match_tile_grid(n, tile):
    trace = simulate(GENERIC_128, wl(n, tile))
    row_tiles = math.ceil(n / tile)
    col_tiles = math.ceil(n / tile)
    k_tiles = math.ceil(n / tile)
    loads = [s for s in trace if s.phase == "load"]
    writes = [s for s in trace if s.phase == "writeback"]
    assert len(loads) == row_tiles * col_tiles * k_tiles
    assert len(writes) == row_tiles * col_tiles


def test_active_cores_within_total_when_tiled():
    total = GENERIC_128.total_cores()
    for s in simulate(GENERIC_128, wl(8, 2)):
        assert s.active_cores <= total
        assert len(s.core_state) == total


def test_smaller_tiles_lower_utilization():
    # N=8 on the 128-lane die: whole matrix lights 64 cells -> 64 cores; a 2x2
    # tile lights 4 cells -> 4 cores. Tiling trades occupancy for memory.
    whole = max(s.utilization for s in simulate(GENERIC_128, wl(8, 8)))
    tiled = max(s.utilization for s in simulate(GENERIC_128, wl(8, 2)))
    assert tiled < whole


def test_tile_context_present_during_work_absent_at_rest():
    trace = simulate(GENERIC_128, wl(4, 2))
    for s in trace:
        if s.phase in ("load", "compute"):
            assert s.tile_row is not None and s.tile_col is not None
            assert s.k_tile is not None
        if s.phase == "writeback":
            assert s.tile_row is not None and s.k_tile is None
        if s.phase in ("idle", "done"):
            assert s.tile_row is None and s.k_tile is None
