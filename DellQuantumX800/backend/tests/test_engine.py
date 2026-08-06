"""Full-trace invariants for the Quantum-X800 fabric engine (style of the
GPU, R760, and SN6000 twins): assert over the whole simulate() trace, no
HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import (
    LEAVES,
    MANAGER_PHASES,
    SPINES,
    TRAFFIC_PHASES,
    simulate,
)

PHASE_ORDER = [
    "off", "power", "discover", "routes", "credits", "ready",
    "collective", "sharp", "burst", "steady",
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


def test_no_packet_is_ever_sent_without_a_credit():
    """THE invariant, and this twin's reason for existing — stated in the
    constructive form the SN6000 twin cannot claim: not zero drops caught
    in time, but zero transmissions the link layer could not express."""
    for s in simulate():
        assert s.packets_sent_without_credit == 0, (
            f"step {s.step} ({s.phase}): {s.packets_sent_without_credit} "
            f"uncredited transmissions"
        )


def test_the_burst_stalls_senders_instead_of_losing_work():
    """The claim is only interesting under stress: the burst step must
    drive the hot link near saturation AND make senders genuinely wait —
    the honest cost of constructive losslessness — while nothing is lost
    and the collective keeps running."""
    trace = simulate()
    bursts = [s for s in trace if s.phase == "burst"]
    assert bursts, "no burst step — the invariant would be untested"
    peak = max(bursts, key=lambda s: s.peak_link_percent)
    assert peak.peak_link_percent >= 95, "burst must actually saturate a link"
    assert peak.stall_micros_per_sec > 0, (
        "burst must stall senders — a lossless fabric that never waits "
        "was never actually stressed"
    )
    assert peak.allreduce_gbps > 0, "the job must keep making progress"


def test_stalls_happen_only_under_the_burst():
    """Waiting is the price of the incast, not a standing tax: every step
    outside the burst phase carries zero stall time."""
    for s in simulate():
        if s.phase != "burst":
            assert s.stall_micros_per_sec == 0, (
                f"step {s.step} ({s.phase}): stalls outside the burst"
            )


def test_routes_are_installed_before_any_traffic():
    """The fabric is programmed, not converged: no byte moves until the
    subnet manager's forwarding tables are installed and credits armed."""
    trace = simulate()
    first_traffic = next(i for i, s in enumerate(trace) if s.fabric_tbps > 0)
    last_bringup = max(
        i for i, s in enumerate(trace)
        if s.phase in ("off", "power", "discover", "routes", "credits")
    )
    assert last_bringup < first_traffic
    for s in trace:
        if s.phase not in TRAFFIC_PHASES:
            assert s.fabric_tbps == 0, f"step {s.step}: traffic during {s.phase}"
            assert s.allreduce_gbps == 0, (
                f"step {s.step}: collective progress during {s.phase}"
            )


def test_the_manager_programs_the_fabric_then_leaves_the_data_path():
    """The centralized brain's whole biography: active in exactly the
    discover and routes phases, absent from every step that carries
    traffic. Central control plane, distributed data plane — the same
    move as Exascale's metadata server and PowerFlex's coordinator."""
    trace = simulate()
    for s in trace:
        if s.phase in MANAGER_PHASES:
            assert "manager" in s.active_regions, (
                f"step {s.step} ({s.phase}): the SM should be working here"
            )
        else:
            assert "manager" not in s.active_regions, (
                f"step {s.step} ({s.phase}): the SM must be off the data path"
            )
    manager_steps = {s.phase for s in trace if "manager" in s.active_regions}
    assert manager_steps == MANAGER_PHASES


def test_sharp_moves_the_math_into_the_fabric():
    """The signature crossing: when SHARP engages, raw fabric traffic
    strictly falls (sums are smaller than their inputs; data crosses once)
    while the effective all-reduce rate strictly rises. Both switch tiers
    must be lit — the reduction runs in the switches."""
    trace = simulate()
    collective = next(s for s in trace if s.phase == "collective")
    sharp = next(s for s in trace if s.phase == "sharp")
    assert sharp.fabric_tbps < collective.fabric_tbps, (
        "SHARP must reduce the bytes crossing the fabric"
    )
    assert sharp.allreduce_gbps > collective.allreduce_gbps, (
        "SHARP must raise the effective all-reduce rate"
    )
    active = set(sharp.active_regions)
    assert any(r.startswith("spine-") for r in active)
    assert any(r.startswith("leaf-") for r in active)


def test_route_computation_is_the_longest_stage():
    """Computing every forwarding table centrally is the single longest
    stage — the InfiniBand counterpart of the SN6000's link training and
    the R760's memory training. Programmed, not converged, and the wait
    is the work."""
    trace = simulate()
    routes = [s for s in trace if s.phase == "routes"]
    assert routes, "no route-computation step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert routes[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_spine_leaf_lockstep():
    """Whenever any spine is active, all spines are, and likewise leaves —
    a half-programmed fabric is not a fabric."""
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
    """Any endpoint-to-endpoint traffic is two hops through the topology,
    so whenever the fabric carries traffic, both tiers are working."""
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
