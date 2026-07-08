"""Full-trace invariants for the E3200 boot engine (style of the R760 app's
test_engine.py): assert over the whole simulate() trace, no HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import simulate

PHASE_ORDER = [
    "off", "standby", "poweron", "onie", "nos", "dataplane", "ports", "forwarding",
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


def test_power_watts_bounds():
    trace = simulate()
    assert all(s.power_watts >= 0 for s in trace)
    assert trace[0].power_watts == 0, "starts dark at AC disconnect"
    assert trace[-1].power_watts > 0, "ends forwarding with PoE up"


def test_fan_percent_in_range():
    trace = simulate()
    assert all(0 <= s.fan_percent <= 100 for s in trace)


def test_data_rate_zero_until_ports_then_nonzero_at_end():
    trace = simulate()
    # No traffic before the data plane / ports come up.
    early = [s for s in trace if s.phase in ("off", "standby", "poweron", "onie", "nos")]
    assert all(s.data_rate_gbps == 0 for s in early)
    assert trace[-1].data_rate_gbps > 0, "ends carrying line-rate traffic"


def test_poe_step_is_the_power_peak():
    """Most of the switch's wattage is the PoE budget leaving the front ports,
    so total draw peaks once PoE is delivered."""
    trace = simulate()
    poe = [s for s in trace if "poe" in s.label.lower()]
    assert poe, "no PoE step in the trace"
    assert max(s.power_watts for s in trace) == max(s.power_watts for s in poe)


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


def test_nos_boot_is_the_longest_stage():
    trace = simulate()
    nos = [s for s in trace if "network os" in s.label.lower()]
    assert nos, "no network-OS boot step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert nos[0].cycle_cost == max_cost
    # Strictly the single longest stage.
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


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
