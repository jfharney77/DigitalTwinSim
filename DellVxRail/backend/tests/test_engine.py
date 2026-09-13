"""Full-trace invariants for the cluster first-run engine (style of the GPU,
R760, and PowerStore twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import NODES, simulate
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "off", "power", "esxi", "discovery", "primary", "cluster", "vsan", "online",
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


def test_power_watts_bounds():
    trace = simulate()
    assert all(s.power_watts >= 0 for s in trace)
    assert trace[0].power_watts == 0, "starts dark before power-on"
    assert trace[-1].power_watts > 0, "ends serving VMs"


def test_progress_percent_monotonic_0_to_100():
    trace = simulate()
    prog = [s.progress_percent for s in trace]
    assert all(0 <= p <= 100 for p in prog)
    assert prog[0] == 0 and prog[-1] == 100
    assert prog == sorted(prog), "cluster-build progress must not go backwards"


def test_cluster_build_is_the_longest_stage():
    """VxRail Manager building the cluster is the single longest stage — like
    the R760's memory training or PowerStore's OS boot, the UI dwells here."""
    trace = simulate()
    build = [s for s in trace if "builds the cluster" in s.label.lower()]
    assert build, "no cluster-build step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert build[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def _node_suffixes(active):
    """Node suffixes (n1..n4) present among a set of active region ids."""
    return {rid.rsplit("-", 1)[1] for rid in active if rid.rsplit("-", 1)[1] in NODES}


def test_nodes_boot_in_lockstep():
    """In the power/esxi/discovery phases, whatever lights on one node lights
    on all nodes — the cluster's nodes wake in parallel, never one at a time."""
    for state in simulate():
        if state.phase not in ("power", "esxi", "discovery"):
            continue
        active = set(state.active_regions)
        for rid in active:
            base, _, suffix = rid.rpartition("-")
            if suffix in NODES:
                for n in NODES:
                    twin = f"{base}-{n}"
                    assert twin in active, (
                        f"step {state.step}: {rid} lit without its twin {twin}"
                    )


def test_primary_election_lights_exactly_one_node():
    """The defining HCI beat: in the 'primary' phase exactly one node — the
    election winner running VxRail Manager — is active, breaking lockstep."""
    primary = [s for s in simulate() if s.phase == "primary"]
    assert primary, "no primary-election step"
    for state in primary:
        suffixes = _node_suffixes(state.active_regions)
        assert suffixes == {"n1"}, (
            f"step {state.step}: expected only the elected node n1, got {suffixes}"
        )
