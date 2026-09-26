"""Full-trace invariants for the SN6000 fabric engine (style of the GPU,
R760, and PowerStore twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import LEAVES, SPINES, TRAFFIC_PHASES, simulate
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "off", "power", "linktrain", "topology", "ready",
    "collective", "congestion", "reroute", "steady",
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


def test_losslessness_is_paid_for_and_the_price_is_shown():
    """Zero drops is not a free lunch. On the congestion step the fabric is
    marking (ECN) and pausing (PFC), and both figures are on the trace so the
    panel can show them beside the zero — the Ethernet counterpart of the
    Quantum-X800 twin's sender-stall row. After the reroute the pauses stop
    and the marks fall; before any traffic both are zero."""
    trace = simulate()
    peak = next(s for s in trace if s.phase == "congestion")
    after = next(s for s in trace if s.phase == "reroute")
    assert peak.ecn_marked_percent > 0 and peak.pfc_pauses_per_sec > 0
    assert after.pfc_pauses_per_sec == 0
    assert after.ecn_marked_percent < peak.ecn_marked_percent
    for s in trace:
        if s.fabric_tbps == 0:
            assert s.ecn_marked_percent == 0 and s.pfc_pauses_per_sec == 0
        if s.pfc_pauses_per_sec > 0:
            assert s.peak_link_percent >= 90, "pauses only under saturation"


def test_the_hot_link_is_one_adaptive_routing_can_relieve():
    """The hotspot is a leaf-spine link, named exactly while it is saturated.
    A rack's last hop has no alternate path, so crediting adaptive routing
    with relieving it would be wrong; the hot link must have a sibling
    through the other spine."""
    ids = {r.id for r in ANATOMY.regions}
    for s in simulate():
        assert (s.hot_link is not None) == (s.peak_link_percent >= 90), s.step
        if s.hot_link:
            leaf, spine = s.hot_link.split(":")
            assert leaf in ids and leaf.startswith("leaf-")
            assert spine in ids and spine.startswith("spine-")
            assert len(SPINES) > 1, "no alternate path to reroute onto"


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


def test_link_training_is_the_longest_stage():
    """Training every link at 800 Gb/s is the single longest stage — as with
    the R760's memory training and the XE9712's NVLink fabric, the UI dwells
    here."""
    trace = simulate()
    lt = [s for s in trace if s.phase == "linktrain"]
    assert lt, "no link-training step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert lt[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1
