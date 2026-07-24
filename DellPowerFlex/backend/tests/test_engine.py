"""Full-trace invariants for the PowerFlex cluster engine (style of the GPU,
R760, and PowerStore twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import (
    ALL_NODES,
    FAILED_NODE,
    IO_PHASES,
    STEADY_PHASES,
    SURVIVORS,
    simulate,
)

PHASE_ORDER = [
    "off", "cluster", "pool", "volumes",
    "io", "failure", "rebuild", "rebalanced", "steady",
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


def test_every_surviving_node_rebuilds():
    """THE invariant, and this twin's reason for existing. A rebuild is
    many-to-many: every surviving node reconstructs a sliver at the same
    time, never a subset and never a designated partner. This is what makes
    recovery get faster as the cluster grows — in a hundred-node pool a
    hundred nodes each rebuild a hundredth."""
    trace = simulate()
    rebuilding = [s for s in trace if s.phase == "rebuild"]
    assert rebuilding, "no rebuild step — the invariant would be untested"
    for s in rebuilding:
        assert s.rebuild_participants == s.nodes_online, (
            f"step {s.step}: only {s.rebuild_participants} of "
            f"{s.nodes_online} nodes rebuilding — that is a controller "
            f"architecture wearing a disguise"
        )


def test_nobody_rebuilds_outside_a_rebuild():
    for s in simulate():
        if s.phase != "rebuild":
            assert s.rebuild_participants == 0, (
                f"step {s.step} ({s.phase}): rebuilding with nothing to rebuild"
            )


def test_no_node_is_privileged():
    """There is no controller, so no node is special. In every step the lit
    node set is either empty, all six, or all five survivors — never an
    arbitrary subset, and never one node doing the work for the others."""
    allowed = [set(), set(ALL_NODES), set(SURVIVORS)]
    for s in simulate():
        lit = {r for r in s.active_regions if r.startswith("node-")}
        assert lit in allowed, f"step {s.step}: privileged node set {lit}"


def test_the_failed_node_never_comes_back():
    """Once node 6 is gone it stays gone for the rest of the trace — the
    pool recovers by redistributing onto survivors, not by waiting for a
    replacement."""
    trace = simulate()
    first_failure = next(i for i, s in enumerate(trace) if s.phase == "failure")
    for s in trace[first_failure:]:
        assert FAILED_NODE not in s.active_regions, (
            f"step {s.step}: {FAILED_NODE} rose from the dead"
        )
        assert s.nodes_online == len(SURVIVORS)


def test_service_survives_the_failure():
    """Losing a node costs throughput proportional to the node, not a
    failover pause. I/O never stops and never falls below 70% of the steady
    rate — a controller array's failover would show a gap here."""
    trace = simulate()
    steady = max(s.iops_thousands for s in trace)
    for s in trace:
        if s.phase in ("failure", "rebuild"):
            assert s.iops_thousands > 0, f"step {s.step}: I/O stopped"
            assert s.iops_thousands >= 0.7 * steady, (
                f"step {s.step}: {s.iops_thousands} is a stall, not a dip"
            )


def test_protection_dips_and_fully_returns():
    """Protection is allowed to fall when hardware is lost, and is not
    allowed to settle anywhere but 100."""
    trace = simulate()
    failure = next(s for s in trace if s.phase == "failure")
    assert failure.protected_percent < 100, (
        "losing a node with no protection impact would mean nothing was "
        "protected in the first place"
    )
    for s in trace:
        if s.phase in ("rebalanced", "steady"):
            assert s.protected_percent == 100, (
                f"step {s.step} ({s.phase}): settled at "
                f"{s.protected_percent}% protection"
            )


def test_protection_recovers_monotonically_after_the_failure():
    trace = simulate()
    start = next(i for i, s in enumerate(trace) if s.phase == "failure")
    after = [s.protected_percent for s in trace[start:]]
    assert all(a <= b for a, b in zip(after, after[1:])), (
        "protection went backwards during recovery"
    )


def test_the_coordinator_is_absent_from_the_steady_data_path():
    """The metadata manager referees; it does not carry data. During
    ordinary I/O it is dark, because the client already holds the map and
    addresses nodes directly. It lights up only to place chunks and to
    handle a failure."""
    for s in simulate():
        if s.phase in STEADY_PHASES:
            assert "mdm" not in s.active_regions, (
                f"step {s.step} ({s.phase}): coordinator in the data path"
            )


def test_no_io_before_the_pool_is_protected():
    """Nothing is served from a pool that has not finished laying out its
    redundant copies."""
    for s in simulate():
        if s.iops_thousands > 0:
            assert s.protected_percent > 0, f"step {s.step}: unprotected I/O"
            assert s.phase in IO_PHASES


def test_clients_are_lit_whenever_there_is_io():
    for s in simulate():
        if s.iops_thousands > 0:
            assert "clients" in s.active_regions, f"step {s.step}: I/O with no client"
            assert "fabric" in s.active_regions, f"step {s.step}: I/O with no fabric"


def test_building_the_pool_is_the_longest_stage_not_repairing_it():
    """This twin deliberately inverts the pattern the other twins follow. In
    the R760 it is memory training, in the SN6000 link training, in the Pro
    Max Plus the model load — always some unavoidable setup. Here the long
    stage is scattering chunks across every node, and the *rebuild* is
    markedly shorter, because the data was already everywhere. That
    relationship is the product claim, so it is pinned."""
    trace = simulate()
    pool = next(s for s in trace if s.phase == "pool")
    rebuild = next(s for s in trace if s.phase == "rebuild")
    max_cost = max(s.cycle_cost for s in trace)
    assert pool.cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1
    assert rebuild.cycle_cost < pool.cycle_cost, (
        "if recovery cost as much as construction, the scatter bought "
        "nothing"
    )


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


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
