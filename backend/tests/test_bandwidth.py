"""Bandwidth / roofline model tests (spec_04 §5)."""

from __future__ import annotations

import pytest

from app.engine import analyze, simulate
from app.models import Workload
from app.profiles import GENERIC_128


def wl(n: int, tile: int = 0, dtype: str = "fp32") -> Workload:
    return Workload(N=n, tile_size=tile, dtype=dtype)  # type: ignore[arg-type]


def test_determinism():
    assert analyze(GENERIC_128, wl(4, 2)) == analyze(GENERIC_128, wl(4, 2))


def test_intensity_is_macs_per_byte():
    s = analyze(GENERIC_128, wl(4, 4, "fp32"))
    assert s.arithmetic_intensity == pytest.approx(64 / s.bytes_moved)


def test_smaller_tiles_lower_intensity_toward_memory_bound():
    # Less reuse -> more bytes moved -> lower intensity.
    big = analyze(GENERIC_128, wl(8, 8))
    small = analyze(GENERIC_128, wl(8, 2))
    assert small.arithmetic_intensity < big.arithmetic_intensity
    assert small.bytes_moved > big.bytes_moved


def test_lower_precision_raises_intensity_toward_compute_bound():
    fp32 = analyze(GENERIC_128, wl(4, 2, "fp32"))
    fp16 = analyze(GENERIC_128, wl(4, 2, "fp16"))
    int8 = analyze(GENERIC_128, wl(4, 2, "int8"))
    assert fp16.arithmetic_intensity > fp32.arithmetic_intensity
    assert int8.arithmetic_intensity > fp16.arithmetic_intensity


def test_regime_flips_with_dtype():
    # Same workload; fp32 is memory-bound, int8 tips to compute-bound.
    assert analyze(GENERIC_128, wl(4, 2, "fp32")).regime == "memory"
    assert analyze(GENERIC_128, wl(4, 2, "int8")).regime == "compute"


def test_regime_consistent_with_cycle_totals():
    for w in (wl(4, 2, "fp32"), wl(8, 4, "fp16"), wl(6, 2, "int8")):
        s = analyze(GENERIC_128, w)
        if s.regime == "memory":
            assert s.load_cycles_total > s.compute_cycles_total
        else:
            assert s.load_cycles_total <= s.compute_cycles_total


def test_load_states_are_stalled_and_costly():
    trace = simulate(GENERIC_128, wl(4, 4, "fp32"))
    loads = [s for s in trace if s.phase == "load"]
    assert loads and all(s.stalled for s in loads)
    assert all(s.cycle_cost >= 1 for s in loads)
    # A big fp32 whole-matrix load costs more than one cycle.
    assert max(s.cycle_cost for s in loads) > 1
    # Non-load states are never stalled.
    assert all(not s.stalled for s in trace if s.phase != "load")
