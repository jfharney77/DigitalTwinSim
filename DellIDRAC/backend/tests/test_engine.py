"""Full-trace invariants for the iDRAC bring-up engine (style of the R760
app's test_engine.py): assert over the whole simulate() trace, no HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import simulate
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = ["off", "standby", "reset", "bootldr", "kernel", "services", "ready"]


PROFILE = TraceProfile(phases=PHASE_ORDER, anatomy=ANATOMY)


def test_trace_invariants():
    """Steps from zero, phases in order and all reached, the clock advancing,
    only real regions lit, every step at least one cycle — and deterministic.
    The shared definitions live in twinkit.testing."""
    assert_trace_invariants(simulate(), PROFILE)
    assert_deterministic(simulate)


def test_engine_is_pure():
    import app.engine as engine_module

    assert_engine_is_pure(engine_module)


def test_power_watts_bounds():
    trace = simulate()
    assert all(s.power_watts >= 0 for s in trace)
    assert trace[0].power_watts == 0, "starts dark with no AC"
    assert trace[-1].power_watts > 0, "ends with iDRAC running on standby power"


def test_progress_percent_monotonic_and_completes():
    trace = simulate()
    pct = [s.progress_percent for s in trace]
    assert all(0 <= p <= 100 for p in pct)
    assert pct == sorted(pct), "init progress regressed"
    assert pct[0] == 0 and pct[-1] == 100


def test_lifecycle_controller_is_the_longest_stage():
    trace = simulate()
    lc = [s for s in trace if "lifecycle controller" in s.label.lower()]
    assert lc, "no Lifecycle Controller step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert lc[0].cycle_cost == max_cost
    # Strictly the single longest stage.
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_host_never_powers_on():
    """This twin is iDRAC's own bring-up; the host stays off the whole time,
    so BMC-domain draw stays in single/low-double-digit watts throughout."""
    assert all(s.power_watts <= 20 for s in simulate())
