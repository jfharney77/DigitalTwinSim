"""Full-trace invariants for the cluster-join engine (house style: assert
over the whole simulate() trace, no HTTP layer).

The signature invariants are the launch claims made testable: downtime is
identically zero, service never pauses, the mixed-generation join happens
exactly once, the live rebalance is the honest longest stage, and the 3x
performance multiplier is earned at cutover — never before it."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import simulate

PHASE_ORDER = [
    "steady", "power", "join", "mesh", "rebalance", "cutover", "repurpose",
    "elite",
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


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


def test_downtime_is_always_zero():
    """The twin's reason for existing: host-visible downtime across the
    entire modernization is identically zero, on every single step."""
    for state in simulate():
        assert state.downtime_seconds == 0, (
            f"step {state.step} ({state.label!r}) reports downtime — the "
            f"no-forklift claim just failed"
        )


def test_service_never_pauses():
    """IOPS is positive on every step and never falls below 85% of the
    starting baseline — the rebalance may tax service, never stop it."""
    trace = simulate()
    base = trace[0].iops_thousands
    assert base > 0
    for state in trace:
        assert state.iops_thousands > 0, f"step {state.step}: service stopped"
        assert state.iops_thousands >= 0.85 * base, (
            f"step {state.step}: served IOPS fell below the floor"
        )


def test_generations_join_exactly_once():
    """One generation before the join, two from the join to the end —
    monotone, exactly one increment, and it lands in the join phase.
    Mixed-generation membership is the end state, not a transition."""
    trace = simulate()
    gens = [s.generations_in_cluster for s in trace]
    assert gens[0] == 1
    assert gens[-1] == 2
    assert all(a <= b for a, b in zip(gens, gens[1:])), "generations regressed"
    increments = [
        i for i in range(1, len(trace)) if gens[i] == gens[i - 1] + 1
    ]
    assert len(increments) == 1, "the join must happen exactly once"
    assert trace[increments[0]].phase == "join"


def test_rebalance_is_the_longest_stage():
    """Moving petabytes live takes hours; the trace dwells there. The
    honest location of the cost of 'no migration project' is duration."""
    trace = simulate()
    max_cost = max(s.cycle_cost for s in trace)
    longest = [s for s in trace if s.cycle_cost == max_cost]
    assert len(longest) == 1, "the longest stage must be unique"
    assert longest[0].phase == "rebalance"


def test_performance_triples_only_after_cutover():
    """The 3x claim is earned by the sequence: before cutover the cluster
    serves near baseline (≤1.2x), from cutover on it serves ≥3x."""
    trace = simulate()
    base = trace[0].iops_thousands
    cut = next(i for i, s in enumerate(trace) if s.phase == "cutover")
    for state in trace[:cut]:
        assert state.iops_thousands <= 1.2 * base, (
            f"step {state.step}: the 3x showed up before cutover earned it"
        )
    for state in trace[cut:]:
        assert state.iops_thousands >= 3 * base, (
            f"step {state.step}: post-cutover service below the 3x claim"
        )


def test_effective_capacity_only_grows_and_jumps_at_the_join():
    """Capacity is monotone and its single jump is the join — joining a
    cluster is what adds a pool; nothing else in the trace does."""
    trace = simulate()
    caps = [s.effective_tb for s in trace]
    assert all(a <= b for a, b in zip(caps, caps[1:])), "capacity shrank"
    jumps = [i for i in range(1, len(trace)) if caps[i] > caps[i - 1]]
    assert len(jumps) == 1, "capacity must jump exactly once"
    assert trace[jumps[0]].phase == "join"
    assert caps[-1] >= 5800, "the Elite pool alone is 5.8 PB effective"


def test_the_mesh_carries_the_migration():
    """The RDMA interconnect lights first in the mesh phase — never
    before — and is active on every rebalance step: all cross-generation
    data movement rides it."""
    trace = simulate()
    first_mesh = next(i for i, s in enumerate(trace) if s.phase == "mesh")
    for state in trace[:first_mesh]:
        assert "cluster-mesh" not in state.active_regions, (
            f"step {state.step}: the mesh lit before the mesh phase"
        )
    for state in trace:
        if state.phase == "rebalance":
            assert "cluster-mesh" in state.active_regions, (
                f"step {state.step}: rebalancing without the interconnect"
            )


def test_elite_nodes_wake_in_lockstep():
    """In the power phase, whatever lights on node A lights on node B too —
    the dual-canister habit inherited from the PowerStore twin."""
    for state in simulate():
        if state.phase != "power":
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


def test_the_prior_generation_is_never_evicted():
    """The final steady state still lights prior-generation hardware —
    repurposed, not retired. Mixed-generation is where the story ends."""
    trace = simulate()
    last = trace[-1]
    assert any(rid.startswith("prior-") for rid in last.active_regions), (
        "the old array vanished from the end state — that's a forklift "
        "with extra steps"
    )
    assert last.generations_in_cluster == 2


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
