"""Full-trace invariants for the PowerScale namespace engine (style of the
GPU, R760, and PowerFlex twins): assert over the whole simulate() trace,
no HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import (
    ADDED_NODES,
    ALL_NODES,
    INITIAL_NODES,
    PROTOCOLS,
    SERVING_PHASES,
    simulate,
)
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "off", "form", "stripe", "serve",
    "fill", "addnode", "rebalance", "served",
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


def test_there_is_only_ever_one_namespace():
    """THE invariant, and this twin's reason for existing. Conventional NAS
    accumulates volumes, each a future migration. OneFS presents one file
    system at four nodes and at six — growth never mints a second one."""
    for s in simulate():
        assert s.namespaces == 1, (
            f"step {s.step} ({s.phase}): {s.namespaces} namespaces — "
            f"someone provisioned a volume"
        )


def test_growing_the_cluster_requires_no_migration():
    """The administrative cost conventional NAS pays forever and this
    architecture does not pay at all. migrations_required is zero on every
    step, including across the expansion and the rebalance."""
    trace = simulate()
    assert any(s.phase == "addnode" for s in trace), (
        "no expansion step — the invariant would be untested"
    )
    for s in trace:
        assert s.migrations_required == 0, (
            f"step {s.step} ({s.phase}): {s.migrations_required} migrations "
            f"required — that is a volume architecture wearing a disguise"
        )


def test_capacity_grows_with_nodes_not_with_planning():
    """capacity_tb increases only at the addnode step, in lockstep with the
    node count — never because anything was provisioned. And used_percent
    falls there as a consequence of new hardware, not because anything was
    deleted or moved by hand."""
    trace = simulate()
    addnode_index = next(i for i, s in enumerate(trace) if s.phase == "addnode")
    growth_steps = [
        i for i in range(1, len(trace))
        if trace[i].capacity_tb > trace[i - 1].capacity_tb
    ]
    assert growth_steps == [addnode_index], (
        f"capacity changed at steps {growth_steps}, expected only the "
        f"addnode step {addnode_index}"
    )
    # Capacity never shrinks, and the jump rides on nodes joining.
    caps = [s.capacity_tb for s in trace]
    assert all(a <= b for a, b in zip(caps, caps[1:])), "capacity shrank"
    assert trace[addnode_index].nodes > trace[addnode_index - 1].nodes
    # Fullness falls at the expansion — the consequence, not an action.
    assert trace[addnode_index].used_percent < trace[addnode_index - 1].used_percent
    # And nowhere else: no step deletes or moves data to free space.
    for i in range(1, len(trace)):
        if i != addnode_index:
            assert trace[i].used_percent >= trace[i - 1].used_percent, (
                f"step {i}: usage fell outside the expansion"
            )


def test_service_continues_during_rebalance():
    """Expansion is a background task, not an outage. From the serve phase
    onward every step keeps all four protocols up — including while
    rebalancing is true."""
    trace = simulate()
    rebalancing = [s for s in trace if s.phase == "rebalance"]
    assert rebalancing, "no rebalance step — the invariant would be untested"
    assert all(s.rebalancing for s in rebalancing)
    first_serve = next(i for i, s in enumerate(trace) if s.phase == "serve")
    for s in trace[first_serve:]:
        assert s.phase in SERVING_PHASES
        for proto in PROTOCOLS:
            assert proto in s.active_regions, (
                f"step {s.step} ({s.phase}): {proto} down — clients "
                f"noticed the expansion"
            )


def test_rebalancing_flag_only_during_rebalance():
    for s in simulate():
        assert s.rebalancing == (s.phase == "rebalance"), (
            f"step {s.step} ({s.phase}): rebalancing={s.rebalancing}"
        )


def test_all_nodes_serve_all_protocols():
    """No node is the 'NFS node' or the 'SMB head'. Whenever any protocol
    is up, all four are up and every online node is lit — which is what
    makes the single namespace usable rather than merely true."""
    for s in simulate():
        lit_protos = [p for p in s.active_regions if p in PROTOCOLS]
        if lit_protos:
            assert set(lit_protos) == set(PROTOCOLS), (
                f"step {s.step}: only {lit_protos} up — a protocol head "
                f"exists somewhere"
            )
            lit_nodes = {r for r in s.active_regions if r.startswith("node-")}
            assert len(lit_nodes) == s.nodes, (
                f"step {s.step}: {len(lit_nodes)} nodes serving but "
                f"{s.nodes} online"
            )


def test_nodes_are_never_partitioned():
    """Striping spans the cluster: no step lights a strict subset of the
    online nodes for data placement. The lit node set is always empty, the
    initial four, or all six."""
    allowed = [set(), set(INITIAL_NODES), set(ALL_NODES)]
    for s in simulate():
        lit = {r for r in s.active_regions if r.startswith("node-")}
        assert lit in allowed, f"step {s.step}: partitioned node set {lit}"
        if lit:
            assert len(lit) == s.nodes, (
                f"step {s.step}: {len(lit)} nodes lit, {s.nodes} online"
            )


def test_the_new_nodes_join_and_stay():
    """Nodes five and six appear at the addnode step and serve on every
    step after — the cluster grew, it did not gain spares."""
    trace = simulate()
    addnode_index = next(i for i, s in enumerate(trace) if s.phase == "addnode")
    for s in trace[:addnode_index]:
        for n in ADDED_NODES:
            assert n not in s.active_regions, (
                f"step {s.step}: {n} active before it joined"
            )
    for s in trace[addnode_index:]:
        assert s.nodes == len(ALL_NODES)
        for n in ADDED_NODES:
            assert n in s.active_regions, f"step {s.step}: {n} idle after joining"


def test_rebalancing_is_the_longest_stage():
    """Unique max cycle_cost. Redistributing data onto new nodes is
    genuinely slow, and it is the price of never having to migrate."""
    trace = simulate()
    rebalance = next(s for s in trace if s.phase == "rebalance")
    max_cost = max(s.cycle_cost for s in trace)
    assert rebalance.cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1, (
        "the rebalance must be the single longest stage"
    )


def test_the_namespace_region_is_lit_from_stripe_onward():
    """Once the file system is laid out, the one namespace never goes
    dark — it is the thing every later step is about."""
    trace = simulate()
    first_stripe = next(i for i, s in enumerate(trace) if s.phase == "stripe")
    for s in trace[first_stripe:]:
        assert "namespace" in s.active_regions, (
            f"step {s.step} ({s.phase}): the namespace went dark"
        )


def test_no_usage_before_the_namespace_is_served():
    for s in simulate():
        if s.used_percent > 0:
            assert s.phase in SERVING_PHASES, (
                f"step {s.step}: data present before clients could write it"
            )
