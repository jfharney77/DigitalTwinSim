"""Full-trace invariants for the CloudIQ pipeline engine (style of the GPU,
R760, and PowerStore apps): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import simulate
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "idle", "collect", "transmit", "ingest", "analyze", "detect", "surface",
    "assist", "notify",
]


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


def test_progress_percent_monotonic_0_to_100():
    trace = simulate()
    prog = [s.progress_percent for s in trace]
    assert all(0 <= p <= 100 for p in prog)
    assert all(a <= b for a, b in zip(prog, prog[1:])), "progress regressed"
    assert trace[0].progress_percent == 0, "starts at 0"
    assert trace[-1].progress_percent == 100, "ends at 100"


def test_health_score_in_range():
    assert all(0 <= s.health_score <= 100 for s in simulate())


def test_health_starts_perfect_dips_on_detection_then_recovers():
    """The signature CloudIQ behavior: healthy at idle, the Health Score drops
    when a risk is detected, and it begins recovering as remediation starts."""
    trace = simulate()
    assert trace[0].health_score == 100, "idle should be a perfect score"
    min_health = min(s.health_score for s in trace)
    assert min_health < 100, "no risk was ever detected — nothing to show"
    # The dip happens at or after the 'detect' phase, never before.
    first_dip = next(i for i, s in enumerate(trace) if s.health_score < 100)
    first_detect = next(i for i, s in enumerate(trace) if s.phase == "detect")
    assert first_dip >= first_detect
    # The final step is recovering: above the low-water mark, but not yet 100.
    assert min_health < trace[-1].health_score < 100


def test_analyze_is_the_longest_stage():
    trace = simulate()
    analyze = [s for s in trace if s.phase == "analyze"]
    assert analyze, "no analyze step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert analyze[0].cycle_cost == max_cost
    # Strictly the single longest stage (the ML pass).
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_telemetry_flows_one_way():
    """Transmit (leaving the data center) must precede any insight surfacing —
    telemetry flows source → cloud → insight, never the reverse."""
    trace = simulate()
    first_transmit = next(i for i, s in enumerate(trace) if s.phase == "transmit")
    first_surface = next(i for i, s in enumerate(trace) if s.phase == "surface")
    assert first_transmit < first_surface
