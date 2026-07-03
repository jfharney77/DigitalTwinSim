"""Double-buffering / pipelining tests (spec_05 §4)."""

from __future__ import annotations

import pytest

from app.engine import analyze, simulate
from app.models import Workload
from app.profiles import GENERIC_128


def wl(n: int, tile: int = 0, dbuf: bool = False) -> Workload:
    return Workload(N=n, tile_size=tile, double_buffer=dbuf)


def strip(trace):
    """Comparable projection (drop the big core_state array)."""
    return [
        (s.phase, s.k, s.mac_done, s.mem_active, s.stalled, s.prefetching,
         s.tile_row, s.tile_col, s.k_tile)
        for s in trace
    ]


def test_flag_off_matches_serial_regression():
    a = simulate(GENERIC_128, wl(6, 3, dbuf=False))
    b = simulate(GENERIC_128, wl(6, 3))  # default is serial
    assert strip(a) == strip(b)


def test_single_tile_identical_with_or_without_double_buffer():
    # Nothing to overlap when the whole matrix is one tile.
    serial = simulate(GENERIC_128, wl(4, 0, dbuf=False))
    pipe = simulate(GENERIC_128, wl(4, 0, dbuf=True))
    assert strip(serial) == strip(pipe)


@pytest.mark.parametrize("n,tile", [(4, 2), (6, 2), (6, 3), (8, 4)])
def test_pipelined_total_macs(n, tile):
    trace = simulate(GENERIC_128, wl(n, tile, dbuf=True))
    assert trace[-1].mac_done == n**3 == trace[-1].mac_total
    macs = [s.mac_done for s in trace]
    assert macs == sorted(macs)


def test_pipelined_has_single_prologue_load_and_no_compute_stalls():
    trace = simulate(GENERIC_128, wl(8, 2, dbuf=True))
    loads = [s for s in trace if s.phase == "load"]
    assert len(loads) == 1  # only the prologue
    assert loads[0].stalled
    computes = [s for s in trace if s.phase == "compute"]
    assert all(not s.stalled for s in computes)
    # every compute except the last tile's overlaps a background load
    assert any(s.prefetching for s in computes)
    assert not computes[-1].prefetching


def test_prefetch_implies_memory_active():
    for s in simulate(GENERIC_128, wl(8, 2, dbuf=True)):
        if s.prefetching:
            assert s.mem_active and s.phase == "compute"


def test_pipelined_never_slower_than_serial():
    for w in ((8, 2), (6, 2), (6, 3), (4, 2), (4, 0)):
        s = analyze(GENERIC_128, wl(*w))
        assert s.pipelined_cycles <= s.serial_cycles


def test_single_tile_no_speedup():
    s = analyze(GENERIC_128, wl(4, 0))
    assert s.pipelined_cycles == s.serial_cycles


def test_tiled_workload_gets_speedup():
    s = analyze(GENERIC_128, wl(8, 2))
    assert s.pipelined_cycles < s.serial_cycles
