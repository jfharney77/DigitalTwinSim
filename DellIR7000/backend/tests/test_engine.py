"""Full-trace invariants for the thermal bring-up engine (style of the GPU,
R760, and PowerStore twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import BAYS, simulate

PHASE_ORDER = [
    "off", "fill", "pump", "verify", "airdoor", "load", "balance", "steady",
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


def test_heat_balance_holds_on_every_step():
    """The twin's defining invariant: energy is conserved. Every watt of IT
    load leaves through the liquid loop or the rear door — exactly, on every
    step, with no tolerance. Heat is not managed; it is conserved."""
    for s in simulate():
        assert s.liquid_watts + s.air_watts == s.it_load_watts, (
            f"step {s.step} ({s.phase}): {s.liquid_watts} + {s.air_watts} "
            f"!= {s.it_load_watts}"
        )


def test_liquid_carries_the_overwhelming_share():
    """Direct liquid cooling is the point: whenever there is load, at least
    85% of it leaves through the liquid loop, the rest via the rear door."""
    for s in simulate():
        if s.it_load_watts > 0:
            assert s.liquid_watts / s.it_load_watts >= 0.85, (
                f"step {s.step}: liquid share "
                f"{s.liquid_watts / s.it_load_watts:.2f} < 0.85"
            )


def test_flow_before_heat():
    """Liquid before silicon, seen from the loop's side: coolant is flowing
    (flow_lpm > 0) strictly before the first watt of IT load appears, and
    flow never decreases while load is climbing."""
    trace = simulate()
    first_flow = next(i for i, s in enumerate(trace) if s.flow_lpm > 0)
    first_load = next(i for i, s in enumerate(trace) if s.it_load_watts > 0)
    assert first_flow < first_load
    flows = [s.flow_lpm for s in trace]
    assert flows == sorted(flows), "flow regressed during bring-up"


def test_load_monotonic_to_design_point():
    trace = simulate()
    loads = [s.it_load_watts for s in trace]
    assert loads[0] == 0, "starts with a dry, dark rack"
    assert loads == sorted(loads), "IT load regressed during the ramp"
    assert loads[-1] >= 200_000, "ends at the IR7000-class design point"


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


def test_verification_is_the_longest_stage():
    """The per-branch leak/flow verification is the single longest stage —
    the careful commissioning work the compute twins' liquid-before-silicon
    interlock waits on. The UI dwells here."""
    trace = simulate()
    verify = [s for s in trace if s.phase == "verify"]
    assert verify, "no verification step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert verify[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_bays_heat_in_lockstep():
    """Whenever any bay's cold plates are active, all four bays' are — the
    loop treats the payload as uniform heat, and verification, load, and
    balance sweep every branch together."""
    for state in simulate():
        active = set(state.active_regions)
        lit = {rid for rid in active if rid.startswith("coldplate-")}
        if lit:
            assert lit == {f"coldplate-{b}" for b in BAYS}, (
                f"step {state.step}: bays {lit} lit without their twins"
            )


def test_engine_is_pure():
    """The engine must not import FastAPI/IO — same rule as every twin."""
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
