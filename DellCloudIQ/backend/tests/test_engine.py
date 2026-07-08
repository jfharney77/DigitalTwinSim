"""Full-trace invariants for the CloudIQ pipeline engine (style of the GPU,
R760, and PowerStore apps): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import simulate

PHASE_ORDER = [
    "idle", "collect", "transmit", "ingest", "analyze", "detect", "surface",
    "assist", "notify",
]


def test_steps_sequential_from_zero():
    trace = simulate()
    assert [s.step for s in trace] == list(range(len(trace)))


def test_phase_order_never_regresses_and_all_phases_appear():
    trace = simulate()
    indices = [PHASE_ORDER.index(s.phase) for s in trace]
    assert indices == sorted(indices), "phase order regressed"
    assert set(s.phase for s in trace) == set(PHASE_ORDER)


def test_elapsed_seconds_strictly_increasing():
    trace = simulate()
    elapsed = [s.elapsed_seconds for s in trace]
    assert all(a < b for a, b in zip(elapsed, elapsed[1:]))


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


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


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


def test_engine_is_pure():
    """The engine must not import FastAPI/IO — same rule as the GPU app."""
    import ast

    import app.engine as engine_module

    tree = ast.parse(open(engine_module.__file__, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {"fastapi", "time", "asyncio", "threading", "os", "io"}
