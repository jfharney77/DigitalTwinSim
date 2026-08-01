"""Full-trace invariants for the SN6000 fabric engine (style of the GPU,
R760, and PowerStore twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import LEAVES, SPINES, TRAFFIC_PHASES, simulate

PHASE_ORDER = [
    "off", "power", "linktrain", "topology", "ready",
    "collective", "congestion", "reroute", "steady",
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


def test_fabric_never_drops_a_packet():
    """THE invariant, and this twin's reason for existing: an AI fabric's
    product is what it refuses to do. Zero drops on every step — including
    at the peak of the incast, where ordinary Ethernet would be discarding
    frames and forcing retransmissions that stall the whole job."""
    for s in simulate():
        assert s.dropped_packets == 0, (
            f"step {s.step} ({s.phase}): dropped {s.dropped_packets} packets"
        )


def test_congestion_actually_happens_and_is_survived():
    """The lossless claim is only interesting if the fabric is genuinely
    pushed: the congestion step must drive the hot link near saturation,
    still without loss."""
    trace = simulate()
    congestion = [s for s in trace if s.phase == "congestion"]
    assert congestion, "no congestion step — the invariant would be untested"
    assert max(s.peak_link_percent for s in congestion) >= 95, (
        "congestion step must actually saturate a link"
    )


def test_adaptive_routing_relieves_without_losing_work():
    """After the reroute, the hot link must be measurably cooler while total
    throughput does not fall — the work did not shrink, it spread."""
    trace = simulate()
    peak = next(s for s in trace if s.phase == "congestion")
    after = next(s for s in trace if s.phase == "reroute")
    assert after.peak_link_percent < peak.peak_link_percent, (
        "reroute must relieve the hot link"
    )
    assert after.fabric_tbps >= peak.fabric_tbps, (
        "throughput must not fall when flows are spread"
    )


def test_no_traffic_before_links_train():
    """Nothing crosses the fabric until every link has trained and routing
    has converged — bytes cannot precede a working path."""
    trace = simulate()
    first_traffic = next(i for i, s in enumerate(trace) if s.fabric_tbps > 0)
    last_bringup = max(
        i for i, s in enumerate(trace)
        if s.phase in ("off", "power", "linktrain", "topology")
    )
    assert last_bringup < first_traffic
    for s in trace:
        if s.phase not in TRAFFIC_PHASES:
            assert s.fabric_tbps == 0, f"step {s.step}: traffic during {s.phase}"


def test_spine_leaf_lockstep_during_bringup():
    """Bring-up is uniform: whenever any spine is active, all spines are,
    and likewise for leaves. A half-trained fabric is not a fabric."""
    for state in simulate():
        active = set(state.active_regions)
        lit_spines = {r for r in active if r.startswith("spine-")}
        if lit_spines:
            assert lit_spines == {f"spine-{s}" for s in SPINES}, (
                f"step {state.step}: partial spine set {lit_spines}"
            )
        lit_leaves = {r for r in active if r.startswith("leaf-")}
        if lit_leaves:
            assert lit_leaves == {f"leaf-{l}" for l in LEAVES}, (
                f"step {state.step}: partial leaf set {lit_leaves}"
            )


def test_traffic_always_crosses_leaves_and_spines():
    """Any endpoint-to-endpoint traffic is two hops through the topology, so
    whenever the fabric carries traffic, both tiers are working."""
    for s in simulate():
        if s.fabric_tbps > 0:
            active = set(s.active_regions)
            assert any(r.startswith("spine-") for r in active), (
                f"step {s.step}: traffic without spines"
            )
            assert any(r.startswith("leaf-") for r in active), (
                f"step {s.step}: traffic without leaves"
            )


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


def test_link_training_is_the_longest_stage():
    """Training every link at 1.6 Tb/s is the single longest stage — as with
    the R760's memory training and the XE9712's NVLink fabric, the UI dwells
    here."""
    trace = simulate()
    lt = [s for s in trace if s.phase == "linktrain"]
    assert lt, "no link-training step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert lt[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


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
