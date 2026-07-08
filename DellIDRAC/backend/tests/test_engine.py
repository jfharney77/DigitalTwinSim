"""Full-trace invariants for the iDRAC bring-up engine (style of the R760
app's test_engine.py): assert over the whole simulate() trace, no HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import simulate

PHASE_ORDER = ["off", "standby", "reset", "bootldr", "kernel", "services", "ready"]


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


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


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


def test_engine_is_pure():
    """The engine must not import FastAPI/IO — same rule as the other twins."""
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
