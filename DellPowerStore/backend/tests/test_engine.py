"""Full-trace invariants for the power-on engine (style of the GPU and R760
apps): assert over the whole simulate() trace, no HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import simulate

PHASE_ORDER = ["off", "power", "boot", "drives", "cluster", "services", "online"]


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
    assert trace[0].power_watts == 0, "starts dark at AC plug-in"
    assert trace[-1].power_watts > 0, "ends serving I/O"


def test_fan_percent_in_range():
    trace = simulate()
    assert all(0 <= s.fan_percent <= 100 for s in trace)


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


def test_powerstoreos_boot_is_the_longest_stage():
    trace = simulate()
    boot = [s for s in trace if "powerstoreos" in s.label.lower()]
    assert boot, "no PowerStoreOS-boot step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert boot[0].cycle_cost == max_cost
    # Strictly the single longest stage.
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_dual_node_bring_up_is_symmetric():
    """In power/boot, whatever lights on node A lights on node B too —
    the two canisters wake in parallel, never one at a time."""
    for state in simulate():
        if state.phase not in ("power", "boot"):
            continue
        active = set(state.active_regions)
        for rid in active:
            if rid.endswith("-a"):
                twin = rid[:-2] + "-b"
                assert twin in active, (
                    f"step {state.step}: {rid} lit without its twin {twin}"
                )
            elif rid.endswith("-b"):
                twin = rid[:-2] + "-a"
                assert twin in active, (
                    f"step {state.step}: {rid} lit without its twin {twin}"
                )


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
